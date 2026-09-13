# modes/scalper.py - استراتيجية السكالبر المتقدمة (القناص)
import pandas as pd
import numpy as np
from config import SCALPER_CONFIG, SYMBOLS_CONFIG

class ScalperBot:
    def __init__(self):
        self.config = SCALPER_CONFIG
        self.positions = {}
        self.capital = self.config['initial_capital']
        self.initial_capital = self.config['initial_capital']
        self.trades_log = []

    def calculate_indicators(self, df):
        """حساب جميع المؤشرات الفنية المطلوبة"""
        # EMA
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # ADX (مبسط للسرعة - في الإنتاج استخدم TA-Lib)
        # نفترض وجود اتجاه إذا كانت الشروط الأخرى محققة
        df['adx'] = 40 
        
        return df

    def check_smc_signals(self, df_5m, df_15m):
        """التحقق من إشارات SMC (BOS, CHoCH, FVG)"""
        last_5 = df_5m.iloc[-1]
        last_15 = df_15m.iloc[-1]
        
        signals = {'bos': False, 'fvg': False, 'liquidity_sweep': False}
        
        # منطق مبسط للباك تيست:
        # BOS: كسر هيكل مع إغلاق فوق الشمعة السابقة
        if len(df_5m) > 5:
            prev_high = df_5m['high'].iloc[-5:-1].max()
            if last_5['close'] > prev_high and last_5['close'] > last_5['open']:
                signals['bos'] = True
        
        # FVG: افتراض وجوده إذا كان هناك زخم قوي
        if last_5['close'] > last_15['ema_50'] and last_15['close'] > last_15['ema_50']:
            signals['fvg'] = True
            
        return signals

    def validate_entry(self, symbol, df_5m, df_15m):
        """التحقق من شروط الدخول الصارمة (فلاتر القناص)"""
        if len(df_5m) < 50 or len(df_15m) < 50:
            return None

        last = df_5m.iloc[-1]
        
        # 1. فلتر الاتجاه (EMA 50) - سعر فوق المتوسط
        if last['close'] < last['ema_50']:
            return None

        # 2. فلتر الزخم (RSI) - نطاق مثالي للدخول
        if not (45 < last['rsi'] < 70):
            return None

        # 3. فلتر الحجم - حجم تداول أعلى من المتوسط
        avg_vol = df_5m['volume'].rolling(20).mean().iloc[-1]
        if last['volume'] < avg_vol * 1.5:
            return None

        # 4. إشارات SMC
        smc = self.check_smc_signals(df_5m, df_15m)
        if not (smc['bos'] and smc['fvg']):
            return None

        # 5. تأكيد الشمعة - جسم شمعة قوي
        candle_body = abs(last['close'] - last['open'])
        candle_range = last['high'] - last['low']
        if candle_range == 0 or candle_body < candle_range * 0.5:
            return None

        # حساب الأهداف والرافعة
        atr = last['atr']
        sl_dist = atr * self.config['exit_strategy']['sl_atr_mult']
        tp1_dist = last['close'] * self.config['exit_strategy']['tp1_level']
        
        # رافعة ديناميكية حسب قوة الإشارة
        leverage = 5.0
        if last['volume'] > avg_vol * 2.5:
            leverage = 10.0
        elif last['volume'] > avg_vol * 1.8:
            leverage = 7.5

        return {
            'symbol': symbol,
            'entry': last['close'],
            'sl': last['close'] - sl_dist,
            'tp1': last['close'] + tp1_dist,
            'tp2': last['close'] + (tp1_dist * 2),
            'tp3': last['close'] + (tp1_dist * 4),
            'leverage': leverage,
            'direction': 'LONG'
        }

    def run_backtest(self, data_dict):
        """تشغيل الباك تيست على البيانات"""
        print(f"🚀 Starting Backtest with ${self.capital}...")
        
        min_len = min(len(d['5m']) for d in data_dict.values())
        active_trades = []
        
        # حلقة زمنية محاكية للسوق
        for i in range(200, min_len):
            for symbol, dfs in data_dict.items():
                df_5m = dfs['5m'].iloc[:i+1].copy()
                df_15m = dfs['15m'].iloc[:i+1].copy()
                
                # إدارة الصفقات المفتوحة
                for trade in active_trades[:]:
                    if trade['symbol'] != symbol:
                        continue
                    
                    current_price = df_5m.iloc[-1]['close']
                    
                    # التحقق من وقف الخسارة
                    if current_price <= trade['sl']:
                        loss = (trade['entry'] - current_price) * trade['size']
                        self.capital -= loss
                        self.trades_log.append({
                            **trade, 
                            'exit_price': current_price, 
                            'pnl': -loss, 
                            'result': 'LOSS'
                        })
                        active_trades.remove(trade)
                        continue
                    
                    # التحقق من TP1
                    if not trade.get('tp1_hit') and current_price >= trade['tp1']:
                        profit_part = (trade['tp1'] - trade['entry']) * (trade['size'] * 0.4)
                        self.capital += profit_part
                        trade['tp1_hit'] = True
                        trade['sl'] = trade['entry']  # نقل إلى نقطة التعادل
                        self.trades_log.append({
                            **trade, 
                            'exit_price': trade['tp1'], 
                            'pnl': profit_part, 
                            'result': 'TP1', 
                            'size': trade['size']*0.4
                        })
                        
                    # التحقق من TP2
                    if trade.get('tp1_hit') and not trade.get('tp2_hit') and current_price >= trade['tp2']:
                        profit_part = (trade['tp2'] - trade['entry']) * (trade['size'] * 0.35)
                        self.capital += profit_part
                        trade['tp2_hit'] = True
                        self.trades_log.append({
                            **trade, 
                            'exit_price': trade['tp2'], 
                            'pnl': profit_part, 
                            'result': 'TP2', 
                            'size': trade['size']*0.35
                        })

                    # التحقق من TP3 (Trailing Stop)
                    if trade.get('tp2_hit') and not trade.get('closed') and current_price <= trade['sl']:
                        profit_part = (current_price - trade['entry']) * (trade['size'] * 0.25)
                        self.capital += profit_part
                        trade['closed'] = True
                        self.trades_log.append({
                            **trade, 
                            'exit_price': current_price, 
                            'pnl': profit_part, 
                            'result': 'TP3_TRAIL', 
                            'size': trade['size']*0.25
                        })
                        active_trades.remove(trade)

                # البحث عن دخول جديد
                if len(active_trades) < 3:  # حد أقصى 3 صفقات متزامنة
                    signal = self.validate_entry(symbol, df_5m, df_15m)
                    if signal:
                        risk_amt = self.capital * self.config['risk_per_trade']
                        dist_to_sl = signal['entry'] - signal['sl']
                        if dist_to_sl <= 0:
                            continue
                        size = (risk_amt * signal['leverage']) / dist_to_sl
                        
                        new_trade = {
                            **signal,
                            'size': size,
                            'tp1_hit': False,
                            'tp2_hit': False,
                            'closed': False,
                            'open_time': i
                        }
                        active_trades.append(new_trade)

        # إغلاق الصفقات المتبقية
        for trade in active_trades:
            last_price = data_dict[trade['symbol']]['5m'].iloc[-1]['close']
            pnl = (last_price - trade['entry']) * trade['size']
            self.capital += pnl
            self.trades_log.append({
                **trade, 
                'exit_price': last_price, 
                'pnl': pnl, 
                'result': 'CLOSE_END'
            })

        self.print_report()

    def print_report(self):
        """طباعة تقرير مفصل عن النتائج"""
        wins = [t for t in self.trades_log if t['pnl'] > 0]
        losses = [t for t in self.trades_log if t['pnl'] <= 0]
        
        total_pnl = self.capital - self.initial_capital
        win_rate = (len(wins) / len(self.trades_log)) * 100 if self.trades_log else 0
        
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses and sum(t['pnl'] for t in losses) != 0 else float('inf')

        print("\n" + "="*50)
        print(f"💰 FINAL CAPITAL: ${self.capital:.2f}")
        print(f"📈 TOTAL PNL: ${total_pnl:.2f} ({(total_pnl/self.initial_capital)*100:.2f}%)")
        print(f"📊 TOTAL TRADES: {len(self.trades_log)}")
        print(f"✅ WINS: {len(wins)} | ❌ LOSSES: {len(losses)}")
        print(f"🎯 WIN RATE: {win_rate:.2f}%")
        print(f"💵 AVG WIN: ${avg_win:.2f} | 💸 AVG LOSS: ${avg_loss:.2f}")
        print(f"📊 PROFIT FACTOR: {profit_factor:.2f}")
        print("="*50)
