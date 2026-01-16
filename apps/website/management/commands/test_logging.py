from django.core.management.base import BaseCommand
import logging
import time

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from dashboard.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")
        print(f"[SAFE_LOG] {message}")
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Тестирование системы логирования'

    def handle(self, *args, **options):
        logger.info("Начало теста логирования")

        # Тестовые сообщения разных уровней
        logger.debug("Отладочное сообщение")
        logger.info("Информационное сообщение")
        logger.warning("Предупреждение")
        logger.error("Ошибка")
        logger.critical("Критическая ошибка")

        # Имитация работы
        for i in range(5):
            logger.info(f"Тестовая итерация {i + 1}")
            time.sleep(1)

        logger.info("Тест завершен")