#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")


def main():
    """Run administrative tasks."""
    # ✅ КРИТИЧЕСКИ ВАЖНО: Добавляем apps в sys.path ПЕРЕД импортом Django
    project_root = os.path.dirname(os.path.abspath(__file__))
    apps_path = os.path.join(project_root, 'apps')
    if apps_path not in sys.path:
        sys.path.insert(0, apps_path)

    # ✅ Инициализация системы логирования
    try:
        from apps.core.logging_config import setup_logging
        setup_logging()
    except Exception as e:
        print(f"❌ Ошибка инициализации логирования: {e}")

    # ✅ Устанавливаем settings модуль (теперь core вместо apps.core)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
