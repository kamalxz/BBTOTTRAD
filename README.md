# 🚀 نظام التداول الموحد v2.0

## 📋 نظرة عامة
نظام تداول آلي متكامل يدعم 6 أنماط تداول مختلفة باستخدام منهجية **Smart Money Concepts (SMC)** مع منظومة حماية متعددة الطبقات.

**🎯 هدف النظام: تحقيق 90% نجاح الصفقات** عبر:
- NO TRADE Engine (11 فلتر رفض)
- Score Engine (Score < 7 → لا تداول)
- Risk Management متعدد الطبقات
- التحليل SMC الكامل (BOS, CHOCH, FVG, OB, Liquidity)

---

## 🎮 كيفية التشغيل

### الطريقة المفضلة: عبر التلغرام
```bash
python telegram_control.py
```
بعد التشغيل، أرسل أي أمر إلى بوت التلغرام:
```
/start          → عرض القائمة
/help           → جميع الأوامر
/scan BTCUSDT   → مسح فوري للرمز
/start_swing    → تشغيل Swing Trader
/start_all      → تشغيل جميع البوتات
/stop_all       → إيقاف الكل
/status         → حالة البوتات
/dca 100 60000  → حساب مستويات DCA
/pnl 50000 52000 0.002 → حساب P&L
```

### التشغيل المباشر:
```bash
python unified_trading_system.py     # النظام الموحد
python main.py                       # القائمة الرئيسية (9 خيارات + تلغرام)
python run_unified.py --scan BTCUSDT # مسح فوري
```

---

## 📊 الأنماط المدعومة

| الرمز | النمط | الوصف | R:R الأدنبي |
|-------|-------|-------|-------------|
| ⚡️ | Scalping (Futures) | تداول سريع (1m-5m) | 1.5:1 |
| 🏹 | Day Trading (Futures) | تداول يومي (15m/1h) | 2.5:1 |
| 🌊 | Swing Trading (Futures) | تداول تأرجحي (1D/4H) | 3.0:1 |
| 🏦 | Position Trading (Spot) | استثمار طويل المدى (DCA) | غير محدد |
| 🏦⚠️ | Position Trading (Futures) | محمي بـ 5 طبقات | 5.0:1 |
| 📰 | News Trading | نظام إنذار فقط (بدون تداول تلقائي) | — |

---

## 🛡️ منظومة الحماية المتكاملة

### 1. NO TRADE Engine (11 فلاتر)
- ❌ HTF bias غير واضح
- ❌ Structure متناقض
- ❌ لا توجد Liquidity واضحة
- ❌ لا توجد POI مناسبة
- ❌ Confirmation ضعيف
- ❌ R:R غير كافٍ
- ❌ Spread مرتفع
- ❌ Slippage مرتفع
- ❌ Volatility غير طبيعية
- ❌ News Risk مرتفع
- ❌ Funding Cost مرتفع

### 2. Score Engine
- **Score ≤ 7**: NO TRADE
- **Score 7-10**: Valid Setup
- **Score 11+**: A+ Candidate
- **Score 12+**: Premium Setup

### 3. Portfolio Protection
- الحد الأقصى للصفقات المتزامنة: 3
- الحد الأقصى للخسارة اليومية: 5%
- الحد الأقصى للخسائر المتتالية: 2
- الحد الأقصى للمخاطرة الإجمالية: 5%

### 4. إدارة مخاطر متقدمة
- Risk per Trade: 1%
- Leverage: 3x كحد أقصى
- Break Even عند 1:1
- Trailing Stop بعد 1:2
- Time Stop حسب النمط

---

## 🧠 التحليل SMC الموحد

### الخوارزمية الأساسية:
```
Market Context
    +
Market Structure (BOS/CHoCH)
    +
Liquidity (Sweep/Levels)
    +
POI (Order Block/FVG)
    +
Confirmation (CHoCH/Engulfing/Volume)
    +
Risk/Reward
    +
Execution Conditions
=
Valid Setup
```

### مؤشرات SMC المدعومة:
- **BOS** (Break of Structure)
- **CHoCH** (Change of Character)
- **FVG** (Fair Value Gap)
- **Order Block** (OB)
- **Liquidity Zones** (BSL/SSL/EQH/EQL)
- **Premium/Discount** (Fibonacci)

---

## 📁 هيكل المشروع

```
📦 All in One/
├── 🎮 نقاط الدخول الرئيسية
│   ├── main.py                    # القائمة الرئيسية (9 خيارات + تلغرام)
│   ├── telegram_control.py        # التحكم الكامل عبر تلغرام
│   ├── unified_trading_system.py  # النظام الموحد الرئيسي
│   ├── run_unified.py             # تشغيل مباشر
│   └── run_swing.py               # تشغيل الـ Swing Trader الأصلي
│
├── ⚙️ الإعدادات
│   ├── config.py                  # الإعدادات الأصلية (تستورد من config_unified)
│   └── config_unified.py          # الإعدادات المحسّنة (المصدر الواحد)
│
├── 🛠️ النواة (core/)
│   ├── exchange.py                # Binance API
│   ├── telegram_alerts.py         # إرسال إشعارات تلغرام
│   ├── unified_filters.py         # فلاتر NO TRADE + Score Engine + Time Filters
│   ├── unified_risk.py            # محرك المخاطر + DCA + Position Sizing
│   ├── unified_smc.py             # محرك تحليل SMC
│   ├── unified_backtester.py      # نظام باك تيست مدمج
│   └── unified_logging.py         # نظام سجلات ملون
│
├── 🤖 البوتات (modes/)
│   ├── base.py                    # الواجهة المشتركة
│   ├── scalper.py                 # ⚡️ Scalping Bot (Futures)
│   ├── day_trader.py              # 🏹 Day Trading Bot (Futures) [محسّن بـ SMC]
│   ├── swing_trader.py            # 🌊 Swing Trading Bot (Futures)
│   ├── position_trader.py         # 🏦 Position Trading (Spot - DCA)
│   ├── position_trader_futures.py # 🏦⚠️ Position Trading (Futures - 5 طبقات)
│   └── news_trader.py             # 📰 News Monitor (بدون تداول تلقائي)
│
├── 📰 أنظمة الأخبار
│   ├── news_alert_agent.py        # مراقب أخبار Tier 1
│   └── ai_news_agent.py           # تحليل أخبار بالذكاء الاصطناعي
│
├── 📊 مكتبة التحليل (analysis/)
│   ├── fvg_detector.py            # كشف FVG
│   ├── ob_detector.py             # كشف Order Block
│   └── market_structure.py        # هيكل السوق
│
├── 📅 الأدلة
│   ├── README.md                  # الدليل الأصلي
│   ├── README_KIMI.md             # خطة KIMI الكاملة
│   ├── README_GPT.md              # التوثيق الاحترافي (GPT)
│   ├── README_CLOUD.md            # مواصفات النظام المتقدم (Cloud)
│   └── README_QWEN.md             # الملخص العملي (Qwen)
│
└── 📂 الملفات الداعمة
    ├── .env.example               # نموذج ملف البيئة
    ├── tests/                     # اختبارات الوحدة
    └── logs/                      # ملفات السجلات
```

---

## 🌐 متطلبات التشغيل

```bash
pip install -r requirements.txt
```

ملف `.env` يحتاج إلى:
```
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token
```

---

## 📈 الأداء المتوقع (من Backtesting)

| النمط | Win Rate | Profit Factor | Max Drawdown |
|-------|----------|---------------|--------------|
| Scalping | > 55% | > 1.5 | < 10% |
| Day Trading | > 55% | > 1.5 | < 10% |
| Swing Trading | > 60% | > 2.0 | < 15% |
| Position (Spot) | > 70% | > 3.0 | < 20% |
| Position (Futures) | > 55% | > 2.0 | < 25% |

---

## 🚨 التحذيرات المهمة

1. **Scalping**: غير مربح مع رافعة 3x ورصيد صغير (الرسوم تأكل الربح)
2. **News Trading**: خطير جداً — استخدم كنظام إنذار فقط
3. **Position Futures**: محمي بـ 5 طبقات لكنه لا يزال خطيراً
4. **Demo First**: استخدم وضع التدريب قبل الرأس المال الحقيقي
5. **Backtest Required**: اختبر كل استراتيجية على بيانات تاريخية أولاً

---

## 📞 الدعم

للاستفسارات أو التحديثات:
- 📄 راجع ملفات README المرتبطة
- 🧪 استخدم `--help` للحصول على المساعدة
- 📱 تواصل عبر تلغرام باستخدام الأوامر المدمجة

---

**آخر تحديث**: 2026-09-10  
**الإصدار**: 2.0 (موحد ومحسّن)  
**المصدر**: دمج 4 ملفات README (KIMI, GPT, CLOUD, QWEN)