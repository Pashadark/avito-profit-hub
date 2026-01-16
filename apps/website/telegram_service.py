# dashboard/telegram_service.py
import requests
import logging
from django.conf import settings

logger = logging.getLogger('dashboard.telegram')


class TelegramService:
    """Сервис для отправки сообщений в Telegram"""

    @staticmethod
    def send_message(message, chat_id=None, token=None):
        """Отправка сообщения в Telegram"""
        try:
            # Получаем настройки из конфигурации
            if not token:
                token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

            if not chat_id:
                chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)

            if not token or token == 'ваш_токен_бота':
                logger.error("❌ TELEGRAM_BOT_TOKEN не настроен")
                return False

            if not chat_id:
                logger.error("❌ TELEGRAM_CHAT_ID не настроен")
                return False

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("✅ Сообщение отправлено в Telegram")
                return True
            else:
                logger.error(f"❌ Ошибка Telegram API: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False

    @staticmethod
    def send_registration_confirmation(phone_number, confirmation_code, user_data=None):
        """Отправка кода подтверждения регистрации"""
        try:
            message = f"""
🔐 <b>НОВАЯ РЕГИСТРАЦИЯ</b>

📱 <b>Телефон:</b> {phone_number}
🔢 <b>Код подтверждения:</b> <code>{confirmation_code}</code>

👤 <b>Данные пользователя:</b>
• Имя: {user_data.get('first_name', 'Не указано')}
• Фамилия: {user_data.get('last_name', 'Не указано')} 
• Email: {user_data.get('email', 'Не указан')}
• Username: {user_data.get('username', 'Не указан')}

⏰ <b>Код действителен 10 минут</b>

💡 <i>Пользователь должен ввести этот код на сайте для завершения регистрации</i>
            """

            return TelegramService.send_message(message)

        except Exception as e:
            logger.error(f"❌ Ошибка отправки кода подтверждения: {e}")
            return False


# Создаем глобальный экземпляр
telegram_service = TelegramService()