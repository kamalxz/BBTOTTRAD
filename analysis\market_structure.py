"""🧠 market_structure.py — أدوات هيكل السوق (Swing Points, BOS, CHoCH)"""
import pandas as pd
from typing import Optional, List, Dict


def detect_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> List[Dict]:
    """العثور على القمم والقيعان (Swing Highs/Lows) باستخدام نافذة من الجانبين.
    
    Args:
        df: إطار البيانات مع عومات high/low.
        window: عدد الشموع على كل جانب لتحديد القمة/القاع.

    Returns:
        قائمة بالقمم والقيعان مع إحداتها وفهارسها.
    """
    if len(df) < window * 2 + 1:
        return []

    points = []
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values

    for i in range(window, len(df) - window):
        # Swing High: أعلى قيمة في النافذة
        if highs[i] == max(highs[i - window : i + window + 1]):
            points.append({
                "index": i,
                "type": "high",
                "price": float(highs[i]),
                "timestamp": df.iloc[i]["timestamp"],
                "mitigated": False
            })

        # Swing Low: أقل قيمة في النافذة
        if lows[i] == min(lows[i - window : i + window + 1]):
            points.append({
                "index": i,
                "type": "low",
                "price": float(lows[i]),
                "timestamp": df.iloc[i]["timestamp"],
                "mitigated": False
            })

    points.sort(key=lambda x: x["index"])
    return points


def detect_bos(df: pd.DataFrame, swing_points: List[Dict], trend: str = "auto") -> Optional[Dict]:
    """اكتشاف BOS (Break of Structure) — كسر آخر هيكل رئيسي.

    Args:
        df: إطار البيانات.
        swing_points: القوائم المرتجعة من detect_swing_highs_lows.
        trend: "bullish"، "bearish"، أو "auto".

    Returns:
        قاموس يحتوي على نوع الـ BOS والسعر المكسور إذا وُجد.
    """
    if len(swing_points) < 2 or len(df) < 2:
        return None

    last_close = df["close"].iloc[-1]
    last_point = swing_points[-1]

    # BOS صعودي: كسر قمة سابقة
    if last_point["type"] == "high" and last_close > last_point["price"]:
        return {"type": "bullish_bos", "level": last_point["price"], "index": last_point["index"]}

    # BOS هابط: كسر قاع سابق
    if last_point["type"] == "low" and last_close < last_point["price"]:
        return {"type": "bearish_bos", "level": last_point["price"], "index": last_point["index"]}

    return None


def detect_choch(swing_points: List[Dict]) -> Optional[Dict]:
    """اكتشاف CHoCH (Change in Character) — تغيير في اتجاه السوق.

    يحدث عندما يتغير الاتجاه من صعودي إلى هبوطي (أو العكس)
    بكسر تسلسل القم أو القيعان.

    Args:
        swing_points: قائمة النقاط المرتجعة من detect_swing_highs_lows.

    Returns:
        قاموس يحتوي على نوع الـ CHoCH إذا وُجد.
    """
    if len(swing_points) < 3:
        return None

    # البحث عن تباباً في التسلسل (Higher Highs / Lower Lows)
    # إذا كان آخر نوعين متتاليين متقابلين (High ثم Low ثم High ...)
    recent = swing_points[-3:]

    types = [p["type"] for p in recent]
    prices = [p["price"] for p in recent]

    # نمط صعودي: Low → High → Higher Low
    if types == ["low", "high", "low"] and prices[-1] > prices[0]:
        return {"type": "bullish_choch", "level": prices[0]}

    # نمط هبوطي: High → Low → Lower High
    if types == ["high", "low", "high"] and prices[-1] < prices[0]:
        return {"type": "bearish_choch", "level": prices[0]}

    return None


def get_daily_bias(df_1d: pd.DataFrame, lookback: int = 10) -> str:
    """تحديد الاتجاه اليومي (Daily Bias).
    
    Args:
        df_1d: إطار البيانات اليومي.
        lookback: عدد الشموع السابقة للمقارنة.

    Returns:
        "bullish"، "bearish"، أو "neutral".
    """
    if len(df_1d) < 2:
        return "neutral"

    high_higher = df_1d["high"].iloc[-1] > df_1d["high"].iloc[-lookback]
    low_higher = df_1d["low"].iloc[-1] > df_1d["low"].iloc[-lookback]

    if high_higher and low_higher:
        return "bullish"
    elif not high_higher and not low_higher:
        return "bearish"
    else:
        return "neutral"


def get_major_liquidity(df_1d: pd.DataFrame, swing_window: int = 10) -> Dict:
    """العثور على أكبر مستويات السيولة (Liquidity) على الإطار اليومي.
    
    Args:
        df_1d: إطار البيانات اليومي.
        swing_window: نافذة الـ Swing Points.

    Returns:
        قاموس يحتوي على "support" و "resistance" الرئيسيين.
    """
    swing_points = detect_swing_highs_lows(df_1d, swing_window)
    highs = [p for p in swing_points if p["type"] == "high"]
    lows = [p for p in swing_points if p["type"] == "low"]

    # أقرب قمة وأقرب قاع
    if len(highs) > 0 and len(lows) > 0:
        return {
            "resistance": max(p["price"] for p in highs[-5:]) if len(highs) >= 5 else highs[-1]["price"],
            "support": min(p["price"] for p in lows[-5:]) if len(lows) >= 5 else lows[-1]["price"]
        }
    return {"resistance": df_1d["high"].iloc[-1], "support": df_1d["low"].iloc[-1]}
