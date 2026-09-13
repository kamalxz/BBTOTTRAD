"""📰 news_alert_agent.py — نظام إنذار ذكي للأخبار الاقتصادية Tier 1 مع دعم Cloudflare AI + fallback"""
import json
import logging
import time
from datetime import datetime

import requests

import config

logger = logging.getLogger("news_alert")

_TELEGRAM_TOKEN = getattr(config, "TELEGRAM_BOT_TOKEN", "") or getattr(config, "TELEGRAM_TOKEN", "")
_CHAT_ID = getattr(config, "TELEGRAM_CHAT_ID", "") or getattr(config, "CHAT_ID", "")
_CF_TOKEN = getattr(config, "CLOUDFLARE_API_TOKEN", "")
_CF_ACCOUNT = getattr(config, "CLOUDFLARE_ACCOUNT_ID", "")


class NewsAlertAgent:
    name = "NEWS_ALERT"
    check_interval = 300  # 5 دقائق
    tier1_keywords = ("CPI", "FOMC", "NFP", "FED")
    _alerted_news: set[str] = set()  # تجنب التكرار

    def run(self):
        logger.info("📰 بدء مراقبة الأخبار الاقتصادية...")
        while True:
            try:
                news_list = self._fetch_calendar()
                for item in self._filter_tier1(news_list):
                    key = f"{item.get('title', '')}_{item.get('timestamp', '')}"
                    if key in self._alerted_news:
                        continue
                    self._alerted_news.add(key)

                    analysis = self._analyze_ai(item)
                    trade_idea = self._generate_trade_idea(item, analysis)
                    self._send_alert(item, analysis, trade_idea)

                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("🛑 إيقاف مراقبة الأخبار")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في مراقبة الأخبار: {e}")
                time.sleep(60)

    def _fetch_calendar(self):
        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            r = requests.get(url, timeout=10)
            return r.json() if r.ok else []
        except Exception as e:
            logger.warning(f"⚠️  فشل جلب التقويم الاقتصادي: {e}")
            return []

    def _filter_tier1(self, news_list):
        filtered = []
        for item in news_list:
            title = item.get("title", "")
            impact = item.get("impact", "")
            if any(kw in title for kw in self.tier1_keywords) and impact in ("High", "Holiday"):
                filtered.append(item)
                logger.info(f"🎯 خبر Tier 1: {title}")
        return filtered

    def _analyze_ai(self, news_item):
        if not _CF_TOKEN or not _CF_ACCOUNT:
            return None

        title = news_item.get("title", "")
        forecast = news_item.get("forecast", "N/A")
        previous = news_item.get("previous", "N/A")

        prompt = (
            f"أنت محلل اقتصادي في أسواق الكريبتو. "
            f"حلّل هذا الخبر وأظهر التأثير المتوقع على BTC و ETH:\n"
            f"العنوان: {title}\nالتوقعات: {forecast}\nالسابق: {previous}\n"
            f"أجب بصيغة JSON:\n"
            f'{{"impact": "Bullish/Bearish/Neutral", "reason": "...", "confidence": "High/Medium/Low"}}'
        )

        # نسخة 1: Cloudflare Workers AI (نموذج Llama 3.1)
        url = f"https://api.cloudflare.com/client/v4/accounts/{_CF_ACCOUNT}/ai/run/@cf/meta/llama-3.1-8b-instruct"
        headers = {"Authorization": f"Bearer {_CF_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messages": [
                {"role": "system", "content": "أنت محلل اقتصادي خبير."},
                {"role": "user", "content": prompt}
            ]
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            if r.ok:
                result = r.json().get("result", {})
                # ✅ Cloudflare Llama 3.1 يرجع الـ JSON مباشرةً كـ object
                if isinstance(result, dict) and "impact" in result:
                    return result
                resp = result.get("response", str(result))
                if isinstance(resp, dict):
                    return resp  # الـ JSON مباشرة
                start, end = resp.find("{"), resp.rfind("}") + 1
                if start != -1:
                    return json.loads(resp[start:end])
            else:
                logger.warning(f"⚠️  Cloudflare AI غير متاح ({r.status_code}) — نستخدم القواعد")
        except Exception as e:
            logger.warning(f"⚠️  خطأ في Cloudflare AI: {e} — نستخدم التحليل القواعدي")

        # Fallback: تحليل قواعدي بسيط
        return self._rule_based_fallback(title)

    def _rule_based_fallback(self, title: str) -> dict:
        """تحليل بديل إذا فشل AI"""
        title_lower = title.lower()
        if any(kw in title_lower for kw in ("cpi", "gdp", "nfp")):
            if "core" in title_lower:
                return {"impact": "Neutral", "reason": "CPI Core قد لا يؤثر كثيراً على الكريبتو", "confidence": "Medium"}
            return {"impact": "Neutral", "reason": "التأثير غير مؤكد — راقب التفاعل الفعلي للسعر", "confidence": "Low"}
        return {"impact": "Neutral", "reason": "تحليل مبدئي — راجع التحركات السعرية", "confidence": "Low"}

    def _generate_trade_idea(self, news_item, analysis):
        if not analysis:
            return None
        impact = analysis.get("impact", "Neutral")
        if impact == "Neutral":
            return {"direction": "Hold", "reason": analysis.get("reason", ""), "sl_hint": "انتظر التوضح"}
        elif impact == "Bullish":
            return {
                "direction": "Long",
                "entry_strategy": "انتظر إغلاق شمعتين على 1m بعد 60s، ثم ادخل إذا CHoCH صاعد",
                "sl_hint": "تحت آخر قاع على فريم 1m",
                "tp_hint": "أعلى قمة على فريم 5 دقائق",
            }
        else:
            return {
                "direction": "Short",
                "entry_strategy": "انتظر إغلاق شمعتين على 1m بعد 60s، ثم ادخل إذا CHoCH هابط",
                "sl_hint": "فوق آخر قمة على فريم 1m",
                "tp_hint": "أدنى قاع على فريم 5 دقائق",
            }

    def _send_alert(self, news_item, analysis, trade_idea):
        title = news_item.get("title", "خبر اقتصادي")
        forecast = news_item.get("forecast", "N/A")
        impact = news_item.get("impact", "N/A")
        timestamp = news_item.get("timestamp", datetime.utcnow().isoformat())

        msg = f"🚨 *تنبيه خبر اقتصادي مهم!*\n\n📰 {title}\n📊 التوقع: {forecast}\n⚡ الأثر: {impact}\n🕐 الوقت: {timestamp}\n\n"

        if analysis:
            msg += f"🧠 التحليل: {analysis.get('impact', 'N/A')} ({analysis.get('confidence', 'N/A')})\n💡 {analysis.get('reason', '')}\n\n"
        else:
            msg += "⚠️ لم يتم التحليل بعد — راقب السعر يدوياً.\n\n"

        if trade_idea:
            msg += (
                f"💡 *فكرة تداول مبدئية:*\n"
                f"• الاتجاه: {trade_idea.get('direction', 'N/A')}\n"
                f"• استراتيجية الدخول: {trade_idea.get('entry_strategy', 'N/A')}\n"
                f"• SL: {trade_idea.get('sl_hint', 'N/A')}\n"
                f"• TP: {trade_idea.get('tp_hint', 'N/A')}\n\n"
            )

        msg += "⏰ *تذكير:* لا تدخل أثناء الخبر! انتظر 60 ثانية على الأقل."

        if not _TELEGRAM_TOKEN or not _CHAT_ID:
            logger.warning(f"[توثيق فقط] {msg}")
            return

        url = f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": _CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.ok:
                logger.info("✅ إشعار تلغرام أُرسل")
            else:
                logger.error(f"❌ فشل إرسال تلغرام: {r.status_code}")
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال التلغرام: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = NewsAlertAgent()

    # اختبار جلب الأخبار
    news = agent._fetch_calendar()
    print(f"\n📰 الأخبار القادمة: {len(news)}")

    # اختبار الفلترة
    tier1 = agent._filter_tier1(news)
    print(f"🎯 أخبار Tier 1: {len(tier1)}")

    # اختبار التحليل (مع fallback)
    if tier1:
        test_news = tier1[0]
        print(f"\n🧠 اختبار تحليل AI للخبر: {test_news.get('title')}")
        analysis = agent._analyze_ai(test_news)
        print(f"📊 التحليل: {analysis}")
