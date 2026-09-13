"""
🚀 ALL-IN-ONE BOT v1.0
يدعم 5 أنماط تداول مختلفة — اختر الأنماغ عند بدء التشغيل
*1. SCALPER - فكرة "السرعة" ⚡️
*2. DAY TRADER - فكرة "النظافة" 👑
*3. SWING - فكرة "صيد الموجة" 🌊
*4. POSITION - فكرة "الاستثمار" 🏦
*5. NEWS TRADER - فكرة "الفوضى" 📰
"""
import sys

import config
from modes import ScalperBot, DayTraderBot, SwingTraderBot, PositionTraderBot, NewsTraderBot
from core.telegram_alerts import send_telegram_alert


class AllInOneBot:
    def __init__(self, mode: str = "swing"):
        self.mode = mode.lower()
        self.bot_name = self.get_mode_name()
        self.bot = self._build_bot()

    def get_mode_name(self) -> str:
        names = {
            "scalper": "⚡️ SCALPER - فكرة السرعة",
            "day": "👑 DAY TRADER - فكرة النظافة",
            "swing": "🌊 SWING - فكرة صيد الموجة",
            "position": "🏦 POSITION - فكرة الاستثمار",
            "news": "📰 NEWS TRADER - فكرة الفوضى",
        }
        return names.get(self.mode, names["swing"])

    def _build_bot(self):
        bots = {
            "scalper": ScalperBot,
            "day": DayTraderBot,
            "swing": SwingTraderBot,
            "position": PositionTraderBot,
            "news": NewsTraderBot,
        }
        return bots.get(self.mode, SwingTraderBot)()

    def start(self):
        msg = f"🚀 {self.bot_name} جاهز!\n🎯 الوضع: {'محاكاة' if config.DRY_RUN else 'حقيقي'}"
        send_telegram_alert(msg)
        self.bot.run()


def prompt_mode() -> str:
    print("\n" + "=" * 50)
    print("🎯 اختر نمط التداول:")
    print("1. SCALPER    - ⚡️ السرعة")
    print("2. DAY TRADER - 👑 النظافة")
    print("3. SWING      - 🌊 صيد الموجة")
    print("4. POSITION   - 🏦 الاستثمار")
    print("5. NEWS TRADER - 📰 الفوضى")
    print("=" * 50)
    choice = input("👉 اختر رقم النمط (1-5) [3]: ").strip()
    modes = {"1": "scalper", "2": "day", "3": "swing", "4": "position", "5": "news"}
    return modes.get(choice, "swing")


if __name__ == "__main__":
    mode = prompt_mode() if "--interactive" in sys.argv else config.DEFAULT_MODE
    AllInOneBot(mode=mode).start()
