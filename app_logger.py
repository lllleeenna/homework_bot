import logging
import sys
from logging import StreamHandler


def get_stream_handler():
    """Хэндлер для вывода логов в stdout."""
    handler = StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    return handler


def get_logger(name):
    """Получить логер."""
    logging.basicConfig(
        level=logging.INFO,
        handlers=[get_stream_handler()]
    )
    return logging.getLogger(name)
