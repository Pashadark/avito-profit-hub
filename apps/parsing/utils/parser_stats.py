import time
import logging


class ParserStats:
    """Сбор статистики работы парсера"""

    def __init__(self):
        self.products_found = 0
        self.notifications_sent = 0
        self.errors = 0
        self.cycles_completed = 0
        self.start_time = time.time()
        self.last_notification_time = None

    def increment_products_found(self, count=1):
        """Увеличивает счетчик найденных товаров"""
        self.products_found += count

    def increment_notifications_sent(self):
        """Увеличивает счетчик отправленных уведомлений"""
        self.notifications_sent += 1
        self.last_notification_time = time.time()

    def increment_errors(self):
        """Увеличивает счетчик ошибок"""
        self.errors += 1

    def increment_cycles(self):
        """Увеличивает счетчик завершенных циклов"""
        self.cycles_completed += 1

    def get_uptime(self):
        """Время работы парсера в секундах"""
        return time.time() - self.start_time

    def get_uptime_formatted(self):
        """Форматированное время работы"""
        uptime = self.get_uptime()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_stats_message(self):
        """Статистика в виде сообщения для Telegram"""
        if self.products_found > 0:
            efficiency = (self.notifications_sent / self.products_found * 100)
        else:
            efficiency = 0

        return f"""
📊 <b>СТАТИСТИКА ПАРСЕРА</b>

⏰ <b>Время работы:</b> {self.get_uptime_formatted()}
🔄 <b>Циклов завершено:</b> {self.cycles_completed}
🔍 <b>Найдено товаров:</b> {self.products_found}
📨 <b>Уведомлений отправлено:</b> {self.notifications_sent}
❌ <b>Ошибок:</b> {self.errors}
💪 <b>Эффективность:</b> {efficiency:.1f}%

📈 <b>Средняя производительность:</b>
• <b>{self.products_found / self.cycles_completed:.1f}</b> товаров/цикл
• <b>{self.notifications_sent / self.cycles_completed:.1f}</b> уведомлений/цикл
"""

    def get_short_stats(self):
        """Короткая статистика для логов"""
        return (f"Cycles: {self.cycles_completed}, "
                f"Products: {self.products_found}, "
                f"Notifications: {self.notifications_sent}, "
                f"Errors: {self.errors}")

    def reset(self):
        """Сброс статистики"""
        self.products_found = 0
        self.notifications_sent = 0
        self.errors = 0
        self.cycles_completed = 0
        self.start_time = time.time()
        self.last_notification_time = None