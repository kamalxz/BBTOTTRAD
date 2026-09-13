# run_scalper_backtest.py - سكريبت تشغيل الباك تيست
import pandas as pd
import os
from modes.scalper import ScalperBot
from config import SYMBOLS_CONFIG

def load_data(symbol):
    """
    تحميل البيانات من ملفات CSV المحلية.
    ملاحظة: يجب أن تكون الملفات موجودة في نفس المجلد.
    اسم الملف المتوقع: btc_usdt_5m.csv, eth_usdt_5m.csv ...
    أو btc_60days_5m.csv لـ BTC
    """
    # تنظيف اسم العملة ليكون مناسباً لاسم الملف
    clean_name = symbol.split('/')[0].replace('/', '_').replace(':USDT', '').lower()
    
    file_5m = f"{clean_name}_5m_data.csv"
    
    # محاولة تحميل ملف عام إذا كان الاسم مختلفاً
    if not os.path.exists(file_5m):
        if os.path.exists("btc_60days_5m.csv") and "BTC" in symbol:
            file_5m = "btc_60days_5m.csv"
        elif os.path.exists(f"{clean_name}_5m.csv"):
            file_5m = f"{clean_name}_5m.csv"
        else:
            print(f"⚠️ File not found for {symbol}: {file_5m}")
            return None

    try:
        df_5m = pd.read_csv(file_5m)
        
        # التحقق من أسماء الأعمدة وتعديلها إذا لزم الأمر
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        # إذا كانت الأعمدة بأسماء مختلفة، نحاول تعيينها
        if not all(col in df_5m.columns for col in required_cols):
            # نفترض الترتيب الشائع: timestamp, open, high, low, close, volume
            if len(df_5m.columns) >= 6:
                df_5m.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] + list(df_5m.columns[6:])
            else:
                print(f"❌ Columns mismatch for {symbol}. Found: {df_5m.columns.tolist()}")
                return None
        
        # إنشاء فريم 15 دقيقة من 5 دقائق (Resample)
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
        
        # إعادة تعيين الفهرس
        df_5m.reset_index(drop=True, inplace=True)
        df_15m.reset_index(drop=True, inplace=True)

        return {'5m': df_5m, '15m': df_15m}
    except Exception as e:
        print(f"❌ Error loading {symbol}: {e}")
        return None

def main():
    bot = ScalperBot()
    data_dict = {}
    
    print("="*50)
    print("🔍 SCALPER BACKTEST ENGINE v2.0")
    print("="*50)
    print("\n📂 Loading local data files...")
    
    # قائمة العملات للاختبار
    test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT'] 
    
    for symbol in test_symbols:
        data = load_data(symbol)
        if data:
            data_dict[symbol] = data
            print(f"✅ Loaded {symbol} (5m: {len(data['5m'])} candles, 15m: {len(data['15m'])} candles)")
        else:
            print(f"⚠️ Skipped {symbol} (No data)")

    if not data_dict:
        print("\n❌ No data loaded! Please ensure CSV files exist in the directory.")
        print("Expected files: btc_60days_5m.csv, or [symbol]_5m_data.csv")
        return

    print("\n⏳ Running Backtest Engine...")
    print("-" * 50)
    bot.run_backtest(data_dict)

if __name__ == "__main__":
    main()
