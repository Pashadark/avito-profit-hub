from django.contrib import admin

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from apps.website.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")
        print(f"[SAFE_LOG] {message}")
# Register your models here.
