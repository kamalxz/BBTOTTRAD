#!/usr/bin/env python3
"""
سكربت اختبار استراتيجية السكالبر المتطورة
يعمل على البيانات المحلية (CSV) لمدة 60 يوم
"""

import pandas as pd
import numpy as np
import sys
import os

# إضافة المسار الحالي للـ Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modes.scalper import ScalperBot
from config import SCALPER_CONFIG

def load_data(symbol):
    """
    تحميل البيانات من ملفات CSV المحلية
    """
    # تنظيف اسم العملة ليكون مناسباً لاسم الملف
    clean_name = symbol.split('/')[0].replace('/', '_').replace(':USDT', '').lower()
    
    # محاولة تحميل ملف BTC الرئيسي
    if 'BTC' in symbol:
        file_5m = "btc_60days_5m.csv"
    else:
        file_5m = f"{clean_name}_5m_data.csv"
    
    if not os.path.exists(file_5m):
        print(f"⚠️ File not found for {symbol}: {file_5m}")
        return None

    try:
        df_5m = pd.read_csv(file_5m)
        
        # التحقق من أسماء الأعمدة المطلوبة
        required_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        
        # التأكد من وجود جميع الأعمدة المطلوبة
        missing_cols = [col for col in required_cols if col not in df_5m.columns]
        if missing_cols:
            print(f"❌ Missing columns in {file_5m}: {missing_cols}")
            print(f"   Available columns: {df_5m.columns.tolist()}")
            return None
        
        # تحويل timestamp إلى datetime
        df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
        
        # إنشاء فريم 15 دقيقة من 5 دقائق (Resample)
        df_15m = df_5m.set_index('timestamp').resample('15T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        # إعادة تعيين الفهرس
        df_5m.reset_index(drop=True, inplace=True)
        df_15m.reset_index(drop=True, inplace=True)
        
        print(f"✅ Loaded {symbol}: 5m={len(df_5m)} candles, 15m={len(df_15m)} candles")
        return {'5m': df_5m, '15m': df_15m}
        
    except Exception as e:
        print(f"❌ Error loading {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None

def print_report(results):
    """طباعة تقرير مفصل"""
    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS")
    print("="*70)
    print(f"💰 Initial Capital:     ${results['initial_capital']:,.2f}")
    print(f"💵 Final Capital:       ${results['final_capital']:,.2f}")
    print(f"📈 Total PnL:           ${results['total_pnl']:,.2f} ({results['total_pnl_pct']:.2f}%)")
    print("-"*70)
    print(f"📊 Total Trades:        {results['total_trades']}")
    print(f"✅ Winning Trades:      {results['winning_trades']}")
    print(f"❌ Losing Trades:       {results['losing_trades']}")
    print(f"🎯 Win Rate:            {results['win_rate']:.2f}%")
    print("-"*70)
    print(f"💹 Avg Win:             ${results['avg_win']:,.2f}")
    print(f"📉 Avg Loss:            ${results['avg_loss']:,.2f}")
    print(f"📊 Profit Factor:       {results['profit_factor']:.2f}")
    print(f"📉 Max Drawdown:        {results['max_drawdown']:.2f}%")
    print("="*70)

def main():
    print("="*60)
    print("🚀 SCALPER BACKTEST ENGINE - LOCAL DATA")
    print("="*60)
    
    bot = ScalperBot()
    data_dict = {}
    
    print("\n📂 Loading local data files...")
    
    # نختبر BTC فقط لتوفير الوقت (يمكن إضافة عملات أخرى)
    test_symbols = ['BTC/USDT:USDT']
    
    for symbol in test_symbols:
        data = load_data(symbol)
        if data:
            data_dict[symbol] = data
    
    if not data_dict:
        print("\n❌ No data loaded! Please ensure CSV files exist.")
        print("Expected file: btc_60days_5m.csv")
        return
    
    print(f"\n⏳ Running Backtest on {len(data_dict)} symbols...")
    initial_capital = SCALPER_CONFIG.get('initial_capital', 1000.0)
    print(f"   Initial Capital: ${initial_capital}")
    print(f"   Max Leverage: {SCALPER_CONFIG.get('max_leverage', 10)}x")
    print(f"   Risk per Trade: {SCALPER_CONFIG.get('risk_per_trade', 0.02)*100}%")
    print("-"*60)
    
    # تشغيل الباك تيست لكل عملة
    for symbol, data in data_dict.items():
        print(f"\n🔍 Testing {symbol}...")
        results = bot.backtest_multi_timeframe(
            df_5m=data['5m'],
            df_15m=data['15m'],
            initial_capital=initial_capital
        )
        print_report(results)
    
    print("\n" + "="*60)
    print("✅ BACKTEST COMPLETED")
    print("="*60)

if __name__ == "__main__":
    main()
