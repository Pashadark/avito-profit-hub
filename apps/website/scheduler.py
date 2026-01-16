import schedule
import time
import threading
import logging
from django.utils import timezone
from apps.website.utils.subscription_utils import deduct_daily_payments, check_subscription_health

logger = logging.getLogger('scheduler')


class SubscriptionScheduler:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.scheduler_thread = None

    def run_daily_charge(self):
        """Ежедневное списание в 06:00"""
        try:
            logger.info("💰 === ЗАПУСК ЕЖЕДНЕВНОГО СПИСАНИЯ ===")
            result = deduct_daily_payments()

            if result:
                logger.info("✅ Ежедневное списание завершено успешно")
            else:
                logger.warning("⚠️ Ежедневное списание завершено с проблемами")

            return result
        except Exception as e:
            logger.error(f"❌ Ошибка ежедневного списания: {e}")
            return False

    def run_health_check(self):
        """Проверка здоровья в 00:30"""
        try:
            logger.info("🔧 === ЗАПУСК ПРОВЕРКИ ЗДОРОВЬЯ ПОДПИСОК ===")
            result = check_subscription_health()

            if result:
                logger.info("✅ Проверка здоровья завершена успешно")
            else:
                logger.warning("⚠️ Проверка здоровья завершена с проблемами")

            return result
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья: {e}")
            return False

    def start(self):
        """Запуск планировщика"""
        if self.is_running:
            logger.warning("⚠️ Планировщик уже запущен")
            return False

        logger.info("🚀 Запуск планировщика подписок...")
        self.is_running = True

        # Настраиваем расписание
        schedule.every().day.at("06:00").do(self.run_daily_charge)
        schedule.every().day.at("00:30").do(self.run_health_check)

        # Запускаем в отдельном потоке
        def run_scheduler():
            logger.info("✅ Планировщик подписок запущен")
            logger.info("🤖 Умное списание будет выполняться ежедневно в 06:00")
            logger.info("🔧 Проверка здоровья подписок в 00:30")

            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Проверяем каждую минуту
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка в планировщике: {e}")
                    time.sleep(300)  # Ждем 5 минут при ошибке

        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("✅ Планировщик запущен в фоновом режиме")
        return True

    def stop(self):
        """Остановка планировщика"""
        if not self.is_running:
            return True

        logger.info("🛑 Остановка планировщика подписок...")
        self.is_running = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)

        logger.info("✅ Планировщик остановлен")
        return True

    def get_status(self):
        """Получить статус планировщика"""
        status = "✅ Запущен" if self.is_running else "❌ Остановлен"
        next_run = "Не доступно"

        try:
            # Получаем следующее запланированное задание
            jobs = schedule.get_jobs()
            if jobs:
                next_run = str(jobs[0].next_run) if hasattr(jobs[0], 'next_run') else "Скоро"
        except:
            next_run = "Ошибка получения"

        return {
            'running': self.is_running,
            'status': status,
            'next_run': next_run,
            'jobs_count': len(schedule.get_jobs())
        }


# Глобальный экземпляр
scheduler = SubscriptionScheduler()