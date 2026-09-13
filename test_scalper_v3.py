import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print('📥 جاري تحميل بيانات BTC/USDT الحقيقية من بينانس (6 أشهر)...')
exchange = ccxt.binance()
timeframe_5m = '5m'
timeframe_15m = '15m'
limit = 60 * 24 * 180  # 6 أشهر تقريباً

try:
    ohlcv_5m = exchange.fetch_ohlcv('BTC/USDT', timeframe_5m, limit=limit)
    ohlcv_15m = exchange.fetch_ohlcv('BTC/USDT', timeframe_15m, limit=limit)
    
    df_5m = pd.DataFrame(ohlcv_5m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'], unit='ms')
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    
    print(f'✅ تم تحميل {len(df_5m)} شمعة 5د و {len(df_15m)} شمعة 15د.')
except Exception as e:
    print(f'❌ خطأ في التحميل: {e}')
    print('جاري استخدام بيانات بديلة...')
    dates = pd.date_range(start='2023-01-01', periods=50000, freq='5min')
    df_5m = pd.DataFrame({'timestamp': dates, 'open': 30000, 'high': 30100, 'low': 29900, 'close': 30050, 'volume': 1000})
    df_15m = df_5m.resample('15min', on='timestamp').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()

def calculate_indicators(df):
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['vol_ma'] = df['volume'].rolling(20).mean()
    return df

df_5m = calculate_indicators(df_5m)
df_15m = calculate_indicators(df_15m)

class SmartScalper:
    def __init__(self, initial_capital=1000):
        self.capital = initial_capital
        self.trades = []
        self.max_leverage = 10.0
        
    def get_dynamic_leverage(self, score):
        if score > 85: return 10.0
        elif score > 75: return 7.0
        elif score > 60: return 4.0
        else: return 1.0

    def check_entry(self, idx, row_5m, row_15m):
        if idx < 200 or pd.isna(row_5m['rsi']) or pd.isna(row_15m['ema_50']): 
            return None
        
        trend_up = row_15m['close'] > row_15m['ema_50']
        trend_down = row_15m['close'] < row_15m['ema_50']
        
        rsi_buy = 40 < row_5m['rsi'] < 65
        rsi_sell = 35 < row_5m['rsi'] < 60
        
        vol_ok = row_5m['volume'] > row_5m['vol_ma'] * 1.2
        
        score = 0
        signal = None
        
        if trend_up and rsi_buy and vol_ok:
            score += 40
            if row_5m['close'] > row_5m['ema_50']: score += 20
            if row_5m['rsi'] > 50: score += 20
            if row_5m['close'] > row_5m['open']: score += 20
            if score >= 60: signal = 'BUY'
            
        elif trend_down and rsi_sell and vol_ok:
            score += 40
            if row_5m['close'] < row_5m['ema_50']: score += 20
            if row_5m['rsi'] < 50: score += 20
            if row_5m['close'] < row_5m['open']: score += 20
            if score >= 60: signal = 'SELL'
            
        if signal:
            leverage = self.get_dynamic_leverage(score)
            atr = row_5m['atr']
            if pd.isna(atr): atr = (row_5m['high'] - row_5m['low']) # Fallback
            
            sl_dist = atr * 1.5
            tp1_dist = atr * 1.0
            tp2_dist = atr * 2.0
            tp3_dist = atr * 3.5
            
            return {
                'type': signal,
                'entry': row_5m['close'],
                'sl': row_5m['close'] - sl_dist if signal == 'BUY' else row_5m['close'] + sl_dist,
                'tp1': row_5m['close'] + tp1_dist if signal == 'BUY' else row_5m['close'] - tp1_dist,
                'tp2': row_5m['close'] + tp2_dist if signal == 'BUY' else row_5m['close'] - tp2_dist,
                'tp3': row_5m['close'] + tp3_dist if signal == 'BUY' else row_5m['close'] - tp3_dist,
                'leverage': leverage,
                'score': score,
                'time': row_5m['timestamp']
            }
        return None

    def run_backtest(self, df_5m, df_15m):
        df_15m.set_index('timestamp', inplace=True)
        
        in_trade = False
        trade_details = {}
        
        for i in range(200, len(df_5m)):
            row_5m = df_5m.iloc[i]
            t_15m = row_5m['timestamp'] - timedelta(minutes=(row_5m['timestamp'].minute % 15))
            try:
                row_15m = df_15m.loc[t_15m]
            except:
                continue

            if not in_trade:
                signal = self.check_entry(i, row_5m, row_15m)
                if signal:
                    in_trade = True
                    trade_details = {
                        'entry': signal['entry'],
                        'type': signal['type'],
                        'sl': signal['sl'],
                        'tp1': signal['tp1'],
                        'tp2': signal['tp2'],
                        'tp3': signal['tp3'],
                        'leverage': signal['leverage'],
                        'start_cap': self.capital,
                        'size': (self.capital * signal['leverage']) / signal['entry'],
                        'tp1_hit': False,
                        'tp2_hit': False,
                        'highest_pnl': 0
                    }
            else:
                current_price = row_5m['close']
                pnl_pct = 0
                
                if trade_details['type'] == 'BUY':
                    pnl_pct = (current_price - trade_details['entry']) / trade_details['entry']
                    if pnl_pct > trade_details['highest_pnl']:
                        trade_details['highest_pnl'] = pnl_pct
                    
                    exit_reason = None
                    exit_price = current_price
                    
                    if current_price <= trade_details['sl']:
                        exit_reason = 'SL'
                    elif trade_details['tp1_hit']:
                        trailing_sl = trade_details['entry'] * (1 + (trade_details['highest_pnl'] * 0.5))
                        if current_price <= trailing_sl:
                            exit_reason = 'Trailing SL'
                            exit_price = trailing_sl
                    elif current_price >= trade_details['tp3']:
                        exit_reason = 'TP3'
                    
                    if current_price >= trade_details['tp1'] and not trade_details['tp1_hit']:
                        trade_details['tp1_hit'] = True
                        trade_details['sl'] = trade_details['entry'] * 1.001

                    if exit_reason:
                        in_trade = False
                        final_pnl_pct = pnl_pct
                        if exit_reason == 'TP3': final_pnl_pct = (trade_details['tp3'] - trade_details['entry']) / trade_details['entry']
                        elif exit_reason == 'Trailing SL': final_pnl_pct = (exit_price - trade_details['entry']) / trade_details['entry']
                        elif exit_reason == 'SL': final_pnl_pct = (trade_details['sl'] - trade_details['entry']) / trade_details['entry']
                        
                        profit = final_pnl_pct * trade_details['size'] * trade_details['entry']
                        self.capital += profit
                        self.trades.append({
                            'type': trade_details['type'],
                            'entry': trade_details['entry'],
                            'exit': exit_price if exit_reason != 'TP3' else trade_details['tp3'],
                            'pnl': profit,
                            'leverage': trade_details['leverage'],
                            'reason': exit_reason
                        })

                elif trade_details['type'] == 'SELL':
                    pnl_pct = (trade_details['entry'] - current_price) / trade_details['entry']
                    if pnl_pct > trade_details['highest_pnl']:
                        trade_details['highest_pnl'] = pnl_pct
                        
                    exit_reason = None
                    exit_price = current_price

                    if current_price >= trade_details['sl']:
                        exit_reason = 'SL'
                    elif trade_details['tp1_hit']:
                        trailing_sl = trade_details['entry'] * (1 - (trade_details['highest_pnl'] * 0.5))
                        if current_price >= trailing_sl:
                            exit_reason = 'Trailing SL'
                            exit_price = trailing_sl
                    elif current_price <= trade_details['tp3']:
                        exit_reason = 'TP3'
                    
                    if current_price <= trade_details['tp1'] and not trade_details['tp1_hit']:
                        trade_details['tp1_hit'] = True
                        trade_details['sl'] = trade_details['entry'] * 0.999

                    if exit_reason:
                        in_trade = False
                        final_pnl_pct = pnl_pct
                        if exit_reason == 'TP3': final_pnl_pct = (trade_details['entry'] - trade_details['tp3']) / trade_details['entry']
                        elif exit_reason == 'Trailing SL': final_pnl_pct = (trade_details['entry'] - exit_price) / trade_details['entry']
                        elif exit_reason == 'SL': final_pnl_pct = (trade_details['entry'] - trade_details['sl']) / trade_details['entry']

                        profit = final_pnl_pct * trade_details['size'] * trade_details['entry']
                        self.capital += profit
                        self.trades.append({
                            'type': trade_details['type'],
                            'entry': trade_details['entry'],
                            'exit': exit_price if exit_reason != 'TP3' else trade_details['tp3'],
                            'pnl': profit,
                            'leverage': trade_details['leverage'],
                            'reason': exit_reason
                        })

        return self.capital, self.trades

bot = SmartScalper(initial_capital=1000)
final_cap, trades = bot.run_backtest(df_5m, df_15m)

total_profit = final_cap - 1000
win_trades = [t for t in trades if t['pnl'] > 0]
loss_trades = [t for t in trades if t['pnl'] <= 0]
win_rate = (len(win_trades) / len(trades) * 100) if trades else 0
avg_win = np.mean([t['pnl'] for t in win_trades]) if win_trades else 0
avg_loss = np.mean([t['pnl'] for t in loss_trades]) if loss_trades else 0

print('\n' + '='*60)
print('🏆 نتائج باكتيست القناص الذكي (Smart Scalper v3)')
print('='*60)
print(f'💰 رأس المال الأولي: $1000')
print(f'💵 رأس المال النهائي: ${final_cap:.2f}')
print(f'📈 صافي الربح: ${total_profit:.2f} ({(total_profit/1000)*100:.2f}%)')
print(f'🔢 عدد الصفقات: {len(trades)}')
print(f'✅ الصفقات الرابحة: {len(win_trades)}')
print(f'❌ الصفقات الخاسرة: {len(loss_trades)}')
print(f'🎯 نسبة الفوز: {win_rate:.2f}%')
print(f'📊 متوسط الربح: ${avg_win:.2f}')
print(f'📉 متوسط الخسارة: ${avg_loss:.2f}')
if len(trades) > 0:
    avg_lev = np.mean([t['leverage'] for t in trades])
    print(f'🚀 متوسط الرافعة: {avg_lev:.2f}x')
print('='*60)
if len(trades) > 0:
    print('🔍 آخر 5 صفقات:')
    for t in trades[-5:]:
        status = 'WIN' if t['pnl'] > 0 else 'LOSS'
        print(f'  [{status}] {t["type"]} | Lev: {t["leverage"]}x | PnL: ${t["pnl"]:.2f} | Exit: {t["reason"]}')
else:
    print('⚠️ لم يتم فتح أي صفقات.')
