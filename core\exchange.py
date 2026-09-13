"""🔌 BinanceExchange — جسر احترافي للتواصل مع Binance API (Futures + Spot)"""
import logging
from typing import Optional

import ccxt
import pandas as pd

try:
    import config
except ImportError:
    config = None

logger = logging.getLogger("exchange")


class BinanceExchange:
    """جسر يدعم كلاً من Futures و Spot Trading."""

    def __init__(self):
        self.api_key = getattr(config, "BINANCE_API_KEY", "") or getattr(config, "API_KEY", "") or ""
        self.api_secret = getattr(config, "BINANCE_API_SECRET", "") or getattr(config, "SECRET_KEY", "") or ""
        self.sandbox_mode = getattr(config, "SANDBOX_MODE", True)

        common_opts = {"adjustForTimeDifference": True}

        # ✅ دعم البروكسي — يتم تمريره إلى ccxt إذا كان مفعّلاً
        proxies = getattr(config, "PROXY_DICT", {}) if getattr(config, "USE_PROXY", False) else {}

        self.futures = ccxt.binance({
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "options": {"defaultType": "future", **common_opts},
            "enableRateLimit": True,
            "proxies": proxies if proxies else None,
        })

        self.spot = ccxt.binance({
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "options": {"defaultType": "spot", **common_opts},
            "enableRateLimit": True,
            "proxies": proxies if proxies else None,
        })

        if self.sandbox_mode:
            self.futures.set_sandbox_mode(True)
            self.spot.set_sandbox_mode(True)
            logger.info("🧪 وضع Sandbox (Paper Trading) مفعّل")

        logger.info("✅ تم تهيئة Binance Exchange بنجاح")

    def _handle_api_error(self, error: Exception) -> None:
        """معالجة أخطاء API — يرسل IP الحالي إذا كان السبب غير مصرح به."""
        try:
            from core.telegram_alerts import send_telegram_alert
            from core.ip_utils import get_proxy_ip

            error_msg = str(error)
            # الأخطاء الناتجة عن IP غير مصرح به
            if any(code in error_msg for code in ["-2015", "-2019"]) or "Invalid" in error_msg or "permissions" in error_msg.lower():
                current_ip = get_proxy_ip()
                logger.warning(f"⚠️  IP غير مصرح به: {current_ip}")
                send_telegram_alert(
                    f"<b>⚠️ IP غير مصرح به على بنانس</b>\n\n"
                    f"🌍 <b>الـ IP الحالي:</b> <code>{current_ip}</code>\n\n"
                    f"📝 <b>ما تفعله:</b>\n"
                    f"أضف هذا الـ IP إلى Binance API Management:\n"
                    f"https://www.binance.com/en/my/settings/settings/api-management\n"
                    f"\n⚠️ <b>ملاحظة:</b> الـ IP تغّر بسبب البروكسي — قد تحتاج إلى تحديثه كل مرة يتغيّر فيها."
                )
        except Exception:
            pass

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        market_type: str = "futures",
    ) -> pd.DataFrame:
        """جلب بيانات الشموع (OHLCV) من Binance."""
        try:
            exchange = self.futures if market_type == "futures" else self.spot
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not ohlcv:
                logger.warning(f"⚠️ لم يتم استلام بيانات لـ {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            logger.info(f"✅ {len(df)} شمعة لـ {symbol} على فريم {timeframe}")
            return df

        except Exception as e:
            self._handle_api_error(e)
            logger.error(f"❌ خطأ في جلب بيانات {symbol}: {e}")
            return pd.DataFrame()

    def fetch_current_price(self, symbol: str, market_type: str = "futures") -> Optional[float]:
        try:
            exchange = self.futures if market_type == "futures" else self.spot
            ticker = exchange.fetch_ticker(symbol)
            return ticker["last"]
        except Exception as e:
            self._handle_api_error(e)
            logger.error(f"❌ خطأ في جلب سعر {symbol}: {e}")
            return None

    def get_balance(self, market_type: str = "futures") -> dict:
        try:
            exchange = self.futures if market_type == "futures" else self.spot
            balance = exchange.fetch_balance()
            usdt = balance.get("USDT", {})
            return {
                "total": usdt.get("total", 0),
                "free": usdt.get("free", 0),
                "used": usdt.get("used", 0),
            }
        except Exception as e:
            self._handle_api_error(e)
            logger.error(f"❌ خطأ في جلب الرصيد: {e}")
            return {"total": 0, "free": 0, "used": 0}

    def fetch_positions(self, symbols: list[str] | None = None) -> list[dict]:
        """جلب المراكز المفتوحة على المستقبل."""
        try:
            return self.futures.fetch_positions(symbols)
        except Exception as e:
            self._handle_api_error(e)
            logger.error(f"❌ خطأ في جلب المراكز: {e}")
            return []

    def create_futures_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: Optional[float] = None,
        leverage: int = 3,
        margin_type: str = "isolated",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[dict]:
        """إنشاء أمر Futures مع SL/TP."""
        try:
            self.futures.set_leverage(leverage, symbol)
            self.futures.set_margin_mode(margin_type, symbol)

            params = {}
            if stop_loss:
                params["stopLoss"] = {"triggerPrice": stop_loss, "type": "MARKET"}
            if take_profit:
                params["takeProfit"] = {"triggerPrice": take_profit, "type": "MARKET"}

            if order_type == "limit":
                if not price:
                    raise ValueError("السعر مطلوب للأوامر المحددة")
                order = self.futures.create_order(
                    symbol=symbol, type="limit", side=side,
                    amount=amount, price=price, params={**params, "timeInForce": "GTC"},
                )
            else:
                order = self.futures.create_order(
                    symbol=symbol, type="market", side=side, amount=amount, params=params
                )

            logger.info(f"✅ أمر Futures: {side.upper()} {amount} {symbol}")
            return order
        except Exception as e:
            logger.error(f"❌ خطأ في أمر Futures: {e}")
            return None

    def close_futures_position(self, symbol: str, side: str, amount: float) -> Optional[dict]:
        """إغلاق مركز Futures باستخدام reduceOnly."""
        try:
            close_side = "sell" if side == "buy" else "buy"
            order = self.futures.create_order(
                symbol=symbol, type="market", side=close_side,
                amount=amount, params={"reduceOnly": True},
            )
            logger.info(f"✅ إغلاق مركز Futures: {symbol}")
            return order
        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق مركز Futures: {e}")
            return None

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        try:
            rate = self.futures.fetch_funding_rate(symbol)
            return rate.get("fundingRate", 0)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب Funding Rate: {e}")
            return None

    def create_spot_limit_buy_order(
        self, symbol: str, quote_amount: float, price: float
    ) -> Optional[dict]:
        """إنشاء أمر Spot Limit Buy باستخدام quote_amount (USDT)."""
        try:
            quantity = self.spot.amount_to_precision(symbol, quote_amount / price)
            price_prec = self.spot.price_to_precision(symbol, price)
            order = self.spot.create_order(
                symbol=symbol, type="limit", side="buy",
                amount=quantity, price=price_prec, params={"timeInForce": "GTC"},
            )
            logger.info(f"✅ أمر Spot Buy: {quantity} {symbol} @ {price_prec} ({quote_amount}$)")
            return order
        except Exception as e:
            logger.error(f"❌ خطأ في أمر Spot Buy: {e}")
            return None

    def get_open_orders(self, symbol: str, market_type: str = "spot"):
        try:
            exchange = self.futures if market_type == "futures" else self.spot
            return exchange.fetch_open_orders(symbol)
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الأوامر المفتوحة: {e}")
            return []

    def cancel_order(self, order_id: str, symbol: str, market_type: str = "spot") -> bool:
        try:
            exchange = self.futures if market_type == "futures" else self.spot
            exchange.cancel_order(order_id, symbol)
            logger.info(f"✅ إلغاء الأمر {order_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إلغاء الأمر {order_id}: {e}")
            return False
