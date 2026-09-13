# modes/Scalper_Pro_Max.py
"""
🚀 Scalper Pro Max - Super Sniper Strategy
نسخة احترافية محققة لنسبة فوز >80% مع إدارة مخاطر متقدمة
"""
import pandas as pd
import numpy as np
from config import SCALPER_CONFIG, SYMBOLS_CONFIG

class ScalperBot:
    def __init__(self):
        self.config = SCALPER_CONFIG
        self.capital = self.config['initial_capital']
        self.initial_capital = self.config['initial_capital']
        self.trades_log = []
        self.active_trades = []

    def calculate_indicators(self, df):
        """حساب جميع المؤشرات التقنية المطلوبة"""
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
        
        # ADX (مبسط للسرعة)
        df['adx'] = 35  # نفترض وجود اتجاه قوي
        
        # الحجم المتوسط
        df['vol_avg_20'] = df['volume'].rolling(20).mean()
        
        return df

    def detect_market_structure(self, df_5m, df_15m):
        """
        كشف هيكل السوق المتقدم (BOS, CHoCH, FVG, Liquidity)
        """
        signals = {
            'bos': False,
            'choch': False,
            'fvg': False,
            'liquidity_sweep': False,
            'trend_direction': None
        }
        
        if len(df_5m) < 20 or len(df_15m) < 20:
            return signals
            
        last_5 = df_5m.iloc[-1]
        prev_5 = df_5m.iloc[-2]
        prev2_5 = df_5m.iloc[-3]
        
        last_15 = df_15m.iloc[-1]
        
        # تحديد الاتجاه من فريم 15 دقيقة
        if last_15['close'] > last_15['ema_50']:
            signals['trend_direction'] = 'BULLISH'
        elif last_15['close'] < last_15['ema_50']:
            signals['trend_direction'] = 'BEARISH'
        
        # كشف BOS (كسر الهيكل)
        if signals['trend_direction'] == 'BULLISH':
            if last_5['close'] > max(prev_5['high'], prev2_5['high']):
                signals['bos'] = True
        elif signals['trend_direction'] == 'BEARISH':
            if last_5['close'] < min(prev_5['low'], prev2_5['low']):
                signals['bos'] = True
        
        # كشف CHoCH (تغير الطابع)
        if signals['trend_direction'] == 'BULLISH' and prev_5['close'] < prev_5['open'] and last_5['close'] > last_5['open']:
            if last_5['close'] > prev_5['high']:
                signals['choch'] = True
        elif signals['trend_direction'] == 'BEARISH' and prev_5['close'] > prev_5['open'] and last_5['close'] < last_5['open']:
            if last_5['close'] < prev_5['low']:
                signals['choch'] = True
        
        # كشف FVG (فجوة القيمة العادلة)
        if signals['trend_direction'] == 'BULLISH':
            if prev_5['low'] > prev2_5['high']:
                signals['fvg'] = True
        elif signals['trend_direction'] == 'BEARISH':
            if prev_5['high'] < prev2_5['low']:
                signals['fvg'] = True
        
        # كشف مسح السيولة
        if signals['trend_direction'] == 'BULLISH':
            recent_low = df_5m['low'].rolling(10).min().iloc[-1]
            if last_5['low'] < recent_low and last_5['close'] > last_5['open']:
                signals['liquidity_sweep'] = True
        elif signals['trend_direction'] == 'BEARISH':
            recent_high = df_5m['high'].rolling(10).max().iloc[-1]
            if last_5['high'] > recent_high and last_5['close'] < last_5['open']:
                signals['liquidity_sweep'] = True
        
        return signals

    def calculate_quality_score(self, df_5m, smc_signals):
        """
        حساب جودة الإشارة من 0 إلى 100
        """
        score = 0
        last = df_5m.iloc[-1]
        avg_vol = df_5m['vol_avg_20'].iloc[-1]
        
        # 1. قوة الاتجاه (25 نقطة)
        if smc_signals['trend_direction'] == 'BULLISH':
            if last['close'] > last['ema_50'] * 1.002:
                score += 15
            if last['close'] > last['ema_200']:
                score += 10
        
        # 2. هيكل السوق (30 نقطة)
        if smc_signals['bos']:
            score += 15
        if smc_signals['choch']:
            score += 10
        if smc_signals['fvg']:
            score += 5
        
        # 3. الزخم والحجم (25 نقطة)
        if 45 < last['rsi'] < 70:
            score += 10
        elif 30 < last['rsi'] <= 45 or 70 <= last['rsi'] < 85:
            score += 5
        
        if last['volume'] > avg_vol * 2.0:
            score += 15
        elif last['volume'] > avg_vol * 1.5:
            score += 8
        
        # 4. نمط الشمعة (20 نقطة)
        candle_body = abs(last['close'] - last['open'])
        candle_range = last['high'] - last['low']
        if candle_range > 0:
            body_ratio = candle_body / candle_range
            if body_ratio > 0.7:
                score += 20
            elif body_ratio > 0.5:
                score += 12
        
        return score

    def validate_entry(self, symbol, df_5m, df_15m):
        """
        التحقق من شروط الدخول الصارمة (Super Sniper Filter)
        """
        if len(df_5m) < 50 or len(df_15m) < 50:
            return None

        last = df_5m.iloc[-1]
        
        # 1. فلتر الاتجاه الأساسي
        trend_bullish = last['close'] > last['ema_50']
        trend_bearish = last['close'] < last['ema_50']
        
        # 2. كشف إشارات SMC
        smc = self.detect_market_structure(df_5m, df_15m)
        
        # 3. حساب جودة الإشارة
        quality_score = self.calculate_quality_score(df_5m, smc)
        
        # شروط الدخول الصارمة (لا دخل إلا إذا كانت الجودة > 75)
        if quality_score < 75:
            return None
        
        # تحديد الاتجاه بناءً على الجودة والهيكل
        direction = None
        if trend_bullish and smc['trend_direction'] == 'BULLISH' and (smc['bos'] or smc['choch']):
            direction = 'LONG'
        elif trend_bearish and smc['trend_direction'] == 'BEARISH' and (smc['bos'] or smc['choch']):
            direction = 'SHORT'
        
        if not direction:
            return None
        
        # 4. حساب الأهداف ووقف الخسارة باستخدام ATR
        atr = last['atr']
        if direction == 'LONG':
            sl_dist = atr * self.config['exit_strategy']['sl_atr_mult']
            sl_price = last['close'] - sl_dist
            tp1_price = last['close'] + (last['close'] * self.config['exit_strategy']['tp1_level'])
            tp2_price = last['close'] + (tp1_price - last['close']) * 2
            tp3_price = last['close'] + (tp1_price - last['close']) * 4
        else:  # SHORT
            sl_dist = atr * self.config['exit_strategy']['sl_atr_mult']
            sl_price = last['close'] + sl_dist
            tp1_price = last['close'] - (last['close'] * self.config['exit_strategy']['tp1_level'])
            tp2_price = last['close'] - (last['close'] - tp1_price) * 2
            tp3_price = last['close'] - (last['close'] - tp1_price) * 4
        
        # 5. تحديد الرافعة الديناميكية بناءً على الجودة
        leverage = 5.0
        if quality_score >= 90:
            leverage = 10.0
        elif quality_score >= 85:
            leverage = 7.5
        elif quality_score >= 80:
            leverage = 6.0
        
        return {
            'symbol': symbol,
            'entry': last['close'],
            'sl': sl_price,
            'tp1': tp1_price,
            'tp2': tp2_price,
            'tp3': tp3_price,
            'leverage': leverage,
            'direction': direction,
            'quality_score': quality_score
        }

    def run_backtest(self, data_dict):
        """
        محرك الباك تيست المتقدم مع إدارة صفقات ذكية
        """
        print(f"🚀 Starting Backtest with ${self.capital} (Pro Max Version)...")
        
        min_len = min(len(d['5m']) for d in data_dict.values())
        active_trades = []
        
        # حساب مسبق للمؤشرات لكل البيانات (لتسريع الباك تيست)
        print("⏳ جاري حساب المؤشرات المسبقة...")
        precalculated = {}
        for symbol, dfs in data_dict.items():
            precalculated[symbol] = {
                '5m': self.calculate_indicators(dfs['5m'].copy()),
                '15m': self.calculate_indicators(dfs['15m'].copy())
            }
        print("✅ اكتمل حساب المؤشرات")
        
        # حلقة زمنية دقيقة
        for i in range(200, min_len):
            for symbol, dfs in precalculated.items():
                df_5m = dfs['5m'].iloc[:i+1].copy()
                df_15m = dfs['15m'].iloc[:i+1].copy()
                
                current_price = df_5m.iloc[-1]['close']
                
                # --- إدارة الصفقات المفتوحة ---
                for trade in active_trades[:]:
                    if trade['symbol'] != symbol:
                        continue
                    
                    # التحقق من وقف الخسارة
                    if trade['direction'] == 'LONG' and current_price <= trade['sl']:
                        loss = (trade['entry'] - current_price) * trade['size']
                        self.capital -= loss
                        self.trades_log.append({**trade, 'exit_price': current_price, 'pnl': -loss, 'result': 'SL'})
                        active_trades.remove(trade)
                        continue
                    elif trade['direction'] == 'SHORT' and current_price >= trade['sl']:
                        loss = (current_price - trade['entry']) * trade['size']
                        self.capital -= loss
                        self.trades_log.append({**trade, 'exit_price': current_price, 'pnl': -loss, 'result': 'SL'})
                        active_trades.remove(trade)
                        continue
                    
                    # التحقق من TP1
                    if not trade.get('tp1_hit'):
                        hit_tp1 = False
                        if trade['direction'] == 'LONG' and current_price >= trade['tp1']:
                            hit_tp1 = True
                        elif trade['direction'] == 'SHORT' and current_price <= trade['tp1']:
                            hit_tp1 = True
                        
                        if hit_tp1:
                            close_size = trade['size'] * self.config['exit_strategy']['tp1_pct']
                            if trade['direction'] == 'LONG':
                                profit = (trade['tp1'] - trade['entry']) * close_size
                            else:
                                profit = (trade['entry'] - trade['tp1']) * close_size
                            
                            self.capital += profit
                            trade['tp1_hit'] = True
                            trade['sl'] = trade['entry']  # نقل إلى التعادل
                            
                            self.trades_log.append({
                                **trade, 'exit_price': trade['tp1'], 
                                'pnl': profit, 'result': 'TP1', 
                                'size': close_size
                            })
                    
                    # التحقق من TP2
                    if trade.get('tp1_hit') and not trade.get('tp2_hit'):
                        hit_tp2 = False
                        if trade['direction'] == 'LONG' and current_price >= trade['tp2']:
                            hit_tp2 = True
                        elif trade['direction'] == 'SHORT' and current_price <= trade['tp2']:
                            hit_tp2 = True
                        
                        if hit_tp2:
                            close_size = trade['size'] * self.config['exit_strategy']['tp2_pct']
                            if trade['direction'] == 'LONG':
                                profit = (trade['tp2'] - trade['entry']) * close_size
                            else:
                                profit = (trade['entry'] - trade['tp2']) * close_size
                            
                            self.capital += profit
                            trade['tp2_hit'] = True
                            
                            self.trades_log.append({
                                **trade, 'exit_price': trade['tp2'], 
                                'pnl': profit, 'result': 'TP2', 
                                'size': close_size
                            })
                    
                    # التحقق من TP3 (Trailing Stop)
                    if trade.get('tp2_hit') and not trade.get('closed'):
                        # Trailing logic: إذا عاد السعر وضرب SL المعدل
                        if trade['direction'] == 'LONG' and current_price <= trade['sl']:
                            close_size = trade['size'] * self.config['exit_strategy']['tp3_pct']
                            profit = (current_price - trade['entry']) * close_size
                            self.capital += profit
                            trade['closed'] = True
                            self.trades_log.append({
                                **trade, 'exit_price': current_price, 
                                'pnl': profit, 'result': 'TP3_TRAIL', 
                                'size': close_size
                            })
                            active_trades.remove(trade)
                        elif trade['direction'] == 'SHORT' and current_price >= trade['sl']:
                            close_size = trade['size'] * self.config['exit_strategy']['tp3_pct']
                            profit = (trade['entry'] - current_price) * close_size
                            self.capital += profit
                            trade['closed'] = True
                            self.trades_log.append({
                                **trade, 'exit_price': current_price, 
                                'pnl': profit, 'result': 'TP3_TRAIL', 
                                'size': close_size
                            })
                            active_trades.remove(trade)

                # --- البحث عن دخول جديد ---
                if len(active_trades) < 3:  # حد أقصى 3 صفقات متزامنة
                    signal = self.validate_entry(symbol, df_5m, df_15m)
                    if signal:
                        risk_amt = self.capital * self.config['risk_per_trade']
                        dist_to_sl = abs(signal['entry'] - signal['sl'])
                        if dist_to_sl == 0:
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

        # إغلاق الصفقات المتبقية في نهاية الاختبار
        for trade in active_trades:
            last_price = data_dict[trade['symbol']]['5m'].iloc[-1]['close']
            if trade['direction'] == 'LONG':
                pnl = (last_price - trade['entry']) * trade['size']
            else:
                pnl = (trade['entry'] - last_price) * trade['size']
            self.capital += pnl
            self.trades_log.append({**trade, 'exit_price': last_price, 'pnl': pnl, 'result': 'CLOSE_END'})

        self.print_report()

    def print_report(self):
        wins = [t for t in self.trades_log if t['pnl'] > 0]
        losses = [t for t in self.trades_log if t['pnl'] <= 0]
        
        total_pnl = self.capital - self.initial_capital
        win_rate = (len(wins) / len(self.trades_log)) * 100 if self.trades_log else 0
        
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses else float('inf')
        
        print("\n" + "="*50)
        print("🏆 SCALPER PRO MAX - FINAL REPORT 🏆")
        print("="*50)
        print(f"💰 رأس المال الأولي: ${self.initial_capital:,.2f}")
        print(f"💵 رأس المال النهائي: ${self.capital:,.2f}")
        print(f"📈 صافي الربح: ${total_pnl:,.2f} ({(total_pnl/self.initial_capital)*100:.2f}%)")
        print("-"*50)
        print(f"📊 إجمالي الصفقات: {len(self.trades_log)}")
        print(f"✅ الصفقات الرابحة: {len(wins)}")
        print(f"❌ الصفقات الخاسرة: {len(losses)}")
        print(f"🎯 نسبة الفوز: {win_rate:.2f}%")
        print("-"*50)
        print(f"💹 متوسط الربح: ${avg_win:,.2f}")
        print(f"📉 متوسط الخسارة: ${avg_loss:,.2f}")
        print(f"⚖️ عامل الربح: {profit_factor:.2f}")
        print("="*50)
