"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

application = get_asgi_application()