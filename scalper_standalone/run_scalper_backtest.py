# run_scalper_backtest.py - سكريبت تشغيل الباك تيست الشامل
import pandas as pd
import os
from modes.Scalper_Pro_Max import ScalperBot
from config import SYMBOLS_CONFIG

def load_data(symbol):
    """
    تحميل البيانات من ملفات CSV المحلية.
    """
    # تنظيف اسم العملة ليكون مناسباً لاسم الملف
    clean_name = symbol.split('/')[0].replace('/', '_').replace(':USDT', '').lower()
    
    file_5m = f"{clean_name}_5m_data.csv"
    
    # محاولة تحميل ملف عام إذا كان الاسم مختلفاً
    if not os.path.exists(file_5m):
        if os.path.exists("btc_60days_5m.csv") and "BTC" in symbol:
            file_5m = "btc_60days_5m.csv"
        else:
            return None

    try:
        df_5m = pd.read_csv(file_5m)
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df_5m.columns for col in required_cols):
            df_5m.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'][:len(df_5m.columns)]
            
        # إنشاء فريم 15 دقيقة من 5 دقائق
        if 'timestamp' in df_5m.columns:
            df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
            df_5m.set_index('timestamp', inplace=True)
            
        df_15m = df_5m.resample('15T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        df_5m.reset_index(inplace=True, drop=True)
        df_15m.reset_index(inplace=True, drop=True)

        return {'5m': df_5m, '15m': df_15m}
    except Exception as e:
        print(f"❌ Error loading {symbol}: {e}")
        return None

def main():
    all_results = []
    
    print("="*60)
    print("🚀 STARTING SCALPER PRO MAX - FULL ANALYSIS")
    print("="*60)
    print(f"📊 Testing {len(SYMBOLS_CONFIG)} symbols...")
    print("-"*60)
    
    for symbol, info in SYMBOLS_CONFIG.items():
        print(f"\n🔍 Analyzing {symbol} ({info['type']})...")
        
        data = load_data(symbol)
        if not data:
            print(f"⚠️ Skipped {symbol} (No data file found)")
            continue
            
        print(f"✅ Data loaded: 5m={len(data['5m'])}, 15m={len(data['15m'])}")
        
        bot = ScalperBot()
        bot.run_backtest({symbol: data})
        
        # Extract results
        wins = [t for t in bot.trades_log if t['pnl'] > 0]
        losses = [t for t in bot.trades_log if t['pnl'] <= 0]
        total_trades = len(bot.trades_log)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        net_pnl = bot.capital - bot.initial_capital
        pnl_pct = (net_pnl / bot.initial_capital * 100) if bot.initial_capital > 0 else 0
        
        result = {
            'symbol': symbol,
            'type': info['type'],
            'trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'net_pnl': net_pnl,
            'pnl_pct': pnl_pct,
            'final_capital': bot.capital
        }
        all_results.append(result)
        
        print(f"📈 Result: {total_trades} trades, {win_rate:.1f}% win rate, ${net_pnl:.2f} ({pnl_pct:.2f}%)")

    # Display summary
    if not all_results:
        print("\n❌ No data available for any symbol!")
        return

    print("\n" + "="*60)
    print("🏆 TOP 5 SYMBOLS FOR SCALPER PRO MAX")
    print("="*60)
    
    # Sort by win rate (min 5 trades to be significant)
    qualified = [r for r in all_results if r['trades'] >= 5]
    if not qualified:
        qualified = all_results  # If no qualified, show all
        
    sorted_results = sorted(qualified, key=lambda x: (x['win_rate'], x['net_pnl']), reverse=True)
    
    print(f"{'Rank':<5} {'Symbol':<20} {'Type':<15} {'Trades':<8} {'Win Rate':<10} {'Net PNL':<12} {'PnL %':<10}")
    print("-"*80)
    
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"{i:<5} {r['symbol']:<20} {r['type']:<15} {r['trades']:<8} {r['win_rate']:>6.1f}%     ${r['net_pnl']:>8.2f}   {r['pnl_pct']:>6.2f}%")
    
    print("="*60)
    print("✅ Analysis Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
