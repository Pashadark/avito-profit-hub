import os
import django


def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")


def configure_django():
    """Настраивает Django для использования вне основного процесса"""
    if not django.conf.settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')
        django.setup()


def get_bot_token():
    """Безопасно получает токен бота"""
    try:
        configure_django()
        from django.conf import settings
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if token and token != 'ваш_токен_бота':
            return token
        return None
    except:
        return None


def get_chat_id():
    """Безопасно получает ID чата"""
    try:
        configure_django()
        from django.conf import settings
        return getattr(settings, 'TELEGRAM_CHAT_ID', None)
    except:
        return None


def check_settings():
    """Проверяет настройки и возвращает статус"""
    try:
        configure_django()
        from django.conf import settings
        token = get_bot_token()
        chat_id = get_chat_id()

        return {
            'token_configured': token is not None,
            'chat_id_configured': chat_id is not None,
            'token': token,
            'chat_id': chat_id
        }
    except:
        return {
            'token_configured': False,
            'chat_id_configured': False,
            'token': None,
            'chat_id': None
        }