import os
import django
from django.conf import settings

def configure_django():
    """Настраивает Django для использования вне основного процесса"""
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')
        django.setup()

def get_bot_token():
    """Безопасно получает токен бота"""
    configure_django()
    return getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

def get_chat_id():
    """Безопасно получает ID чата"""
    configure_django()
    return getattr(settings, 'TELEGRAM_CHAT_ID', None)