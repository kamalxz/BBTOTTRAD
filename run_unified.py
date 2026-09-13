"""
🚀 run_unified.py — نقطة دخول موحدة بسيطة لتشغيل النظام
يدعم التشغيل التلقائي ونظام التحكم بالتلغرام
"""
import sys
import os
import argparse
import logging

# إصلاح ترميز Windows
if sys.stdout.encoding in ("cp1252", "cp1256"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_unified as config
from core.unified_logging import setup_logging
setup_logging(config.LOG_LEVEL)

from telegram_control import TelegramBotController
from unified_trading_system import UnifiedTradingSystem


def main():
    parser = argparse.ArgumentParser(description="🚀 نظام التداول الموحد v2.0")
    parser.add_argument("--mode", "-m", default="swing",
                       choices=["scalping", "day", "swing", "position_spot", "position_futures", "news"],
                       help="وضع التداول")
    parser.add_argument("--capital", "-c", type=float, default=100.0,
                       help="رأس المال الأولي (USDT)")
    parser.add_argument("--telegram", "-t", action="store_true",
                       help="تفعيل نظام التحكم بالتلغرام")
    parser.add_argument("--continuous", action="store_true",
                       help="تشغيل المسح المستمر")
    parser.add_argument("--scan", type=str, default=None,
                       help="مسح رمز محدد (مثال: BTCUSDT)")
    parser.add_argument("--backtest", action="store_true",
                       help="تشغيل نظام الباك تيست")
    parser.add_argument("--interval", type=int, default=60,
                       help="فاصل المسح المستمر (ثواني)")
    
    args = parser.parse_args()
    
    print("🚀 تشغيل نظام التداول الموحد v2.0")
    print("=" * 50)
    
    if args.telegram:
        print("📱 تشغيل نظام التحكم بالتلغرام...")
        controller = TelegramBotController()
        if controller.token:
            controller.start()
            print("✅ نظام التحكم بالتلغرام نشط")
            print("📱 أرسل /start إلى بوت التلغرام للبدء")
            print("🛑 للإيقاف: Ctrl+C")
            
            try:
                while True:
                    import time
                    time.sleep(30)
            except KeyboardInterrupt:
                print("\n🛑 إيقاف النظام...")
                controller.stop()
        else:
            print("❌ TELEGRAM_TOKEN غير محدد في .env")
            print("   الرجاء إضافته ثم المحاولة مرة أخرى")
        return
    
    # إنشاء النظام الموحد
    system = UnifiedTradingSystem(mode=args.mode, account_equity=args.capital)
    print(f"✅ النظام جاهز — الوضع: {args.mode}، رأس المال: {args.capital} USDT")
    
    if args.scan:
        print(f"\n🔍 مسح {args.scan}...")
        result = system.run_scan(args.scan)
        print(f"النتيجة: {result['status']}")
        if result['status'] == 'trade_signal':
            sig = result['signal']
            print(f"  اتجاه: {sig['side']}")
            print(f"  الدخول: {sig['entry_price']:.2f}")
            print(f"  SL: {sig['sl_price']:.2f}")
            print(f"  TP: {sig['tp_price']:.2f}")
            print(f"  R:R: {sig['rr']:.2f}:1")
            print(f"  النقاط: {result['score']}/10")
        elif result['status'] == 'no_trade':
            print(f"  NO TRADE — النقاط: {result.get('score', 0)}/10")
            print(f"  الأسباب: {result.get('reasons', [])}")
    elif args.continuous:
        print(f"\n🔄 مسح مستمر كل {args.interval} ثانية...")
        system.run_continuous(symbols=config.SYMBOLS, interval=args.interval)
    elif args.backtest:
        print("\n🔬 تشغيل نظام الباك تيست...")
        from core.unified_backtester import UnifiedBacktester
        from core.exchange import BinanceExchange
        import pandas as pd
        
        exchange = BinanceExchange()
        symbols = config.SYMBOLS if hasattr(config, 'SYMBOLS') else ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for symbol in symbols[:1]:  # اختبار للرمز الأول فقط
            try:
                data = exchange.fetch_ohlcv(symbol, "1h", 200)
                df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
                backtester = UnifiedBacktester(mode=args.mode, initial_capital=args.capital)
                result = backtester.run_backtest(df)
                print(f"\n📊 نتائج الباك تيست لـ {symbol}:")
                backtester.print_report()
            except Exception as e:
                print(f"❌ خطأ في الباك تيست لـ {symbol}: {e}")
    else:
        # وضع تفاعلي افتراضي
        print("\n📋 نظام التداول الموحد جاهز")
        print("استخدم --telegram لتفعيل التحكم بالتلغرام")
        print("استخدم --scan BTCUSDT للمسح الفوري")
        print("استخدم --continuous للمسح المستمر")
        print("استخدم --backtest لتشغيل الباك تيست")
        
        # بدء المسح المستمر افتراضيًا
        system.run_continuous(symbols=config.SYMBOLS, interval=60)


if __name__ == "__main__":
    main()
