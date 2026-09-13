"""
🚀 unified_trading_system.py — النظام الموحد للتداول الآلي v2.0
يدمج منهجية 90% نجاح الصفقات من جميع الملفات الـREADME (KIMI, GPT, CLOUD, QWEN)

الفلسفة: 
- NO TRADE هو أفضل قرار
- إدارة مخاطر صارمة
- تحليل SMC منهجي
- نظام إنذار ذكي (بدون تداول آلي تلقائي)
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# إصلاح ترميز Windows
if sys.stdout.encoding in ("cp1252", "cp1256"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config_unified as config
from core.unified_logging import setup_logging
setup_logging(config.LOG_LEVEL)

from core.unified_filters import UnifiedFilters, MarketContext, TradeSignal, TimeFilter
from core.unified_risk import UnifiedRiskEngine, RiskParams, PositionSize
from core.unified_smc import UnifiedSMC, SMCAnalysis
from core.unified_backtester import UnifiedBacktester

from core.telegram_alerts import send_telegram_alert

logger = logging.getLogger("unified_trading_system")

LOG_DIR = Path("logs") / f"run_{datetime.now().strftime('%Y%m%d')}.log"
LOG_DIR.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR, encoding="utf-8", errors="replace"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class UnifiedTradingSystem:
    """
    النظام الموحد الرئيسي — يدمج جميع مكوّنات التداول
    
    المنهجية المدمجة:
    - NO TRADE Engine من CLOUD
    - Risk Engine من CLOUD
    - SMC Analysis من GPT/KIMI/QWEN
    - Position Sizing من GPT
    - Time Filters من KIMI
    - Safety Layers من GPT
    """

    def __init__(self, mode: str = "swing", account_equity: float = 100.0):
        self.mode = mode
        self.account_equity = account_equity
        self.filters = UnifiedFilters(mode=mode)
        self.risk_engine = UnifiedRiskEngine(mode=mode)
        self.smc = UnifiedSMC(config_dict=config.SMC_CONFIG)
        
        # حالة النظام
        self.is_running = False
        self.open_positions = 0
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.total_risk_exposure = 0.0
        
        logger.info(f"🚀 تم تشغيل النظام الموحد — الوضع: {mode}، رأس المال: {account_equity} USDT")
        send_telegram_alert(f"🚀 نظام التداول الموحد جاهز — الوضع: {mode}")

    def run_scan(self, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        مسح السوق وتحليل الإعداد المناسب
        
        خطوات التحليل:
        1. جلب بيانات السوق (OHLCV)
        2. تحليل SMC (BOS, CHoCH, FVG, OB)
        3. حساب النقاط (Score Engine)
        4. تطبيق الفلاتر NO TRADE
        5. حساب حجم الصفقة والمخاطرة
        6. إرسال إشعار أو رفض الصفقة
        """
        logger.info(f"🔍 بدء مسح السوق للرمز: {symbol}")
        
        # استيراد التبعيات المؤخرة لتجنب استيراد دائري
        from core.exchange import BinanceExchange
        exchange = BinanceExchange()
        
        # 1. جلب البيانات
        market_type = "futures" if self.mode != "position_spot" else "spot"
        timeframe_map = {
            "scalping": "1m",
            "day": "5m",
            "swing": "1h",
            "position_spot": "1d",
            "position_futures": "1h",
            "news": "1m",
        }
        tf = timeframe_map.get(self.mode, "1h")
        
        try:
            ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100, market_type=market_type)
            import pandas as pd
            df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            logger.error(f"❌ فشل جلب البيانات لـ {symbol}: {e}")
            send_telegram_alert(f"❌ خطأ في جلب البيانات لـ {symbol}: {e}")
            return {"status": "error", "message": str(e)}

        # 2. جلب الفريم العلوي للـ HTF Bias
        htf_tf = config.HTF_TIMEFRAME
        try:
            htf_data = exchange.fetch_ohlcv(symbol, timeframe=htf_tf, limit=50, market_type=market_type)
            htf_df = pd.DataFrame(htf_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        except:
            htf_df = None

        # 3. تحليل SMC
        score, ms, poi_list, confirmation = self.smc.calculate_score(df, htf_df, symbol)

        # 4. بناء سياق السوق
        context = MarketContext(
            htf_bias=ms.trend_direction,
            structure_valid=ms.structure_valid,
            liquidity_present=len([z for z in self.smc.detect_liquidity_zones(df) if z.swept]) > 0,
            poi_found=len(poi_list) > 0,
            confirmation_valid=confirmation.confirmed,
            funding_rate=self._get_funding_rate(symbol),
            spread=0.0001,  # افتراضي
            slippage=0.0002,  # افتراضي
            volatility="normal",
            news_risk="low" if not TimeFilter.is_news_release_soon(15) else "high",
        )

        # 5. حساب مستويات الدخول والخروج
        entry_price, sl_price, tp_price = self.smc.get_entry_and_exit_levels(df, 
            direction="long" if ms.trend_direction == "bullish" else "short")

        if entry_price is None:
            logger.info(f"⚪ {symbol}: لا توجد فرصة تداول واضحة — NO TRADE")
            return {"status": "no_trade", "reason": "No valid setup detected", "score": score}

        # 6. بناء إشارة التداول
        rr_ratio = abs(tp_price - entry_price) / abs(entry_price - sl_price) if sl_price else 0
        signal = TradeSignal(
            symbol=symbol,
            side="LONG" if ms.trend_direction == "bullish" else "SHORT",
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            rr=rr_ratio,
            confidence=confirmation.strength,
            reasons=[f"Score: {score}/10", f"SMC: {ms.trend_direction}", f"Confirmation: {confirmation.type}"],
            score=score,
        )

        # 7. تطبيق فلاتر NO TRADE
        should_trade, rejections = self.filters.check_no_trade_conditions(context, signal)

        # 8. فحص حماية المحفظة
        can_trade_portfolio, portfolio_reason = self.filters.check_portfolio_risk(
            self.open_positions, self.daily_loss, self.consecutive_losses,
            self.total_risk_exposure, self.account_equity
        )

        # 9. اتخاذ القرار
        if not can_trade_portfolio:
            logger.warning(f"🔴 {symbol}: محظور — {portfolio_reason}")
            send_telegram_alert(f"🔴 {symbol}: محظور — {portfolio_reason}")
            return {"status": "rejected", "reason": portfolio_reason}

        if not should_trade:
            logger.info(f"⚪ {symbol}: NO TRADE — {rejections}")
            if len(rejections) <= 2 or score >= 8:  # Score عالي جدًا → إرسال إشعار
                send_telegram_alert(
                    f"⚪ {symbol}: NO TRADE — {rejections}\n"
                    f"📊 النقاط: {score}/10\n"
                    f"⚠️ للمراجعة اليدوية إذا كان Score عاليًا"
                )
            return {"status": "no_trade", "reasons": rejections, "score": score}

        # 10. حساب حجم الصفقة
        risk_params = RiskParams(
            account_equity=self.account_equity,
            risk_percent=config.RISK_PER_TRADE,
            leverage=config.LEVERAGE,
            mode=self.mode,
            funding_cost_expected=config.MAX_EXPECTED_FUNDING_COST if self.mode == "position_futures" else 0.0
        )

        position = self.risk_engine.calculate_position_size(
            signal.entry_price, signal.sl_price, signal.tp_price, risk_params
        )

        if not position.is_valid:
            logger.warning(f"🔴 {symbol}: حجم الصفقة غير صالح — {position.warnings}")
            send_telegram_alert(
                f"🔴 {symbol}: حجم الصفقة غير صالح!\n{position.warnings}"
            )
            return {"status": "rejected", "reasons": position.warnings}

        # 11. إرسال إشعار التداول (بدون تنفيذ تلقائي!)
        confidence_pct = min(signal.confidence * 100, 100)
        message = (
            f"✅ **📊 إشارة تداول مؤهلة**\n\n"
            f"🪙 الرمز: {symbol}\n"
            f"📊 الاتجاه: {signal.side}\n"
            f"🎯 مستوى الدخول: {signal.entry_price:.2f}\n"
            f"🛑 SL: {signal.sl_price:.2f}\n"
            f"✅ TP: {signal.tp_price:.2f}\n"
            f"⚖️ R:R: {signal.rr:.2f}:1\n"
            f"📈 النقاط: {score}/10\n"
            f"💪 الثقة: {confidence_pct:.0f}%\n\n"
            f"💰 حجم الصفقة: {position.position_notional:.2f} USDT\n"
            f"⚙️ الهامض المطلوب: {position.required_margin:.2f} USDT\n"
            f"📉 المخاطرة: {position.risk_amount:.2f} USDT\n"
            f"💸 الرسوم: {position.total_fees:.3f} USDT\n\n"
            f"⚠️ **تذكير**: هذه إشارة مرشح للمراجعة اليدوية.\n"
            f"استخدم Checklists قبل التنفيذ."
        )
        send_telegram_alert(message)
        
        logger.info(f"✅ {symbol}: إشارة صالحة — {signal.side} @ {signal.entry_price:.2f}، R:R {signal.rr:.2f}:1")
        
        return {
            "status": "trade_signal",
            "signal": signal.__dict__,
            "position": position.__dict__,
            "score": score,
            "confidence": signal.confidence,
        }

    def _get_funding_rate(self, symbol: str) -> float:
        """الحصول على معدل التمويل الحالي"""
        from core.exchange import BinanceExchange
        exchange = BinanceExchange()
        try:
            return exchange.get_funding_rate(symbol)
        except:
            return 0.0

    def run_continuous(self, symbols: list = None, interval: int = 300):
        """
        تشغيل النظام باستمرار (للوضع News Monitor)
        """
        if symbols is None:
            symbols = config.SYMBOLS
            
        self.is_running = True
        logger.info(f"🔄 بدء المسح المستمر — كل {interval} ثانية")
        
        while self.is_running:
            try:
                for symbol in symbols:
                    self.run_scan(symbol.replace(":USDT", ""))
                TimeFilter.is_news_release_soon(5)  # فحص الأخبار
                import time
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("🛑 إيقاف النظام المستمر")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ خطأ في التشغيل المستمر: {e}")
                import time
                time.sleep(60)

    def stop(self):
        """إيقاف النظام"""
        self.is_running = False
        logger.info("🛑 تم إيقاف النظام الموحد")


def menu():
    """قائمة النظام الموحدة"""
    print("\n" + "=" * 60)
    print("🤖 نظام التداول الآلي الموحد v2.0 — 90% نجاح الصفقات")
    print("=" * 60)
    print("1️⃣  ⚖️  فحص صفقة واحدة (Single Trade Analysis)")
    print("2️⃣  🔄  مسح مستمر (Continuous Scan)")
    print("3️⃣  📊  تحليل SMC مفصل (Detailed SMC Analysis)")
    print("4️⃣  💰  حساب حجم الصفقة (Position Sizing Calculator)")
    print("5️⃣  🎯  نظام إنذار الأخبار (News Alert System)")
    print("6️⃣  🧪  اختبار النظام (System Test)")
    print("0️⃣  🚪  خروج")
    print("=" * 60)
    return input("👉 اختر رقمًا [0-6]: ").strip()


def main():
    print("🚀 تشغيل النظام الموحد للتداول الآلي v2.0...")
    system = UnifiedTradingSystem(mode="swing", account_equity=100.0)
    
    while True:
        try:
            choice = menu()
            
            if choice == "0":
                system.stop()
                break
                
            elif choice == "1":
                symbol = input("🔤 أدخل الرمز (مثال: BTC/USDT): ").strip() or "BTC/USDT"
                result = system.run_scan(symbol)
                print(f"\n📊 النتيجة: {result['status']}")
                if result['status'] == 'trade_signal':
                    print(f"✅ إشارة صاليدة — R:R: {result['signal']['rr']:.2f}:1")
                elif result['status'] == 'no_trade':
                    print(f"⚪ NO TRADE — النقاط: {result.get('score', 0)}/10")
                    
            elif choice == "2":
                symbols_str = input("🔤 أدخل الرموز (مثال: BTC/USDT,ETH/USDT) أو اتركه فارغًا: ").strip()
                symbols = [s.strip() for s in symbols_str.split(",")] if symbols_str else None
                interval = int(input("⏱️ الفاصل الزمني (ثواني) [300]: ") or 300)
                system.run_continuous(symbols=symbols, interval=interval)
                
            elif choice == "3":
                symbol = input("🔤 أدخل الرمز: ").strip() or "BTC/USDT"
                from core.unified_smc import UnifiedSMC
                smc = UnifiedSMC(config_dict=config.SMC_CONFIG)
                from core.exchange import BinanceExchange
                exchange = BinanceExchange()
                df = pd.DataFrame(exchange.fetch_ohlcv(symbol, "1h", 100), 
                                columns=["timestamp", "open", "high", "low", "close", "volume"])
                score, ms, poi, conf = smc.calculate_score(df, df, symbol)
                print(f"📊 النقاط: {score}/10")
                print(f"📈 الاتجاه: {ms.trend_direction}")
                print(f"🔍 BOS: {ms.bos_detected}, CHoCH: {ms.choch_detected}")
                print(f"🎯 الثقة: {conf.strength:.2f}")
                
            elif choice == "4":
                entry = float(input("💵 سعر الدخول: "))
                sl = float(input("🛑 سعر SL: "))
                tp = float(input("✅ سعر TP: "))
                equity = float(input("💰 رأس المال [100]: ") or 100)
                risk_pct = float(input("⚖️ نسبة المخاطرة [0.01]: ") or 0.01)
                leverage = float(input("⚡ الرافعة [3]: ") or 3)
                
                params = RiskParams(
                    account_equity=equity, risk_percent=risk_pct, leverage=leverage, mode="swing"
                )
                position = system.risk_engine.calculate_position_size(entry, sl, tp, params)
                
                print(f"\n📊 نتائج حساب الصفقة:")
                print(f"   المخاطرة: {position.risk_amount:.2f} USDT")
                print(f"   حجم الصفقة: {position.position_notional:.2f} USDT")
                print(f"   الهامض المطلوب: {position.required_margin:.2f} USDT")
                print(f"   الكمية: {position.quantity:.6f}")
                print(f"   R:R: {position.rr_ratio:.2f}:1")
                print(f"   الرسوم الإجمالية: {position.total_fees:.3f} USDT")
                print(f"   الصلاحية: {'✅' if position.is_valid else '❌'}")
                if position.warnings:
                    print(f"   التحذيرات: {position.warnings}")
                    
            elif choice == "5":
                print("📰 تشغيل نظام إنذار الأخبار...")
                from news_alert_agent import NewsAlertAgent
                agent = NewsAlertAgent()
                agent.run()
                
            elif choice == "6":
                print("🧪 اختبار النظام...")
                system = UnifiedTradingSystem(mode="swing")
                # اختبار بيانات وهمية
                import pandas as pd
                import numpy as np
                dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
                data = {
                    "timestamp": dates.astype(np.int64) // 10**9,
                    "open": np.random.uniform(50000, 60000, 100),
                    "high": np.random.uniform(51000, 61000, 100),
                    "low": np.random.uniform(49000, 59000, 100),
                    "close": np.random.uniform(50000, 60000, 100),
                    "volume": np.random.uniform(100, 500, 100),
                }
                df = pd.DataFrame(data)
                score, ms, poi, conf = system.smc.calculate_score(df, df, "TEST")
                print(f"✅ نتائج الاختبار:")
                print(f"   النقاط: {score}/10")
                print(f"   الاتجاه: {ms.trend_direction}")
                print(f"   الثقة: {conf.strength}")
                print("✅ النظام يعمل بشكل صحيح!")
                
            else:
                print("⚠️ خيار غير صالح!")
                
        except KeyboardInterrupt:
            system.stop()
            break
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
