import asyncio
import time
import logging
from datetime import datetime, timedelta

# Настройка логгера
logger = logging.getLogger('parser.timer')


class TimerManager:
    """УЛУЧШЕННЫЙ менеджер времени и циклов парсера с поддержкой таймера"""

    def __init__(self, check_interval=180):
        self.check_interval = check_interval
        self.cycle_count = 0
        self.timer_hours = None
        self.start_time = None
        self.is_timer_active = False
        self.last_settings_check = time.time()

        logger.info("⏰ Таймер-менеджер инициализирован")

    def set_timer(self, hours):
        """Устанавливает таймер на указанное количество часов - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            if hours is None:
                self.reset_timer()
                return True

            hours = int(hours)
            if hours <= 0:
                logger.warning("⚠️ Попытка установить таймер с нулевым или отрицательным временем")
                return False

            self.timer_hours = hours
            self.start_time = time.time()
            self.is_timer_active = True

            logger.info(f"⏰ Таймер установлен на {hours} часов")
            logger.info(f"⏰ Время начала: {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f"⏰ Окончание: {(datetime.now() + timedelta(hours=hours)).strftime('%H:%M:%S')}")

            return True

        except (ValueError, TypeError) as e:
            logger.error(f"❌ Ошибка установки таймера: {e}")
            return False

    def reset_timer(self):
        """Сбрасывает таймер - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        self.timer_hours = None
        self.start_time = None
        self.is_timer_active = False
        logger.info("⏰ Таймер сброшен (бесконечный режим)")

    def should_stop(self):
        """Проверяет, истекло ли время таймера - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.is_timer_active or not self.timer_hours or not self.start_time:
            return False

        elapsed_time = time.time() - self.start_time
        total_allowed_time = self.timer_hours * 3600

        if elapsed_time >= total_allowed_time:
            logger.info("⏰ Время таймера истекло! Останавливаем парсер...")
            self.is_timer_active = False
            return True

        return False

    def get_remaining_time(self):
        """Возвращает оставшееся время в читаемом формате - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.is_timer_active or not self.timer_hours or not self.start_time:
            return "Не установлен"

        elapsed_time = time.time() - self.start_time
        remaining_seconds = max(0, (self.timer_hours * 3600) - elapsed_time)

        if remaining_seconds <= 0:
            return "00:00:00"

        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)
        seconds = int(remaining_seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_timer_status(self):
        """Возвращает полный статус таймера для отображения - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.is_timer_active or not self.timer_hours or not self.start_time:
            return {
                'active': False,
                'remaining': 'Не установлен',
                'hours': None,
                'elapsed_seconds': 0,
                'total_seconds': 0,
                'should_stop': False,
                'progress_percent': 0
            }

        elapsed_time = time.time() - self.start_time
        total_seconds = self.timer_hours * 3600
        remaining_seconds = max(0, total_seconds - elapsed_time)

        # Форматируем оставшееся время
        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)
        seconds = int(remaining_seconds % 60)

        remaining_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Процент выполнения
        progress_percent = min(100, int((elapsed_time / total_seconds) * 100)) if total_seconds > 0 else 0

        should_stop = remaining_seconds <= 0

        return {
            'active': True,
            'remaining': remaining_str,
            'hours': self.timer_hours,
            'elapsed_seconds': int(elapsed_time),
            'total_seconds': total_seconds,
            'should_stop': should_stop,
            'progress_percent': progress_percent,
            'start_time': self.start_time,
            'estimated_end': self.start_time + total_seconds
        }

    def get_timer_display(self):
        """Возвращает статус таймера для UI - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        status = self.get_timer_status()

        if not status['active']:
            return "Не установлен"

        if status['should_stop']:
            return "Завершен"

        remaining = status['remaining']
        hours = status['hours']

        return f"{remaining} ({hours}ч)"

    async def wait_with_check(self, seconds, stop_callback):
        """Ожидает указанное время с проверкой остановки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            for i in range(int(seconds)):
                # Проверяем нужно ли остановиться
                if not stop_callback():
                    logger.debug("⏰ Остановка по callback")
                    break

                # Проверяем таймер каждую секунду
                if self.should_stop():
                    logger.info("⏰ Остановка по таймеру")
                    break

                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Ошибка в wait_with_check: {e}")

    def increment_cycle(self):
        """Увеличивает счетчик циклов - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        self.cycle_count += 1

        # Логируем каждый 10-й цикл
        if self.cycle_count % 10 == 0:
            logger.info(f"🔄 Цикл #{self.cycle_count}")

            # Логируем статус таймера каждый 10-й цикл
            if self.is_timer_active:
                status = self.get_timer_status()
                logger.info(f"⏰ Таймер: {status['remaining']} осталось (прогресс: {status['progress_percent']}%)")

        return self.cycle_count

    def should_reload_settings(self, interval=5):
        """Проверяет, нужно ли перезагружать настройки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        should_reload = self.cycle_count % interval == 0

        if should_reload:
            logger.debug(f"🔄 Проверка настроек (цикл #{self.cycle_count})")

        return should_reload

    def get_cycle_info(self):
        """Возвращает информацию о циклах - НОВЫЙ МЕТОД"""
        return {
            'cycle_count': self.cycle_count,
            'check_interval': self.check_interval,
            'timer_active': self.is_timer_active,
            'timer_hours': self.timer_hours
        }

    def get_detailed_status(self):
        """Возвращает детальный статус для отладки - НОВЫЙ МЕТОД"""
        timer_status = self.get_timer_status()

        return {
            'timer': timer_status,
            'cycles': self.get_cycle_info(),
            'uptime': time.time() - (self.start_time or time.time()) if self.start_time else 0,
            'current_time': time.time()
        }

    def pause_timer(self):
        """Приостанавливает таймер - НОВЫЙ МЕТОД"""
        if self.is_timer_active and self.start_time:
            self.is_timer_active = False
            logger.info("⏸️ Таймер приостановлен")
            return True
        return False

    def resume_timer(self):
        """Возобновляет таймер - НОВЫЙ МЕТОД"""
        if not self.is_timer_active and self.timer_hours and self.start_time:
            self.is_timer_active = True
            logger.info("▶️ Таймер возобновлен")
            return True
        return False

    def extend_timer(self, additional_hours):
        """Продлевает таймер на указанное количество часов - НОВЫЙ МЕТОД"""
        try:
            if not self.is_timer_active:
                logger.warning("⚠️ Нельзя продлить неактивный таймер")
                return False

            additional_hours = int(additional_hours)
            if additional_hours <= 0:
                logger.warning("⚠️ Нельзя продлить таймер на отрицательное время")
                return False

            self.timer_hours += additional_hours
            logger.info(f"⏰ Таймер продлен на {additional_hours} часов. Новое время: {self.timer_hours} часов")

            return True

        except (ValueError, TypeError) as e:
            logger.error(f"❌ Ошибка продления таймера: {e}")
            return False


# Создаем глобальный экземпляр для использования в парсере
timer_manager = TimerManager()