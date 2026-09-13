"""🧠 market_structure.py — أدوات هيكل السوق (Swing Points, BOS, CHoCH)"""
import pandas as pd
from typing import Optional, List, Dict


def detect_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> List[Dict]:
    """العثور على القمم والقيعان (Swing Highs/Lows) باستخدام نافذة من الجانبين."""
    if len(df) < window * 2 + 1:
        return []

    points = []
    highs = df["high"].values
    lows = df["low"].values
    
    if hasattr(df.index, 'to_series'):
        timestamps = df.index.to_series()
    elif "timestamp" in df.columns:
        timestamps = df["timestamp"]
    else:
        timestamps = range(len(df))

    for i in range(window, len(df) - window):
        if highs[i] == max(highs[i - window : i + window + 1]):
            points.append({
                "index": i,
                "type": "high",
                "price": float(highs[i]),
                "timestamp": timestamps.iloc[i] if hasattr(timestamps, 'iloc') else timestamps[i],
                "mitigated": False
            })

        if lows[i] == min(lows[i - window : i + window + 1]):
            points.append({
                "index": i,
                "type": "low",
                "price": float(lows[i]),
                "timestamp": timestamps.iloc[i] if hasattr(timestamps, 'iloc') else timestamps[i],
                "mitigated": False
            })

    points.sort(key=lambda x: x["index"])
    return points


def detect_bos(df: pd.DataFrame, swing_points: List[Dict], trend: str = "auto") -> Optional[Dict]:
    """اكتشاف BOS (Break of Structure)."""
    if len(swing_points) < 2 or len(df) < 2:
        return None

    last_close = df["close"].iloc[-1]
    last_point = swing_points[-1]

    if last_point["type"] == "high" and last_close > last_point["price"]:
        return {"type": "bullish_bos", "level": last_point["price"], "index": last_point["index"]}

    if last_point["type"] == "low" and last_close < last_point["price"]:
        return {"type": "bearish_bos", "level": last_point["price"], "index": last_point["index"]}

    return None


def detect_choch(swing_points: List[Dict]) -> Optional[Dict]:
    """اكتشاف CHoCH (Change in Character)."""
    if len(swing_points) < 3:
        return None

    recent = swing_points[-3:]
    types = [p["type"] for p in recent]
    prices = [p["price"] for p in recent]

    if types == ["low", "high", "low"] and prices[2] > prices[0]:
        return {"type": "bullish_choch", "level": prices[1]}

    if types == ["high", "low", "high"] and prices[2] < prices[0]:
        return {"type": "bearish_choch", "level": prices[1]}

    return None
