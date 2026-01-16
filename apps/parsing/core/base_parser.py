import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Базовый класс для всех парсеров"""

    def __init__(self):
        self.is_running = False
        # 🔥 ДОБАВЬТЕ ЭТОТ АТРИБУТ:
        self.stats = {
            'total_processed': 0,
            'duplicates_skipped': 0,
            'good_deals_found': 0,
            'vision_checks': 0,
            'vision_rejected': 0
        }

    @abstractmethod
    async def start(self):
        """Запускает парсер"""
        pass

    @abstractmethod
    def stop(self):
        """Останавливает парсер"""
        pass

    @abstractmethod
    def update_settings(self, settings_data):
        """Обновляет настройки парсера"""
        pass

    def get_status(self):
        """Возвращает базовый статус парсера"""
        return {
            'is_running': self.is_running,
            'stats': self.stats
        }