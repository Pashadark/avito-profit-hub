from django.test import TestCase

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from dashboard.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")
        print(f"[SAFE_LOG] {message}")
# Create your tests here.
