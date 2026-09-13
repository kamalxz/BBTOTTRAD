"""🎯 fvg_detector.py — كشف فجوات القيمة العادلة (Fair Value Gaps)"""
import pandas as pd


def detect_fvg(df: pd.DataFrame) -> list:
    """يكتشف فجوات القيمة العادلة (FVG) في بيانات الشموع.

    Bullish FVG: Low الحالية > High الشمعة (i-2)
    Bearish FVG: High الحالية < Low الشمعة (i-2)
    """
    if len(df) < 3:
        return []

    fvgs = []
    for i in range(2, len(df)):
        candle_1 = df.iloc[i - 2]
        candle_3 = df.iloc[i]

        if candle_3["low"] > candle_1["high"]:
            fvgs.append({
                "index": i,
                "type": "bullish",
                "top": float(candle_3["low"]),
                "bottom": float(candle_1["high"]),
                "mitigated": False,
            })
        elif candle_3["high"] < candle_1["low"]:
            fvgs.append({
                "index": i,
                "type": "bearish",
                "top": float(candle_1["low"]),
                "bottom": float(candle_3["high"]),
                "mitigated": False,
            })
    return fvgs


def check_mitigation(df: pd.DataFrame, fvgs: list) -> list:
    """تتحقق مما إذا تم تعبئة (Mitigate) الفجوة بواسطة شمعة لاحقة."""
    for fvg in fvgs:
        if fvg["mitigated"]:
            continue
        start_idx = fvg["index"] + 1
        if start_idx >= len(df):
            break
        subsequent = df.iloc[start_idx:]
        if fvg["type"] == "bullish" and (subsequent["low"] <= fvg["top"]).any():
            fvg["mitigated"] = True
        elif fvg["type"] == "bearish" and (subsequent["high"] >= fvg["bottom"]).any():
            fvg["mitigated"] = True
    return fvgs
