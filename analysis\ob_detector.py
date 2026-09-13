"""🎯 ob_detector.py — كشف مناطق الطلب/العرض (Order Blocks)"""
import pandas as pd


def detect_order_blocks(df: pd.DataFrame) -> list:
    """يكتشف مناطق الطلب/العرض بناءً على الشموع المتمردة (Pin Bars) والسياق السعري.

    Bullish OB: شمعة تراجعية (Bearish) تليها شمعة صعودية تؤكد الكسر.
    Bearish OB: شمعة صعودية (Bullish) تليها شمعة هبوطية تؤكد الكسر.
    """
    if len(df) < 3:
        return []

    obs = []
    for i in range(1, len(df) - 1):
        current = df.iloc[i]
        next_candle = df.iloc[i + 1]

        if current["close"] < current["open"]:
            if next_candle["close"] > next_candle["open"] and next_candle["close"] > current["high"]:
                obs.append({
                    "index": i,
                    "type": "bullish",
                    "top": float(current["high"]),
                    "bottom": float(min(current["open"], current["close"])),
                    "confirmed": True,
                })
        elif current["close"] > current["open"]:
            if next_candle["close"] < next_candle["open"] and next_candle["close"] < current["low"]:
                obs.append({
                    "index": i,
                    "type": "bearish",
                    "top": float(max(current["open"], current["close"])),
                    "bottom": float(current["low"]),
                    "confirmed": True,
                })

    return obs


def check_ob_mitigation(df: pd.DataFrame, obs: list) -> list:
    """تتحقق مما إذا تم اختبار/تعبئة منطقة الطلب/العرض."""
    for ob in obs:
        start_idx = ob["index"] + 1
        if start_idx >= len(df):
            continue
        subsequent = df.iloc[start_idx:]
        if ob["type"] == "bullish" and (subsequent["low"] <= ob["top"]).any():
            ob["mitigated"] = True
        elif ob["type"] == "bearish" and (subsequent["high"] >= ob["bottom"]).any():
            ob["mitigated"] = True
    return obs
