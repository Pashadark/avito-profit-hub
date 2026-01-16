# utils/status_manager.py
import json
import os
from datetime import datetime

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")
        print(f"[SAFE_LOG] {message}")
# Статусы по умолчанию
DEFAULT_STATUSES = {
    'website': {'status': 'running', 'details': {'message': 'Сайт работает'}},
    'bot': {'status': 'running', 'details': {'message': 'Бот активен'}},
    'parser': {'status': 'running', 'details': {'message': 'Парсер запущен'}}
}

def get_service_statuses():
    """Всегда возвращает running статусы как в консоли run.py"""
    return DEFAULT_STATUSES

# Функция update_service_status больше не нужна