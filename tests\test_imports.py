"""🧪 tests/test_imports.py — فحص استيراد جميع الوحدات والبوتات"""

import pytest


# ─── Core ───
def test_telegram_alerts_imports():
    from core.telegram_alerts import send_telegram_alert, format_trade_alert
    assert callable(send_telegram_alert)
    assert callable(format_trade_alert)


def test_exchange_imports():
    from core.exchange import BinanceExchange
    assert hasattr(BinanceExchange, "create_futures_order")
    assert hasattr(BinanceExchange, "create_spot_limit_buy_order")
    assert hasattr(BinanceExchange, "fetch_positions")
    assert hasattr(BinanceExchange, "get_funding_rate")


# ─── Analysis ───
def test_analysis_imports():
    from analysis import (
        detect_fvg,
        detect_ob,
        check_fvg_mitigation,
        check_ob_mitigation,
        detect_bos,
        detect_choch,
        get_daily_bias,
        get_major_liquidity,
    )
    assert all(callable(fn) for fn in [
        detect_fvg, detect_ob, check_fvg_mitigation, check_ob_mitigation,
        detect_bos, detect_choch, get_daily_bias, get_major_liquidity,
    ])


# ─── Modes ───
def test_scalper_imports():
    from modes.scalper import ScalperBot
    assert ScalperBot.name == "SCALPER"
    assert ScalperBot.scalp_leverage <= 3


def test_day_trader_imports():
    from modes.day_trader import DayTraderBot
    assert DayTraderBot.name == "DAY TRADER"
    assert DayTraderBot.scalp_leverage <= 5


def test_swing_trader_imports():
    from modes.swing_trader import SwingTraderBot
    assert SwingTraderBot.name == "SWING_TRADER"


def test_position_trader_imports():
    from modes.position_trader import PositionTraderBot
    assert PositionTraderBot.name == "POSITION_TRADER"
    assert PositionTraderBot.margin_type == "spot"
    assert PositionTraderBot.leverage == 1


def test_position_trader_futures_imports():
    from modes.position_trader_futures import PositionTraderFuturesBot
    assert PositionTraderFuturesBot.name == "POSITION_TRADER_FUTURES"
    assert PositionTraderFuturesBot.leverage <= 3
    assert PositionTraderFuturesBot.margin_type == "isolated"
    assert PositionTraderFuturesBot.min_rr_ratio >= 5.0
    assert PositionTraderFuturesBot.max_position_duration == 7_776_000  # 90 يومًا


# ─── Config ───
def test_config_exists():
    import config
    assert hasattr(config, "SYMBOLS")
    assert hasattr(config, "SANDBOX_MODE")
    assert hasattr(config, "TELEGRAM_BOT_TOKEN")
    assert config.TELEGRAM_CHAT_ID  # غير فارغ


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
