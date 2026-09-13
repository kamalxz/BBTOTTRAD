"""🤖 محلل الأخبار بالذكاء الاصطناعي (Cloudflare Llama 3.1) - محدث"""
import ast
import json
import logging
import re
from datetime import datetime, timezone

import feedparser
import requests

import config

logger = logging.getLogger(__name__)


class AINewsAgent:
    def __init__(self, account_id: str = None, api_token: str = None):
        self.account_id = (account_id or config.CLOUDFLARE_ACCOUNT_ID or
                           config.CF_ACCOUNT_ID or '').strip()
        self.api_token = (api_token or config.CLOUDFLARE_API_TOKEN or
                          config.CF_API_TOKEN or '').strip()
        self.model = "@cf/meta/llama-3.1-8b-instruct"
        self.cache: dict = {}
        self.sources = config.NEWS_SOURCES

    def _parse(self, content) -> tuple:
        if not isinstance(content, str):
            content = json.dumps(content) if isinstance(content, (dict, list)) else str(content)
        content = content.replace("```json", "").replace("```", "").strip()
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return 0.0, 'فشل التحليل'
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            try:
                data = ast.literal_eval(m.group(0))
            except (ValueError, SyntaxError) as e:
                logger.debug(f"AST parse failed: {e}")
                return 0.0, 'فشل التحليل'
        try:
            return float(data.get('sentiment', 0.0)), str(data.get('summary', 'تم التحليل'))
        except (TypeError, ValueError, KeyError) as e:
            logger.debug(f"Unexpected AI data format: {e}")
            return 0.0, 'تنسيق غير معروف'

    def analyze_news(self, symbol: str) -> tuple:
        if not self.api_token or not self.account_id:
            return 0.0, 'AI غير مفعّل'

        coin = symbol.split('/')[0].replace(':USDT', '')
        now = datetime.now(timezone.utc)

        if coin in self.cache:
            t, data = self.cache[coin]
            if (now - t).total_seconds() < config.NEWS_CACHE_MINUTES * 60:
                return data

        headlines = []
        for url in self.sources.get(coin, self.sources['DEFAULT']):
            try:
                # يعمل مباشرة — بدون بروكسي
                r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                feed = feedparser.parse(r.text)
                headlines += [e.title for e in feed.entries[:5]]
            except Exception as e:
                logger.debug(f"News fetch failed for {url}: {e}")

        if not headlines:
            return 0.0, 'لا توجد أخبار'

        prompt = (
            f"Analyze crypto news for '{coin}'. Return ONLY a JSON object: "
            f'{{"sentiment": <float -1 to 1>, "summary": <string>}}. '
            f"Headlines: {chr(10).join(headlines)}"
        )
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
            headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
            # يعمل مباشرة — بدون بروكسي
            r = requests.post(url, headers=headers,
                              json={"messages": [{"role": "user", "content": prompt}]},
                              timeout=15)
            content = r.json().get('result', {}).get('response', '{}')
            result = self._parse(content)
            self.cache[coin] = (now, result)
            return result
        except Exception as e:
            logger.debug(f"AI error: {e}")
            return 0.0, 'خطأ في الاتصال'
