"""Merkezi loglama yapılandırması."""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Kök logger'ı tek seferlik yapılandırır; tekrar çağrılırsa yalnızca seviyeyi günceller."""
    global _configured
    root = logging.getLogger()
    root.setLevel(level)
    if _configured:
        return

    # Windows konsolunda (cp1254/cp1252) Türkçe karakterlerin bozulmasını engelle
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.handlers = [handler]

    # Üçüncü parti kütüphanelerin gürültüsünü azalt
    for noisy in ("httpx", "httpx2", "httpcore", "urllib3", "huggingface_hub", "transformers", "prawcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Modül bazlı logger döndürür. Kullanım: `logger = get_logger(__name__)`."""
    return logging.getLogger(name)
