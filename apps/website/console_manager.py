import threading
from django.utils import timezone
import logging

# Глобальное хранилище консольных сообщений
console_history = []
console_lock = threading.Lock()
logger = logging.getLogger(__name__)


def add_to_console(message, log_to_console=True):
    """Добавляет сообщение в консоль с правильным форматированием"""
    global console_history

    try:
        with console_lock:
            timestamp = timezone.now().strftime("[%H:%M:%S]")

            # Если сообщение уже содержит временную метку, используем как есть
            if isinstance(message, str) and message.startswith('[') and ']' in message:
                formatted_message = message
            else:
                # Обрабатываем многострочные сообщения
                message_str = str(message)
                lines = message_str.split('\n')

                for line in lines:
                    if line.strip():
                        cleaned_line = ' '.join(line.split())
                        if cleaned_line:
                            formatted_message = f"{timestamp} {cleaned_line}"

                            # Проверяем на дубликаты перед добавлением
                            if not any(formatted_message == existing_msg for existing_msg in console_history[-20:]):
                                console_history.append(formatted_message)

                                # Логируем в консоль если нужно
                                if log_to_console:
                                    print(formatted_message)

            # Ограничиваем размер истории
            if len(console_history) > 1000:
                console_history = console_history[-500:]

    except Exception as e:
        print(f"Ошибка добавления в консоль: {e}")
        logger.error(f"Ошибка добавления в консоль: {e}")


def get_console_output(limit=50):
    """Возвращает последние сообщения из консоли"""
    global console_history

    with console_lock:
        return console_history[-limit:] if console_history else ["[00:00:00] Консоль пуста"]


def clear_console():
    """Очищает консоль"""
    global console_history

    with console_lock:
        console_history.clear()
        add_to_console("🧹 Консоль очищена")


def format_multiline_message(*messages):
    """Форматирует многострочное сообщение для красивого вывода"""
    timestamp = timezone.now().strftime("[%H:%M:%S]")
    formatted_lines = []

    for i, message in enumerate(messages):
        if i == 0:
            formatted_lines.append(f"{timestamp} {message}")
        else:
            formatted_lines.append(f"{' ' * len(timestamp)} {message}")

    return "\n".join(formatted_lines)