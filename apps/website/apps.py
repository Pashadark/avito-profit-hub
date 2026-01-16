# website/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import threading
import schedule
import time
import logging

# Используем правильный логгер для Django приложений
logger = logging.getLogger('dapps.website')  # ИЗМЕНИЛ: django.website вместо django.dashboard

class WebsiteConfig(AppConfig):  # ИЗМЕНИЛ: DashboardConfig → WebsiteConfig
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.website'
    verbose_name = _("Вебсайт")  # ИЗМЕНИЛ: "Панель управления" → "Вебсайт"

    def ready(self):
        """Запускается при старте Django"""
        if not self.is_scheduler_running():
            self.start_scheduler()

    def is_scheduler_running(self):
        """Проверяет, запущен ли уже планировщик"""
        return hasattr(self, '_scheduler_thread') and self._scheduler_thread.is_alive()

    def start_scheduler(self):
        """Запускает планировщик в фоновом потоке"""

        def run_scheduler():
            from django.core.management import call_command

            # Ежедневное задание в 00:01
            schedule.every().day.at("00:01").do(
                self.run_daily_charge
            )

            # Тестовое задание каждые 10 минут (для отладки)
            schedule.every(10).minutes.do(
                self.run_daily_charge_test
            )

            logger.info("🚀 Планировщик ежедневного списания запущен")

            while True:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Проверяем каждую минуту
                except Exception as e:
                    logger.error(f"❌ Ошибка в планировщике: {e}")
                    time.sleep(300)  # Ждем 5 минут при ошибке

        # Запускаем в отдельном потоке
        self._scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self._scheduler_thread.start()

    def run_daily_charge(self):
        """Запускает ежедневное списание"""
        try:
            from django.core.management import call_command
            logger.info("🔄 Запуск ежедневного списания...")
            call_command('deduct_daily_payments')
            logger.info("✅ Ежедневное списание завершено")
        except Exception as e:
            logger.error(f"❌ Ошибка при списании: {e}")

    def run_daily_charge_test(self):
        """Тестовый запуск (для отладки)"""
        try:
            from django.core.management import call_command
            logger.info("🧪 Тестовый запуск списания...")
            call_command('deduct_daily_payments')
        except Exception as e:
            logger.error(f"❌ Ошибка тестового списания: {e}")
