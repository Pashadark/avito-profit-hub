# apps/website/console_capture.py
import sys
import threading
from io import StringIO
import logging
import re

logger = logging.getLogger('console.capture')


class ConsoleOutputCapturer:
    """Перехватывает вывод в консоль и красиво форматирует Django HTTP логи"""

    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.captured_output = StringIO()
        self.is_capturing = False
        self.lock = threading.Lock()

        # Хеш для предотвращения дублирования
        self._processed_hashes = set()

    def start_capture(self):
        """Начинает перехват вывода"""
        with self.lock:
            if not self.is_capturing:
                sys.stdout = self
                sys.stderr = self
                self.is_capturing = True
                self._processed_hashes.clear()
                logger.info("🔄 Начат перехват консольного вывода...")

    def stop_capture(self):
        """Останавливает перехват вывода"""
        with self.lock:
            if self.is_capturing:
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
                self.is_capturing = False
                logger.info("⏹️ Остановлен перехват консольного вывода")

    def _format_django_log(self, text):
        """Форматирует Django лог [date] "GET /path" в наш формат"""
        try:
            # Пример: [15/Jan/2026 16:42:17] "GET /debug-settings/ HTTP/1.1" 200 161773

            # Создаем хеш для проверки дублирования
            log_hash = hash(text.strip())
            if log_hash in self._processed_hashes:
                return None  # Уже обработали
            self._processed_hashes.add(log_hash)

            # Извлекаем метод и путь
            method_match = re.search(r'"(\w+)\s+([^"]+?)\s+HTTP', text)
            if not method_match:
                return None

            method = method_match.group(1)  # GET, POST и т.д.
            path = method_match.group(2)

            # Извлекаем статус код
            status_match = re.search(r'"\s+(\d{3})\s+', text)
            status = status_match.group(1) if status_match else "???"

            # Определяем эмодзи по статусу
            if status.startswith('2'):
                status_emoji = '✅'
            elif status.startswith('3'):
                status_emoji = '🔄'
            elif status.startswith('4'):
                status_emoji = '⚠️'
            elif status.startswith('5'):
                status_emoji = '❌'
            else:
                status_emoji = '🌐'

            # Обрезаем длинные пути
            if len(path) > 50:
                display_path = path[:47] + '...'
            else:
                display_path = path

            return f"{status_emoji} {method} {display_path} → {status}"

        except Exception:
            return None

    def write(self, text):
        """Перехватывает вывод и логирует его"""
        if not text.strip():  # Игнорируем пустые строки
            self.original_stdout.write(text)
            return

        text_str = text.rstrip('\n')

        # 🔥 ПРОВЕРКА 1: Django HTTP лог [date] "GET /path HTTP/1.1" status size
        if text_str.startswith('[') and 'HTTP/1.1"' in text_str:
            formatted_log = self._format_django_log(text_str)

            if formatted_log:
                # Логируем в нашем формате
                logger.info(formatted_log)
                # НЕ выводим оригинальный Django лог
                return
            else:
                # Если не смогли отформатировать, выводим как есть
                self.original_stdout.write(text)
                return

        # 🔥 ПРОВЕРКА 2: Другие Django системные сообщения (просто выводим)
        django_system_messages = [
            'Performing system checks...',
            'System check identified no issues',
            'Django version',
            'Starting development server at',
            'Quit the server with',
            'WARNING: This is a development server',
            'For more information on production servers',
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
            'Using settings',
        ]

        if any(msg in text_str for msg in django_system_messages):
            # Просто выводим, не логируем
            self.original_stdout.write(text)
            return

        # 🔥 ПРОВЕРКА 3: WSGI и инициализация Django
        if 'WSGI приложение Django инициализировано' in text_str:
            logger.info(text_str)
            self.captured_output.write(text_str + '\n')
            # Не выводим оригинал
            return

        # 🔥 ПРОВЕРКА 4: Traceback и ошибки
        if 'Traceback' in text_str or 'Error:' in text_str or 'Exception:' in text_str:
            logger.error(text_str)
            self.captured_output.write(text_str + '\n')
            self.original_stdout.write(text)
            return

        # 🔥 ПРОВЕРКА 5: Bad Request, Not Found
        if 'Bad Request:' in text_str or 'Not Found:' in text_str:
            logger.warning(text_str)
            self.captured_output.write(text_str + '\n')
            self.original_stdout.write(text)
            return

        # 🔥 ПРОВЕРКА 6: Игнорируем наши собственные логи
        our_logs_patterns = [
            ' | INFO     |',
            ' | ERROR    |',
            ' | WARNING  |',
            ' | DEBUG    |',
            ' | CRITICAL |',
            '⏱️ GET ',
            '⏱️ POST ',
            '⏱️ PUT ',
            '⏱️ DELETE ',
            '✅ 🌐 ПРОСМОТР |',
            '✅ 📡 API ВЫЗОВ |',
            '✅ 👤 ПРОФИЛЬ |',
            '🎯 Middleware called for:',
            '🎯 Added',
            '🎯 Cleared',
        ]

        if any(pattern in text_str for pattern in our_logs_patterns):
            # Это наши логи - просто пропускаем
            return

        # 🔥 ОБРАБОТКА: Все остальные сообщения
        cleaned_text = text_str.strip()

        if cleaned_text:
            # Определяем уровень логирования по содержанию
            if any(word in cleaned_text.lower() for word in ['error', 'exception', 'failed', '❌']):
                logger.error(cleaned_text)
            elif any(word in cleaned_text.lower() for word in ['warning', '⚠️', 'attention']):
                logger.warning(cleaned_text)
            elif any(word in cleaned_text.lower() for word in ['debug', '🔍']):
                logger.debug(cleaned_text)
            else:
                logger.info(cleaned_text)

            self.captured_output.write(cleaned_text + '\n')

        # Выводим в оригинальный stdout
        self.original_stdout.write(text)

    def flush(self):
        """Flush буфера"""
        self.original_stdout.flush()

    def get_captured_output(self):
        """Возвращает перехваченный вывод для веб-интерфейса"""
        with self.lock:
            output = self.captured_output.getvalue()
            self.captured_output.seek(0)
            self.captured_output.truncate(0)
            return output.split('\n') if output else []

    def clear(self):
        """Очищает буфер"""
        with self.lock:
            self.captured_output.seek(0)
            self.captured_output.truncate(0)
            logger.info("🧹 Буфер консоли очищен")


# Глобальный экземпляр
console_capturer = ConsoleOutputCapturer()