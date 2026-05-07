from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from rich.console import Console
    from rich.logging import RichHandler
except ModuleNotFoundError:
    Console = None
    RichHandler = None

class TelegramNotifier:
    """Non-blocking Telegram notifier using thread pool and session."""
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._executor = __import__("concurrent.futures").futures.ThreadPoolExecutor(max_workers=1)
        
        # Robust session with retries
        self._session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

    def send_message(self, text: str) -> None:
        if not self.token or not self.chat_id:
            return
        self._executor.submit(self._send_blocking, text)

    def _send_blocking(self, text: str) -> None:
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            resp = self._session.post(self._url, json=payload, timeout=5)
            resp.raise_for_status()
        except Exception:
            pass  # intentionally silent — Telegram failures must never block the trading loop

class TelegramLogHandler(logging.Handler):
    """Logging handler that routes ERROR and CRITICAL logs to Telegram."""
    def __init__(self, notifier: TelegramNotifier):
        super().__init__()
        self.notifier = notifier

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from utils.telegram_reporter import build_error_alert
            msg = self.format(record)
            self.notifier.send_message(build_error_alert(record.name, msg, record.levelname))
        except Exception:
            self.handleError(record)

_TELEGRAM_NOTIFIER: TelegramNotifier | None = None

def get_telegram_notifier() -> TelegramNotifier | None:
    return _TELEGRAM_NOTIFIER

class ColoredEmojiFormatter(logging.Formatter):
    """Custom formatter to add emojis and colors to terminal output."""
    COLORS = {
        'DEBUG': '\033[90m',       # Gray
        'INFO': '\033[92m',        # Green
        'WARNING': '\033[93m',     # Yellow
        'ERROR': '\033[91m',       # Red
        'CRITICAL': '\033[1;91m',  # Bold Red
    }
    EMOJIS = {
        'DEBUG': '🐛',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    RESET = '\033[0m'

    def format(self, record):
        # Make a copy so we don't modify the original record meant for the file handler
        record_copy = logging.makeLogRecord(record.__dict__)
        color = self.COLORS.get(record_copy.levelname, self.RESET)
        emoji = self.EMOJIS.get(record_copy.levelname, 'ℹ️')
        
        record_copy.levelname = f"{color}{emoji} {record_copy.levelname:<8}{self.RESET}"
        
        # Check if msg is a string before formatting to avoid issues with exceptions
        if isinstance(record_copy.msg, str):
            record_copy.msg = f"{color}{record_copy.msg}{self.RESET}"
            
        record_copy.name = f"\033[36m{record_copy.name}\033[0m" # Cyan for module name
        return super().format(record_copy)

def setup_logger(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    resolved_dir = Path(log_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    log_file = resolved_dir / "polytrade_bot.log"
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)

    # Console Handler with Color and Emojis
    console_formatter = ColoredEmojiFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    handlers: list[logging.Handler] = [file_handler, console_handler]

    # Attach telegram handler if settings are present
    from config.settings import get_settings
    settings = get_settings()
    global _TELEGRAM_NOTIFIER
    if settings.telegram_bot_token.get_secret_value() and settings.telegram_chat_id.get_secret_value():
        _TELEGRAM_NOTIFIER = TelegramNotifier(
            token=settings.telegram_bot_token.get_secret_value(),
            chat_id=settings.telegram_chat_id.get_secret_value()
        )
        tg_handler = TelegramLogHandler(notifier=_TELEGRAM_NOTIFIER)
        tg_handler.setLevel(logging.ERROR)
        # Use a simpler format for Telegram
        tg_formatter = logging.Formatter("%(name)s | %(message)s")
        tg_handler.setFormatter(tg_formatter)
        handlers.append(tg_handler)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(message)s",
        handlers=handlers,
        force=True,
    )

    logger = logging.getLogger("polytrade_bot")
    logger.info("Logger initialized | level=%s | dir=%s", log_level.upper(), resolved_dir.as_posix())

    # Mute overly verbose or raw library loggers
    for noisy_logger in [
        "py_clob_client_v2",
        "py_clob_client_v2.http_helpers.helpers",
        "urllib3.connectionpool"
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.CRITICAL)

    if RichHandler is None:
        logger.warning("Rich logging is unavailable; falling back to standard stream logging.")
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
