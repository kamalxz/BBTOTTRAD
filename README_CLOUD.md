# 🤖 Crypto Trading Bot System
## نظام تداول آلي متعدد الأنماط — Futures & Spot

> **الإصدار:** 2.0  
> **الحالة:** Specification / Backtesting Required  
> **الهدف:** بناء منظومة تداول آلية تعتمد على SMC + Price Action + Liquidity + Risk Management + Execution Control.

---

# ⚠️ 0. مبدأ النظام

هذا النظام **ليس آلة لتوقع السوق**.

الهدف هو العثور على حالات يكون فيها:

```text
Market Context
      +
Market Structure
      +
Liquidity
      +
POI
      +
Confirmation
      +
Risk/Reward
      +
Execution Conditions
      =
Valid Setup
```

إذا لم تتوفر الشروط المطلوبة:

```text
NO TRADE
```

**عدم الدخول صفقة صحيحة، وليس فشلًا للنظام.**

---

# 🧠 1. المبادئ الأساسية المشتركة

جميع أنماط التداول تستخدم نفس الطبقات الأساسية، لكن تختلف في الفريمات ومدة الصفقة وقواعد التنفيذ.

## 1.1 Market Structure

النظام يتعامل مع:

- Swing High
- Swing Low
- Higher High — HH
- Higher Low — HL
- Lower High — LH
- Lower Low — LL
- BOS
- CHoCH
- MSS
- Internal Structure
- External Structure

### قاعدة مهمة

لا يعتبر البوت أي كسر صغير BOS تلقائيًا.

يجب تحديد:

```text
Swing Definition
+
Close/Wick Rule
+
Displacement
+
Minimum Structural Distance
```

---

# 💧 2. Liquidity Model

يبحث النظام عن:

- Buy-Side Liquidity — BSL
- Sell-Side Liquidity — SSL
- Equal Highs — EQH
- Equal Lows — EQL
- Previous Day High — PDH
- Previous Day Low — PDL
- Previous Week High — PWH
- Previous Week Low — PWL
- Session High/Low
- Major Swing High/Low

## Liquidity Sweep

الـSweep لا يعني الدخول مباشرة.

النموذج الأساسي:

```text
Liquidity
    ↓
Sweep
    ↓
Displacement
    ↓
MSS / CHoCH
    ↓
POI
    ↓
Retest
    ↓
Entry
```

---

# 📦 3. POI — Point of Interest

المناطق الرئيسية:

- Order Block — OB
- Fair Value Gap — FVG
- Breaker
- Mitigation Block
- Previous Structure
- Liquidity Level
- Premium / Discount

لا يتم الدخول لمجرد لمس POI.

يفضل:

```text
HTF POI
+
Liquidity Event
+
LTF Confirmation
```

---

# ⚖️ 4. Premium / Discount

يجب أولًا تحديد:

```text
Dealing Range
    High
      │
      │ Premium
      │
  50% Equilibrium
      │
      │ Discount
      │
    Low
```

### للـLong

يفضل البحث عن فرص في Discount.

### للShort

يفضل البحث عن فرص في Premium.

> Premium/Discount عامل سياقي وليس إشارة دخول مستقلة.

---

# 📐 5. FVG

## Bullish FVG

يتم تعريفه وفق قاعدة قابلة للبرمجة بين ثلاث شموع، مع تحديد:

- Minimum gap size
- Fresh / Mitigated
- Partial fill
- Full fill
- Invalidation
- HTF/LTF

## Bearish FVG

نفس المبدأ في الاتجاه المعاكس.

لا يعتبر وجود FVG وحده سببًا للدخول.

---

# 🧱 6. Order Block

الـOB يجب أن يكون مرتبطًا بحركة واضحة أدت إلى:

```text
Displacement
+
Structural Break
```

ويجب على البوت تخزين:

```text
OB High
OB Low
Direction
Timeframe
Creation Time
Mitigation Status
Invalidation
Freshness
```

---

# 🎯 7. Risk Engine

هذه الطبقة مستقلة عن استراتيجية الدخول.

## Risk Per Trade

القيمة الافتراضية المقترحة:

```text
Normal Trade:
0.5% – 1.0%

High Volatility:
0.25% – 0.5%

News:
0.25% – 0.5%
```

القيم النهائية يجب اختبارها Backtest.

---

## Position Size

لا يتم تحديد حجم الصفقة من الرافعة.

أولًا:

```text
Risk Amount
=
Account Equity × Risk %
```

ثم:

```text
Position Notional
=
Risk Amount / Stop Distance %
```

مثال:

```text
Account = $100

Risk = 1%

Risk Amount = $1

SL = 2%

Position Notional
= $1 / 0.02
= $50
```

الرافعة تحدد **الهامش المطلوب**، وليس مقدار المخاطرة.

---

# 🛑 8. Stop Loss

لا تستخدم قاعدة ثابتة مثل:

```text
SL = 3–5 points
```

بدلًا من ذلك:

```text
SL
=
Structural Invalidation
+
Volatility Buffer
```

حسب نوع Setup يمكن أن يكون خلف:

- OB
- Swing Low/High
- Liquidity
- FVG invalidation
- Structural level

---

# 💰 9. Take Profit

الأولوية:

```text
Liquidity Target
```

ثم يتم فحص:

```text
Expected RR
```

لا يتم إجبار كل صفقة على TP ثابت.

---

# 🚫 10. NO TRADE Engine

لا تدخل الصفقة إذا:

- HTF bias غير واضح
- Structure متناقض
- لا توجد Liquidity واضحة
- لا توجد POI مناسبة
- Confirmation ضعيف
- RR غير كافٍ
- Spread مرتفع
- Slippage مرتفع
- Volatility غير طبيعية
- News Risk مرتفع
- Daily Loss Limit reached
- Max Trades reached
- Duplicate Setup
- Funding Cost مرتفع
- Execution conditions سيئة

---

# 📊 11. Setup Scoring

يمكن للنظام استخدام Score بدل Binary Rules.

مثال أولي:

| العامل | Score |
|---|---:|
| HTF Bias | +2 |
| Liquidity Sweep | +2 |
| MSS/CHoCH | +2 |
| Displacement | +1 |
| FVG | +1 |
| OB | +1 |
| Premium/Discount | +1 |
| Session | +1 |
| Volume/Activity | +1 |
| News Clear | +1 |

مثال:

```text
Score < 7
→ NO TRADE

7–8
→ Valid

9–10
→ High Quality

11+
→ A+ Candidate
```

> الأوزان ليست حقيقة سوقية ثابتة؛ يجب تحسينها بالـBacktesting.

---

# 🛡️ 12. Global Risk Protection

```text
Max Risk / Trade
Max Daily Loss
Max Weekly Loss
Max Concurrent Positions
Max Trades / Day
Max Consecutive Losses
Max Exposure
Max Leverage
Emergency Stop
```

مثال مبدئي:

```text
Risk / Trade = 1%
Daily Loss Limit = 3%
Max Consecutive Losses = 3
Max Trades = Strategy Dependent
```

---

# ⚡ 13. PLAN A — SCALPING FUTURES

## الهدف

التقاط حركات قصيرة جدًا من Liquidity + MSS + FVG/OB.

### مدة الصفقة

```text
Seconds → Minutes
```

### الأسواق

يفضل:

```text
BTC
ETH
```

ويتم السماح بعملات أخرى فقط بعد إثبات السيولة والتنفيذ في Backtest.

---

# ⏱️ Timeframes

```text
15m → Context
5m  → Liquidity / Structure
1m  → Entry
```

---

# 🧭 Scalping Workflow

```text
15m Bias
    ↓
Session Liquidity
    ↓
5m Sweep
    ↓
5m/1m Displacement
    ↓
1m MSS
    ↓
FVG / OB
    ↓
Retest
    ↓
Entry
```

---

# ✅ Long Setup

1. HTF bullish context
2. Price approaches relevant liquidity
3. SSL sweep
4. Bullish displacement
5. Bullish MSS/CHoCH
6. Bullish FVG/OB
7. Retest
8. RR acceptable
9. Execution conditions acceptable

ثم:

```text
BUY
```

---

# 🔻 Short Setup

العكس:

```text
Bearish Context
→ BSL Sweep
→ Bearish Displacement
→ Bearish MSS
→ Bearish FVG/OB
→ Retest
→ SHORT
```

---

# 🛑 Scalping Exit

SL:

```text
Structural Invalidation + Buffer
```

TP:

```text
Nearest Valid Liquidity
```

ويجب احتساب:

```text
Fees
+
Slippage
```

قبل قبول الصفقة.

---

# ⚠️ Scalping Rules

- لا تدخل بسبب Candle واحدة فقط.
- لا تستخدم CHoCH وحده.
- لا تطارد السعر.
- لا تستخدم Market Order بشكل افتراضي.
- لا تفتح عددًا كبيرًا من الصفقات لمجرد الوصول إلى Target.
- إذا لم توجد فرصة، `NO TRADE`.

---

# 🏹 14. PLAN B — DAY TRADING FUTURES

## الهدف

التقاط الحركة الرئيسية داخل اليوم.

### Timeframes

```text
4H → Bias
15m → POI / Liquidity
5m → Confirmation
```

---

# 🧭 Day Trading Workflow

```text
4H Bias
   ↓
External Liquidity
   ↓
15m POI
   ↓
Liquidity Sweep
   ↓
5m MSS
   ↓
FVG / OB
   ↓
Retest
   ↓
Entry
```

---

# 📈 Long

```text
4H Bullish
+
Discount / valid HTF area
+
SSL Sweep
+
Bullish MSS
+
Displacement
+
FVG/OB
+
RR acceptable
```

---

# 📉 Short

```text
4H Bearish
+
Premium / valid HTF area
+
BSL Sweep
+
Bearish MSS
+
Displacement
+
FVG/OB
+
RR acceptable
```

---

# 🎯 TP

الأولوية:

```text
PDH
PDL
Session Liquidity
Major Swing
External Liquidity
```

وليس TP ثابتًا لجميع الصفقات.

---

# 🕐 Time Stop

Time Stop يستخدم كـparameter قابل للاختبار.

مثلاً:

```text
Maximum Holding Time
=
Configurable
```

ولا يتم افتراض أن 8 ساعات هي القيمة المثالية دائمًا.

---

# 🌊 15. PLAN C — SWING TRADING FUTURES

## الهدف

التقاط حركة متعددة الأيام أو الأسابيع.

### Timeframes

```text
1D → Macro Bias
4H → POI
1H → Confirmation
```

---

# 🧭 Swing Workflow

```text
1D Structure
     ↓
Major Liquidity
     ↓
4H POI
     ↓
Liquidity Sweep
     ↓
1H MSS
     ↓
Displacement
     ↓
FVG / OB
     ↓
Entry
```

---

# 📌 Swing Filters

يتم فحص:

- HTF trend
- Major liquidity
- Funding
- Volatility
- Macro events
- BTC correlation
- Market regime

---

# 💸 Funding

لا تستخدم:

```text
Funding > X
→ Always Reject
```

بدلًا من ذلك:

```text
Expected Funding Cost
+
Holding Duration
+
Position Notional
+
Expected Trade Edge
```

ثم:

```text
Cost / Expected Profit
```

إذا أصبحت التكلفة غير منطقية:

```text
NO TRADE
```

---

# 🏦 16. PLAN D — POSITION TRADING FUTURES

## ⚠️ أعلى خطورة

Futures لفترات طويلة تعرض النظام إلى:

- Funding
- Liquidation Risk
- Gap/Volatility
- Leverage Risk
- Long Holding Exposure

لذلك يجب أن يكون هذا النظام أكثر تحفظًا.

---

# Timeframes

```text
1D → Macro Structure
4H → POI
1H → Entry Confirmation
```

---

# Entry Model

```text
1D Bias
   ↓
Major Liquidity
   ↓
4H OB/FVG
   ↓
Liquidity Interaction
   ↓
1H MSS
   ↓
Retest
   ↓
Entry
```

---

# Funding Model

Funding Cost:

```text
Funding Cost
≈
Position Notional
×
Funding Rate
×
Number of Funding Intervals
```

ثم:

```text
Funding Cost / Account Equity
```

يجب حساب التكلفة المتوقعة بناءً على **Notional الحقيقي**.

الرافعة لا تضاعف Funding تلقائيًا إذا بقي الـNotional نفسه.

---

# Duration Guard

الـmaximum holding period يجب أن يكون configurable:

```text
MAX_POSITION_DURATION
```

وليس رقمًا مقدسًا.

إذا تغيرت بنية السوق:

```text
Exit
```

حتى لو لم يصل الحد الزمني.

---

# 🟢 17. PLAN E — POSITION TRADING SPOT

## الهدف

الاستفادة من الاتجاهات طويلة الأجل بدون Liquidation.

### Timeframes

```text
1W → Macro
1D → Structure / Entry
```

---

# Spot Philosophy

Spot مختلف عن Futures.

لا يوجد:

```text
Liquidation
Leverage
Funding
```

لكن لا يعني ذلك أن الشراء آمن أو أن السعر لا يمكن أن ينخفض بشدة.

---

# Macro Model

يتم تحليل:

```text
Weekly Structure
+
Market Regime
+
Liquidity
+
Macro Context
+
Long-Term POI
```

---

# DCA

DCA يستخدم كـRisk Distribution وليس كضمان للربح.

مثال:

```text
Capital = $100

L1 = 20%
L2 = 20%
L3 = 25%
L4 = 35%
```

لكن مستويات الأسعار يجب أن تكون مرتبطة بالسوق، وليس بالضرورة:

```text
-5%
-10%
-15%
```

يمكن استخدام:

```text
HTF Support
OB
FVG
Liquidity
ATR
Structure
```

لتحديد مستويات الشراء.

---

# Average Entry

يجب حساب المتوسط الحقيقي:

```text
Total BTC Bought
=
Σ Allocation / Entry Price

Average Entry
=
Total Capital / Total BTC
```

وليس متوسط الأسعار الحسابي.

---

# Macro Indicators

يمكن استخدام:

- 200W MA
- Fear & Greed
- Halving Cycle
- Macro Liquidity
- BTC Dominance

لكنها:

```text
Context
```

وليست:

```text
Automatic BUY Signal
```

---

# 📰 18. PLAN F — NEWS TRADING

## Smart Alert System

هذا النظام مختلف عن بقية الأنظمة.

الهدف الأساسي:

```text
Detect
→ Analyze
→ Alert
```

وليس تنفيذ صفقة تلقائية أثناء الخبر.

---

# Tier 1 Events

مثل:

- CPI
- FOMC
- NFP

ويتم توسيع قائمة الأخبار فقط بعد اختبارها.

---

# Pre-News

قبل الخبر:

```text
Detect Event
↓
Lock New Entries
↓
Check Open Positions
↓
Check Exposure
↓
Alert User
```

لا يتم افتراض اتجاه الخبر.

---

# News Release

عند صدور الخبر:

```text
DO NOTHING
```

خلال مرحلة volatility الأولية.

---

# Post-News Analysis

يتم تحليل:

```text
Price Reaction
+
Volume
+
Spread
+
Volatility
+
Liquidity
+
Displacement
+
Market Structure
```

---

# Long Scenario

```text
News
 ↓
Initial Volatility
 ↓
SSL Sweep
 ↓
Bullish Displacement
 ↓
MSS
 ↓
Retest
 ↓
Alert
```

---

# Short Scenario

```text
News
 ↓
Initial Volatility
 ↓
BSL Sweep
 ↓
Bearish Displacement
 ↓
MSS
 ↓
Retest
 ↓
Alert
```

---

# 🚨 News Risk

يجب رفض الإشارة إذا:

```text
Spread too high
Slippage too high
Liquidity insufficient
Volatility abnormal
RR insufficient
Structure unclear
```

---

# 🔔 Smart Alert Output

مثال:

```text
NEWS ALERT

Event:
CPI

Symbol:
BTCUSDT

Bias:
Bullish

Liquidity:
SSL Swept

Confirmation:
Bullish MSS

POI:
1m FVG

Risk:
HIGH

Execution:
WAIT FOR RETEST

Status:
ALERT — NOT AUTO ENTRY
```

---

# 🧮 19. Position Sizing Engine

جميع الاستراتيجيات تستخدم:

```text
Account Equity
       ↓
Risk %
       ↓
Risk Amount
       ↓
Stop Distance
       ↓
Position Notional
       ↓
Leverage
       ↓
Required Margin
```

---

# 💵 مثال

```text
Equity = $100
Risk = 1%

Risk Amount = $1

SL Distance = 2%

Position Notional
= $1 / 0.02
= $50
```

إذا:

```text
Leverage = 3x
```

فالهامش التقريبي:

```text
$50 / 3
≈ $16.67
```

لكن الرسوم والـslippage والـfunding يجب إضافتها بشكل مستقل.

---

# 💰 20. PnL Engine

لا يعتمد النظام على Gross PnL فقط.

يحسب:

```text
Gross PnL
-
Entry Fees
-
Exit Fees
-
Funding
-
Slippage
-
Other Costs
=
Net PnL
```

---

# 📊 21. Performance Metrics

بعد Backtesting يتم تسجيل:

```text
Total Trades
Win Rate
Loss Rate
Average R
Expectancy
Profit Factor
Max Drawdown
Average Drawdown
Sharpe Ratio
Sortino Ratio
Largest Win
Largest Loss
Consecutive Wins
Consecutive Losses
Average Holding Time
Fees
Funding
Slippage
```

---

# 🧪 22. Backtesting Protocol

لا يتم تشغيل النظام Live مباشرة.

المراحل:

```text
1. Historical Backtest
        ↓
2. Out-of-Sample Test
        ↓
3. Walk-Forward Test
        ↓
4. Monte Carlo / Robustness
        ↓
5. Paper Trading
        ↓
6. Small Capital
        ↓
7. Controlled Scaling
```

---

# 🚫 23. منع Overfitting

لا تقم بتعديل القواعد حتى يصبح الـBacktest مثاليًا.

يجب الفصل بين:

```text
Training Period
```

و:

```text
Validation Period
```

و:

```text
Out-of-Sample Period
```

---

# 🔄 24. Market Regime Detection

النظام يجب أن يعرف:

```text
Trending
Ranging
High Volatility
Low Volatility
Risk-On
Risk-Off
```

لأن نفس Setup قد يعمل جيدًا في Trend ويفشل في Range.

---

# 🧠 25. Decision Engine

كل Strategy يجب أن تنتهي بواحد من:

```text
LONG
SHORT
NO TRADE
```

ثم:

```text
Risk Engine
```

يتحقق من صلاحية الصفقة.

ثم:

```text
Execution Engine
```

يتولى التنفيذ.

---

# 🏗️ 26. Architecture

```text
                    MARKET DATA
                         │
                         ▼
                ┌─────────────────┐
                │ Market Structure│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Liquidity Engine│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │    SMC Engine   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Strategy Engine │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Score Engine   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │   Risk Engine   │
                └────────┬────────┘
                         │
                    ┌────┴────┐
                    │         │
                   PASS     REJECT
                    │         │
                    ▼         ▼
              Execution    NO TRADE
                 Engine
                    │
                    ▼
             Position Manager
                    │
                    ▼
              Monitoring
                    │
                    ▼
                 Logs
```

---

# 🔐 27. Emergency Protection

يجب أن يستطيع النظام تنفيذ:

```text
GLOBAL STOP
```

عند:

- API Failure
- Exchange Error
- Unexpected Position
- Abnormal Slippage
- Data Feed Failure
- Price Feed Desync
- Excessive Drawdown
- Duplicate Order
- Order Rejection Loop
- Risk Engine Failure

---

# 📋 28. Strategy Comparison

| Strategy | Main TF | Holding | Leverage | Risk |
|---|---|---|---:|---|
| Scalping Futures | 15m/5m/1m | دقائق | Configurable | Very High |
| Day Futures | 4H/15m/5m | ساعات | Configurable | High |
| Swing Futures | 1D/4H/1H | أيام/أسابيع | Configurable | High |
| Position Futures | 1D/4H/1H | أسابيع/أشهر | Low | Very High |
| Position Spot | 1W/1D | أشهر/سنوات | 1x | Medium |
| News Alerts | 5m/1m | دقائق | Prefer Alert | Very High |

---

# 🧩 29. Configuration Philosophy

لا تضع الأرقام داخل Logic بشكل Hardcoded.

استخدم:

```text
config/
    risk.yaml
    scalping.yaml
    day_trading.yaml
    swing.yaml
    position_futures.yaml
    position_spot.yaml
    news.yaml
```

مثال:

```yaml
risk_per_trade: 0.01
max_daily_loss: 0.03
max_consecutive_losses: 3
```

---

# 📝 30. Trade Journal

كل صفقة يجب أن تسجل:

```text
Timestamp
Symbol
Strategy
Direction
HTF Bias
Liquidity
POI
MSS/BOS
FVG
OB
Entry
Stop
Target
Risk
Position Size
Leverage
Fees
Funding
Slippage
Gross PnL
Net PnL
Exit Reason
Screenshot/Reference
```

---

# 🧠 31. Exit Reason Codes

استخدم Codes بدل النصوص العشوائية:

```text
TP
SL
BE
TRAILING_STOP
STRUCTURE_INVALIDATION
TIME_STOP
RISK_STOP
NEWS_STOP
MANUAL_STOP
SYSTEM_ERROR
```

---

# 🚦 32. Final Decision Logic

```text
IF
    Market Data Valid
AND HTF Context Valid
AND Structure Valid
AND Liquidity Valid
AND POI Valid
AND Confirmation Valid
AND RR Valid
AND Risk Valid
AND Execution Valid
AND News Filter Valid
AND Exposure Valid

THEN

    LONG / SHORT

ELSE

    NO TRADE
```

---

# ⚠️ 33. قواعد لا يجب كسرها

```text
Never chase price.

Never increase risk after a loss.

Never use leverage to define risk.

Never assume CHoCH guarantees reversal.

Never assume FVG guarantees reaction.

Never assume OB guarantees reaction.

Never treat Fear & Greed as an entry signal.

Never treat Halving as an automatic BUY signal.

Never treat Funding as a simple fixed threshold.

Never assume historical performance guarantees future performance.

Never allow the bot to trade when the Risk Engine is unavailable.
```

---

# 🎯 34. الأولوية عند تعارض الإشارات

إذا تعارضت الإشارات:

```text
Risk
  >
Market Structure
  >
HTF Context
  >
Liquidity
  >
POI
  >
LTF Confirmation
  >
Entry
```

مثال:

```text
Excellent FVG
+
Bad HTF Structure
=
NO TRADE
```

---

# 🏁 35. Final System Philosophy

الهدف ليس:

```text
Maximum Number of Trades
```

ولا:

```text
Maximum Leverage
```

ولا:

```text
Maximum Daily Profit
```

الهدف:

```text
High Quality Setups
+
Controlled Risk
+
Low Execution Error
+
Positive Expectancy
+
Long-Term Survival
```

النظام الناجح ليس النظام الذي يتداول أكثر.

**النظام الناجح هو النظام الذي يعرف متى يتداول ومتى لا يتداول.**

---

# 🔬 36. Required Before Live Trading

لا يتم الانتقال إلى Live Trading قبل إثبات:

```text
✓ Strategy Backtest
✓ Out-of-Sample Validation
✓ Fees Included
✓ Funding Included
✓ Slippage Included
✓ Execution Simulation
✓ Drawdown Analysis
✓ Consecutive Loss Analysis
✓ Paper Trading
✓ Emergency Stop Tested
✓ Risk Engine Tested
✓ Order Management Tested
✓ API Failure Tested
```

---

# 🔒 37. Final Status

```text
Strategy:
DEFINED

Risk:
DEFINED

Execution:
DEFINED

Backtesting:
REQUIRED

Optimization:
REQUIRED

Paper Trading:
REQUIRED

Live Trading:
NOT READY UNTIL VALIDATED
```

**End of Trading System Specification v2.0**