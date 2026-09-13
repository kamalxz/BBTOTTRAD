"""⏰ فلتر الوقت — Killzones، Silver Bullets، أيام تجارية، أخبار اقتصادية (UTC) يدعم الباكتيست"""
import logging
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)


class TimeFilter:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def is_good_trading_day_at(dt: datetime) -> bool:
        return dt.weekday() not in config.BAD_WEEKDAYS

    @staticmethod
    def is_good_trading_day() -> bool:
        return TimeFilter.is_good_trading_day_at(TimeFilter._now())

    @staticmethod
    def is_good_trading_time_at(dt: datetime) -> bool:
        if not TimeFilter.is_good_trading_day_at(dt):
            return False
        hour = dt.hour
        return not (hour >= config.TRADING_END_HOUR or hour < config.TRADING_START_HOUR)

    @staticmethod
    def is_good_trading_time() -> bool:
        return TimeFilter.is_good_trading_time_at(TimeFilter._now())

    @staticmethod
    def get_killzone_at(dt: datetime) -> tuple:
        t = dt.hour + dt.minute / 60.0
        for sb in config.SILVER_BULLETS_UTC:
            if sb <= t < sb + 1:
                return f"Silver Bullet {int(sb)}:00 UTC", True
        for start, end in config.KILLZONES_UTC:
            if start <= t < end:
                session = "London" if start <= 12.0 else "New York"
                return session, True
        return 'None', False

    @staticmethod
    def get_killzone() -> tuple:
        return TimeFilter.get_killzone_at(TimeFilter._now())

    @staticmethod
    def is_news_time_at(dt: datetime) -> bool:
        wd, day = dt.weekday(), dt.day
        hour, minute = dt.hour, dt.minute
        m = config.NEWS_BLACKOUT_MINUTES

        for name, blk in config.NEWS_BLACKOUTS.items():
            bw = blk.get('weekday')
            if bw is not None:
                if isinstance(bw, list):
                    if wd not in bw:
                        continue
                elif wd != bw:
                    continue
            if 'day_max' in blk and day > blk['day_max']:
                continue
            if 'day_min' in blk and day < blk['day_min']:
                continue

            event_t = blk['hour'] + blk['minute'] / 60.0
            t = hour + minute / 60.0
            if event_t - m / 60.0 <= t <= event_t + m / 60.0:
                logger.warning(f"منع التداول: {name} خلال الناف�ذة الإخبارية")
                return True
        return False

    @staticmethod
    def is_news_time() -> bool:
        return TimeFilter.is_news_time_at(TimeFilter._now())

    @staticmethod
    def check_trading_filters() -> bool:
        if not TimeFilter.is_good_trading_time():
            return False
        return not TimeFilter.is_news_time()

    @staticmethod
    def is_killzone() -> bool:
        """True إذا كنا داخل Killzone."""
        return TimeFilter.get_killzone()[1]

    @staticmethod
    def is_within_killzone() -> bool:
        """Alias for is_killzone."""
        return TimeFilter.is_killzone()

    @staticmethod
    def is_news_release_soon(minutes: int = 15) -> bool:
        """True إذا كانت هناك إطلاق أخبار خلال `minutes` القادمة."""
        now = TimeFilter._now()
        for blk in config.NEWS_BLACKOUTS.values():
            event_t = blk["hour"] + blk["minute"] / 60.0
            current_t = now.hour + now.minute / 60.0
            if abs(event_t - current_t) <= minutes / 60.0:
                return True
        return False
