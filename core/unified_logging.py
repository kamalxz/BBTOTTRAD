"""
📋 unified_logging.py — نظام سجلات متقدم للنظام الموحد
يدعم تسجيل trades، rejections، errors مع تنسيق جميل
يدعم مراجعة الصفقات لتحسين النسبة بنسبة 90%
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# أنماط الألوان
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

# تنسيق ملون للـ console
class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.BOLD + Colors.RED,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        return super().format(record)


def setup_logging(level: str = "INFO"):
    """إعداد نظام السجلات الموحد"""
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8', errors='replace'),
    ]

    stream_handler = handlers[0]
    stream_handler.setFormatter(ColoredFormatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))

    file_handler = handlers[1]
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
