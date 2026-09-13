import ccxt
import pandas as pd
import os
from datetime import datetime, timedelta
import time

# إعدادات التحميل
OUTPUT_DIR = '.'  # الحفظ في نفس المجلد
DAYS_TO_DOWNLOAD = 60  # عدد الأيام (60 يوم لتجنب حدود API الطويلة)
TIMEFRAMES = ['5m', '15m']

# قائمة العملات من config.py (نسخة مختصرة للسكريبت)
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'LTC/USDT', 'XRP/USDT',
    'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'HBAR/USDT',
    'ARB/USDT', 'OP/USDT',
    'LINK/USDT', 'ONDO/USDT', 'MKR/USDT',
    'TAO/USDT', 'RNDR/USDT', 'FET/USDT',
    'XLM/USDT', 'MATIC/USDT'
]

def fetch_ohlcv(symbol, timeframe, days):
    """تحميل البيانات من بينانس"""
    exchange = ccxt.binance()
    
    # حساب وقت البدء
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    since = int(start_time.timestamp() * 1000)
    
    print(f"⏳ جاري تحميل {symbol} ({timeframe})...")
    
    all_candles = []
    current_since = since
    
    while True:
        try:
            # جلب 1000 شمعة كحد أقصى في الطلب الواحد
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            
            if not candles:
                break
                
            all_candles.extend(candles)
            
            # تحديث وقت البدء للدفعة التالية
            last_timestamp = candles[-1][0]
            if last_timestamp >= int(end_time.timestamp() * 1000):
                break
                
            current_since = last_timestamp + 1
            
            # احترام حدود السرعة (Rate Limit)
            time.sleep(0.1) 
            
            print(f"   ... تم تحميل {len(all_candles)} شمعة حتى الآن")
            
        except Exception as e:
            print(f"❌ خطأ في {symbol}: {e}")
            break
            
    return all_candles

def save_to_csv(data, filename):
    """حفظ البيانات في CSV بالتنسيق المطلوب"""
    if not data:
        return False
        
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # تحويل timestamp إلى تاريخ مقروء (اختياري، لكن البوت يتعامل مع الأرقام أيضاً)
    # نحتفظ بـ timestamp كعمود أولي للبوت
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # إعادة ترتيب الأعمدة حسب طلب البوت
    # البوت يتوقع: timestamp, open, high, low, close, volume
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    df.to_csv(filename, index=False)
    return True

def main():
    print("🚀 بدء تحميل البيانات من Binance...")
    print(f"📅 الفترة: آخر {DAYS_TO_DOWNLOAD} يوم")
    print(f"💾 المسار: {os.path.abspath(OUTPUT_DIR)}\n")
    
    for symbol in SYMBOLS:
        clean_name = symbol.replace('/', '_').replace(':USDT', '').lower()
        
        # تحميل فريم 5 دقائق
        data_5m = fetch_ohlcv(symbol, '5m', DAYS_TO_DOWNLOAD)
        if data_5m:
            filename_5m = f"{clean_name}_5m_data.csv"
            save_to_csv(data_5m, os.path.join(OUTPUT_DIR, filename_5m))
            print(f"✅ تم حفظ {filename_5m} ({len(data_5m)} شمعة)\n")
        else:
            print(f"⚠️ فشل تحميل بيانات 5m لـ {symbol}\n")
            continue
            
        # ملاحظة: فريم 15 دقيقة سنقوم بإنشائه من 5 دقائق داخل البوت لضمان التطابق،
        # أو يمكننا تحميله منفصلاً إذا أردت. 
        # لتوفير الوقت والمساحة، سنعتمد على ميزة Resampling في البوت كما هو مبرمج سابقاً.
        # إذا أردت حفظه كملف منفصل، uncomment الكود التالي:
        """
        data_15m = fetch_ohlcv(symbol, '15m', DAYS_TO_DOWNLOAD)
        if data_15m:
            filename_15m = f"{clean_name}_15m_data.csv"
            save_to_csv(data_15m, os.path.join(OUTPUT_DIR, filename_15m))
            print(f"✅ تم حفظ {filename_15m} ({len(data_15m)} شمعة)\n")
        """
        
        # راحة قصيرة بين العملات لتجنب الحظر
        time.sleep(1)

    print("\n🎉 اكتمل التحميل! يمكنك الآن تشغيل الباك تيست.")

if __name__ == "__main__":
    main()
