"""
النقطة الرئيسية لتشغيل بوت السكالبر
"""
from modes.scalper import ScalperBot

def main():
    print("=" * 50)
    print("🎯 بوت السكالبر - استراتيجية القناص المتوازن")
    print("=" * 50)
    
    bot = ScalperBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ حدث خطأ غير متوقع: {e}")

if __name__ == "__main__":
    main()
