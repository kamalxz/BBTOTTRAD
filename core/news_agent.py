"""
وكيل الأخبار - News Agent
يقوم بجلب الأخبار من مصادر RSS وفلترة الكلمات السلبية
"""
import feedparser
import re
from datetime import datetime, timedelta
from config import NEWS_SOURCES, NEGATIVE_KEYWORDS

class NewsAgent:
    def __init__(self):
        self.sources = NEWS_SOURCES
        self.negative_keywords = NEGATIVE_KEYWORDS
    
    def get_symbol_key(self, symbol: str) -> str:
        """استخراج مفتاح العملة من الرمز الكامل"""
        for key in self.sources.keys():
            if key in symbol:
                return key
        return 'DEFAULT'
    
    def check_negative_news(self, symbol: str, lookback_hours: int = 2) -> bool:
        """
        التحقق من وجود أخبار سلبية للعملة خلال آخر ساعتين
        returns: True إذا وجد خبر سلبي، False إذا كان الوضع آمناً
        """
        key = self.get_symbol_key(symbol)
        urls = self.sources.get(key, self.sources['DEFAULT'])
        
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:  # آخر 10 عناوين فقط
                    # التحقق من وقت النشر
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])
                        if pub_time < cutoff_time:
                            continue
                    
                    title = entry.title.lower()
                    summary = entry.summary.lower() if hasattr(entry, 'summary') else ''
                    
                    # البحث عن الكلمات السلبية
                    for keyword in self.negative_keywords:
                        if keyword in title or keyword in summary:
                            print(f"⚠️ تم رصد خبر سلبي لـ {symbol}: {entry.title}")
                            return True  # يوجد خبر سلبي
                
            except Exception as e:
                print(f"خطأ في جلب الأخبار من {url}: {e}")
                continue
        
        return False  # لا توجد أخبار سلبية
    
    def get_latest_news(self, symbol: str, count: int = 5) -> list:
        """جلب آخر العناوين الإخبارية للعملة"""
        key = self.get_symbol_key(symbol)
        urls = self.sources.get(key, self.sources['DEFAULT'])
        news_list = []
        
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:count]:
                    news_list.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else 'N/A'
                    })
            except:
                continue
        
        return news_list

# اختبار سريع
if __name__ == "__main__":
    agent = NewsAgent()
    print("Testing News Agent...")
    has_negative = agent.check_negative_news("BTC/USDT:USDT")
    print(f"BTC has negative news: {has_negative}")
