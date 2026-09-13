#!/usr/bin/env python3
"""
سكريبت شامل لاختبار استراتيجية Scalper_Pro_Max على جميع العملات
وعرض تقرير مفصل لتحديد أفضل العملات للبوت.
"""

import pandas as pd
import os
import sys
from pathlib import Path

# إضافة المسار الحالي للـ sys.path
sys.path.insert(0, str(Path(__file__).parent))

from modes.Scalper_Pro_Max import ScalperBot
from config import SYMBOLS_CONFIG

def load_data_for_symbol(symbol):
    """تحميل البيانات للعملة المحددة"""
    clean_name = symbol.split('/')[0].replace('/', '_').replace(':USDT', '').lower()
    
    # قائمة بالأسماء المحتملة للملف
    possible_files = [
        f"{clean_name}_5m_data.csv",
        f"{clean_name}_5m.csv",
        f"btc_60days_5m.csv" if "BTC" in symbol else None
    ]
    
    file_path = None
    for fname in possible_files:
        if fname and os.path.exists(fname):
            file_path = fname
            break
    
    if not file_path:
        # محاولة البحث في المجلد الرئيسي
        parent_files = [f for f in os.listdir('..') if f.endswith('.csv') and clean_name in f.lower()]
        if parent_files:
            file_path = f"../{parent_files[0]}"
        elif "BTC" in symbol and os.path.exists("../btc_60days_5m.csv"):
            file_path = "../btc_60days_5m.csv"
        else:
            return None

    try:
        df_5m = pd.read_csv(file_path)
        
        # توحيد أسماء الأعمدة
        cols = df_5m.columns.tolist()
        if 'timestamp' not in cols:
            if len(cols) >= 6:
                df_5m.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] + cols[6:]
            elif len(cols) >= 5:
                df_5m.columns = ['open', 'high', 'low', 'close', 'volume'] + cols[5:]
        
        # إنشاء فريم 15 دقيقة
        if 'timestamp' in df_5m.columns:
            df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
            df_15m = df_5m.resample('15T', on='timestamp').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 
                'close': 'last', 'volume': 'sum'
            }).dropna()
        else:
            df_15m = df_5m.resample('15T').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 
                'close': 'last', 'volume': 'sum'
            }).dropna()
        
        return {'5m': df_5m, '15m': df_15m}
    except Exception as e:
        print(f"❌ خطأ في تحميل {symbol}: {e}")
        return None

def test_single_symbol(symbol, data):
    """اختبار عملة واحدة وإرجاع النتائج"""
    bot = ScalperBot()
    bot.capital = 1000  # رأس مال موحد للمقارنة
    bot.initial_capital = 1000
    
    try:
        bot.run_backtest({symbol: data})
        
        wins = [t for t in bot.trades_log if t['pnl'] > 0]
        losses = [t for t in bot.trades_log if t['pnl'] <= 0]
        
        total_trades = len(bot.trades_log)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        total_pnl = bot.capital - bot.initial_capital
        pnl_pct = (total_pnl / bot.initial_capital * 100) if bot.initial_capital > 0 else 0
        
        # حساب متوسط الربح والخسارة
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        # حساب عامل الربح
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        return {
            'symbol': symbol,
            'total_trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'pnl_pct': pnl_pct,
            'final_capital': bot.capital,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': 0  # يمكن حسابه بدقة أكبر إذا لزم الأمر
        }
    except Exception as e:
        print(f"❌ خطأ في اختبار {symbol}: {e}")
        return None

def main():
    print("="*70)
    print("🚀 بدء الاختبار الشامل لاستراتيجية Scalper_Pro_Max")
    print("="*70)
    print(f"📊 عدد العملات المراد اختبارها: {len(SYMBOLS_CONFIG)}")
    print("-"*70)
    
    results = []
    
    for i, (symbol, config) in enumerate(SYMBOLS_CONFIG.items(), 1):
        print(f"\n[{i}/{len(SYMBOLS_CONFIG)}] جاري اختبار: {symbol} ({config['type']})...")
        
        data = load_data_for_symbol(symbol)
        if data:
            print(f"   ✅ تم تحميل البيانات (5m: {len(data['5m'])}, 15m: {len(data['15m'])})")
            result = test_single_symbol(symbol, data)
            if result:
                results.append(result)
                status = "🟢 ممتاز" if result['win_rate'] >= 80 and result['total_pnl'] > 0 else \
                         "🟡 جيد" if result['win_rate'] >= 60 and result['total_pnl'] > 0 else \
                         "🔴 ضعيف"
                print(f"   📈 النتائج: {result['total_trades']} صفقة | فوز: {result['win_rate']:.1f}% | ربح: ${result['total_pnl']:.2f} ({status})")
            else:
                print(f"   ⚠️ فشل في تحليل النتائج")
        else:
            print(f"   ⚠️ لا توجد بيانات متاحة (تم التخطي)")
    
    if not results:
        print("\n❌ لم يتم العثور على أي بيانات للاختبار!")
        print("💡 تأكد من وجود ملفات CSV في المجلد الحالي أو المجلد الأب.")
        return
    
    # عرض التقرير النهائي
    print("\n" + "="*70)
    print("🏆 التقرير النهائي - ترتيب العملات حسب الأداء")
    print("="*70)
    
    # ترتيب حسب نسبة الفوز ثم الربح
    sorted_results = sorted(results, key=lambda x: (x['win_rate'], x['total_pnl']), reverse=True)
    
    print(f"\n{'الترتيب':<8} {'العملة':<20} {'الصفقات':<10} {'نسبة الفوز':<12} {'الربح $':<12} {'العامل':<10} {'التقييم':<10}")
    print("-"*94)
    
    for i, res in enumerate(sorted_results, 1):
        rating = "🟢 ممتاز" if res['win_rate'] >= 80 and res['total_pnl'] > 0 else \
                 "🟡 جيد" if res['win_rate'] >= 60 and res['total_pnl'] > 0 else \
                 "🔴 ضعيف"
        
        pf_str = f"{res['profit_factor']:.2f}" if res['profit_factor'] != float('inf') else "∞"
        
        print(f"{i:<8} {res['symbol']:<20} {res['total_trades']:<10} {res['win_rate']:>10.1f}%  {res['total_pnl']:>10.2f}$  {pf_str:>10}  {rating:<10}")
    
    # ملخص لأفضل العملات
    print("\n" + "="*70)
    print("💡 أفضل 5 عملات لاستراتيجية السكالبر:")
    print("="*70)
    
    top_5 = [r for r in sorted_results if r['win_rate'] >= 70 and r['total_pnl'] > 0][:5]
    
    if top_5:
        for i, res in enumerate(top_5, 1):
            print(f"\n{i}. {res['symbol']}")
            print(f"   ├── نسبة الفوز: {res['win_rate']:.1f}%")
            print(f"   ├── إجمالي الربح: ${res['total_pnl']:.2f} ({res['pnl_pct']:.1f}%)")
            print(f"   ├── عدد الصفقات: {res['total_trades']}")
            print(f"   └── عامل الربح: {res['profit_factor']:.2f}" if res['profit_factor'] != float('inf') else f"   └── عامل الربح: ∞")
    else:
        print("\n⚠️ لا توجد عملات حققت نسبة فوز >= 70% مع ربح موجب في هذه البيانات.")
    
    # حفظ النتائج في ملف CSV
    output_file = "backtest_results_all_symbols.csv"
    df_results = pd.DataFrame(sorted_results)
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 تم حفظ النتائج التفصيلية في ملف: {output_file}")
    
    print("\n" + "="*70)
    print("✅ اكتمل الاختبار بنجاح!")
    print("="*70)

if __name__ == "__main__":
    main()
