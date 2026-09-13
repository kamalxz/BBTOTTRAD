import pandas as pd
import numpy as np
from datetime import datetime

class ScalperBacktest:
    def __init__(self, df, initial_balance=10000):
        self.df = df.copy()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = None
        self.trades = []
        self.df['signal'] = 0
        self.df['entry_price'] = np.nan
        self.df['exit_price'] = np.nan
        self.df['pnl'] = np.nan
        self.df['trade_type'] = ''
        
    def calculate_indicators(self):
        df = self.df
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['swing_high'] = df['high'].rolling(5).max()
        df['swing_low'] = df['low'].rolling(5).min()
        return df
    
    def check_liquidity_sweep(self, idx):
        if idx < 5:
            return False
        current_low = self.df.loc[idx, 'low']
        current_high = self.df.loc[idx, 'high']
        prev_swing_low = self.df.loc[idx-5:idx-1, 'swing_low'].min()
        prev_swing_high = self.df.loc[idx-5:idx-1, 'swing_high'].max()
        sweep_long = current_low < prev_swing_low and self.df.loc[idx, 'close'] > prev_swing_low
        sweep_short = current_high > prev_swing_high and self.df.loc[idx, 'close'] < prev_swing_high
        return sweep_long or sweep_short
    
    def check_choc(self, idx):
        if idx < 10:
            return False
        recent_lows = self.df.loc[idx-10:idx, 'low'].values
        recent_highs = self.df.loc[idx-10:idx, 'high'].values
        bullish_choc = self.df.loc[idx, 'close'] > recent_highs[:-1].max()
        bearish_choc = self.df.loc[idx, 'close'] < recent_lows[:-1].min()
        return bullish_choc or bearish_choc
    
    def check_engulfing(self, idx):
        if idx < 1:
            return False
        prev_open = self.df.loc[idx-1, 'open']
        prev_close = self.df.loc[idx-1, 'close']
        curr_open = self.df.loc[idx, 'open']
        curr_close = self.df.loc[idx, 'close']
        bullish = (prev_close < prev_open and curr_close > curr_open and curr_open <= prev_close and curr_close >= prev_open)
        bearish = (prev_close > prev_open and curr_close < curr_open and curr_open >= prev_close and curr_close <= prev_open)
        return bullish or bearish
    
    def check_volume_spike(self, idx):
        if idx < 20:
            return False
        current_volume = self.df.loc[idx, 'volume']
        avg_volume = self.df.loc[idx, 'volume_ma']
        return current_volume > avg_volume * 1.5
    
    def run_backtest(self):
        print("جاري حساب المؤشرات...")
        self.df = self.calculate_indicators()
        print("جاري محاكاة الصفقات...")
        i = 50
        while i < len(self.df) - 10:
            row = self.df.iloc[i]
            if self.position is not None:
                self.check_exit(i)
                i += 1
                continue
            liquidity_sweep = self.check_liquidity_sweep(i)
            choc = self.check_choc(i)
            engulfing = self.check_engulfing(i)
            volume_spike = self.check_volume_spike(i)
            long_signal = liquidity_sweep and choc and engulfing and volume_spike and row['rsi'] < 40
            short_signal = liquidity_sweep and choc and engulfing and volume_spike and row['rsi'] > 60
            if long_signal:
                self.enter_trade(i, 'LONG')
            elif short_signal:
                self.enter_trade(i, 'SHORT')
            i += 1
        if self.position:
            self.close_trade(len(self.df) - 1, "End of Data")
        return self.generate_report()
    
    def enter_trade(self, idx, trade_type):
        entry_price = self.df.iloc[idx]['close']
        atr = self.df.iloc[idx]['atr']
        if atr is None or np.isnan(atr):
            atr = self.df.iloc[idx-10:idx]['atr'].mean()
            if np.isnan(atr):
                atr = 100
        if trade_type == 'LONG':
            sl = entry_price - (atr * 1.5)
            tp1 = entry_price + (atr * 1)
            tp2 = entry_price + (atr * 2)
            tp3 = entry_price + (atr * 3)
        else:
            sl = entry_price + (atr * 1.5)
            tp1 = entry_price - (atr * 1)
            tp2 = entry_price - (atr * 2)
            tp3 = entry_price - (atr * 3)
        self.position = {
            'entry_idx': idx, 'entry_price': entry_price, 'trade_type': trade_type,
            'sl': sl, 'tp1': tp1, 'tp2': tp2, 'tp3': tp3,
            'size': self.balance * 0.1
        }
        self.df.at[idx, 'signal'] = 1 if trade_type == 'LONG' else -1
        self.df.at[idx, 'entry_price'] = entry_price
    
    def check_exit(self, idx):
        current_price = self.df.iloc[idx]['close']
        pos = self.position
        exit_reason = None
        exit_price = None
        if pos['trade_type'] == 'LONG':
            if current_price <= pos['sl']:
                exit_price, exit_reason = pos['sl'], 'SL'
            elif current_price >= pos['tp3']:
                exit_price, exit_reason = pos['tp3'], 'TP3'
            elif current_price >= pos['tp2']:
                exit_price, exit_reason = pos['tp2'], 'TP2'
            elif current_price >= pos['tp1']:
                exit_price, exit_reason = pos['tp1'], 'TP1'
        else:
            if current_price >= pos['sl']:
                exit_price, exit_reason = pos['sl'], 'SL'
            elif current_price <= pos['tp3']:
                exit_price, exit_reason = pos['tp3'], 'TP3'
            elif current_price <= pos['tp2']:
                exit_price, exit_reason = pos['tp2'], 'TP2'
            elif current_price <= pos['tp1']:
                exit_price, exit_reason = pos['tp1'], 'TP1'
        if exit_reason:
            self.close_trade(idx, exit_reason, exit_price)
    
    def close_trade(self, idx, reason, exit_price=None):
        if exit_price is None:
            exit_price = self.df.iloc[idx]['close']
        pos = self.position
        if pos['trade_type'] == 'LONG':
            pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price'] * 100
        else:
            pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price'] * 100
        pnl_usd = pos['size'] * pnl_pct / 100
        self.balance += pnl_usd
        self.trades.append({
            'entry_idx': pos['entry_idx'], 'entry_price': pos['entry_price'],
            'exit_idx': idx, 'exit_price': exit_price, 'trade_type': pos['trade_type'],
            'exit_reason': reason, 'pnl_pct': pnl_pct, 'pnl_usd': pnl_usd, 'balance': self.balance
        })
        self.df.at[idx, 'exit_price'] = exit_price
        self.df.at[idx, 'pnl'] = pnl_pct
        self.df.at[idx, 'trade_type'] = reason
        self.position = None
    
    def generate_report(self):
        if not self.trades:
            return {'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0, 'win_rate': 0,
                    'total_pnl': 0, 'final_balance': self.balance, 'tp1_count': 0, 'tp2_count': 0,
                    'tp3_count': 0, 'sl_count': 0, 'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0,
                    'message': 'لم يتم العثور على صفقات تناسب الشروط الصارمة للاستراتيجية.'}
        trades_df = pd.DataFrame(self.trades)
        winning = trades_df[trades_df['pnl_pct'] > 0]
        losing = trades_df[trades_df['pnl_pct'] <= 0]
        tp1 = len(trades_df[trades_df['exit_reason'] == 'TP1'])
        tp2 = len(trades_df[trades_df['exit_reason'] == 'TP2'])
        tp3 = len(trades_df[trades_df['exit_reason'] == 'TP3'])
        sl = len(trades_df[trades_df['exit_reason'] == 'SL'])
        total_pnl = trades_df['pnl_usd'].sum()
        avg_win = winning['pnl_pct'].mean() if len(winning) > 0 else 0
        avg_loss = losing['pnl_pct'].mean() if len(losing) > 0 else 0
        gross_profit = winning['pnl_usd'].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing['pnl_usd'].sum()) if len(losing) > 0 else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        return {
            'total_trades': len(trades_df), 'winning_trades': len(winning),
            'losing_trades': len(losing), 'win_rate': len(winning) / len(trades_df) * 100,
            'total_pnl': total_pnl, 'total_pnl_pct': ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            'final_balance': self.balance, 'tp1_count': tp1, 'tp2_count': tp2, 'tp3_count': tp3, 'sl_count': sl,
            'avg_win': avg_win, 'avg_loss': avg_loss, 'profit_factor': profit_factor,
            'largest_win': trades_df['pnl_usd'].max(), 'largest_loss': trades_df['pnl_usd'].min(),
            'consecutive_wins': self.calc_consecutive(trades_df, True),
            'consecutive_losses': self.calc_consecutive(trades_df, False),
            'trades_detail': trades_df
        }
    
    def calc_consecutive(self, df, wins=True):
        series = (df['pnl_pct'] > 0).astype(int) if wins else (df['pnl_pct'] <= 0).astype(int)
        max_cons, current = 0, 0
        for val in series:
            if val == 1:
                current += 1
                max_cons = max(max_cons, current)
            else:
                current = 0
        return max_cons
    
    def print_report(self, report):
        print("\n" + "="*60)
        print("📊 تقرير أداء استراتيجية Scalping")
        print("="*60)
        if report['total_trades'] == 0:
            print(f"\n❌ {report['message']}")
            print("\n💡 نصيحة: الشروط الحالية صارمة جداً. يمكن:")
            print("   1. تخفيف شروط الدخول")
            print("   2. استخدام بيانات لفترة أطول")
            print("   3. اختبار نمط تداول آخر أقل صرامة")
            return
        print(f"\n💰 الرصيد الأولي: ${self.initial_balance:,.2f}")
        print(f"💵 الرصيد النهائي: ${report['final_balance']:,.2f}")
        print(f"📈 إجمالي الربح/الخسارة: ${report['total_pnl']:,.2f} ({report['total_pnl_pct']:.2f}%)")
        print(f"\n📊 إحصائيات الصفقات:")
        print(f"   إجمالي الصفقات: {report['total_trades']}")
        print(f"   ✅ الصفقات الرابحة: {report['winning_trades']}")
        print(f"   ❌ الصفقات الخاسرة: {report['losing_trades']}")
        print(f"   🎯 نسبة الفوز: {report['win_rate']:.2f}%")
        print(f"\n🎯 أهداف الربح:")
        print(f"   TP1: {report['tp1_count']} صفقات")
        print(f"   TP2: {report['tp2_count']} صفقات")
        print(f"   TP3: {report['tp3_count']} صفقات")
        print(f"   SL:  {report['sl_count']} صفقات")
        print(f"\n📈 متوسط الأداء:")
        print(f"   متوسط الربح: {report['avg_win']:.2f}%")
        print(f"   متوسط الخسارة: {report['avg_loss']:.2f}%")
        print(f"   Profit Factor: {report['profit_factor']:.2f}")
        print(f"\n🏆 أفضل وأسوأ صفقة:")
        print(f"   أكبر ربح: ${report['largest_win']:,.2f}")
        print(f"   أكبر خسارة: ${report['largest_loss']:,.2f}")
        print(f"\n📊 التوالي:")
        print(f"   أكبر عدد فوز متتالي: {report['consecutive_wins']}")
        print(f"   أكبر عدد خسارة متتالية: {report['consecutive_losses']}")
        print("\n" + "="*60)
        if len(report['trades_detail']) > 0:
            print("\n📋 تفاصيل أول 10 صفقات:")
            detail = report['trades_detail'].head(10)
            for idx, row in detail.iterrows():
                emoji = "✅" if row['pnl_pct'] > 0 else "❌"
                print(f"   {emoji} {row['trade_type']} | Entry: ${row['entry_price']:,.2f} | Exit: ${row['exit_price']:,.2f} | {row['exit_reason']} | PnL: {row['pnl_pct']:.2f}% (${row['pnl_usd']:.2f})")

if __name__ == "__main__":
    print("🚀 بدء باك تيست استراتيجية Scalping على بيانات Binance الحقيقية")
    print("-" * 60)
    df = pd.read_csv('btc_usdt_5m_data.csv')
    print(f"✅ تم تحميل {len(df)} شمعة")
    print(f"📅 الفترة: {df['timestamp'].min()} إلى {df['timestamp'].max()}")
    backtest = ScalperBacktest(df, initial_balance=10000)
    report = backtest.run_backtest()
    backtest.print_report(report)
    if report['total_trades'] > 0:
        report['trades_detail'].to_csv('scalper_trades_detail.csv', index=False)
        print(f"\n💾 تم حفظ تفاصيل الصفقات في scalper_trades_detail.csv")
