# apps/website/console_capture.py
import sys
import threading
from io import StringIO
import logging
import re
import hashlib

logger = logging.getLogger('console.capture')


class ConsoleOutputCapturer:
    """Перехватывает вывод в консоль и красиво форматирует Django HTTP логи"""

    # 🔥 ЗАЩИТА ОТ РЕКУРСИИ
    _recursion_guard = False
    _message_counter = 0
    _last_messages = []

    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.captured_output = StringIO()
        self.is_capturing = False
        self.lock = threading.Lock()

        # Хеш для предотвращения дублирования
        self._processed_hashes = set()

        # 🔥 Паттерны которые ИГНОРИРУЕМ (чтобы избежать рекурсии)
        self._ignore_patterns = [
            'Logging error',
            'PermissionError',
            'doRollover',
            'emit',
            '_log',
            'handleError',
            'findCaller',
            '_is_internal_frame',
            'logging/',
            'handlers.py',
            'RecursionError',
            'maximum recursion depth exceeded',
            'console_capture.py',
            'logging.__init__',
            'logging.handlers',
            '--- Logging error ---',
        ]

        # 🔥 Паттерны которые ПРОСТО ВЫВОДИМ (не логируем)
        self._pass_through_patterns = [
            'Performing system checks...',
            'System check identified no issues',
            'Django version',
            'Starting development server at',
            'Quit the server with',
            'WARNING: This is a development server',
            'For more information on production servers',
            'Using settings',
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
        ]

        # 🔥 НОВОЕ: Паттерны которые ПОЛНОСТЬЮ ИГНОРИРУЕМ (ML/logging технические)
        self._ml_ignore_patterns = [
            'Parallel(n_jobs=',
            'Using backend',
            'Done',
            'elapsed:',
            '[Parallel(',
            '] Using backend',
            '] Done',
            ' out of ',
            ' tasks',
            'finished',
            'ThreadingBackend',
        ]

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
            # Создаем хеш для проверки дублирования
            log_hash = hashlib.md5(text.strip().encode()).hexdigest()
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

    def _should_ignore(self, text):
        """Проверяет, нужно ли игнорировать сообщение"""
        text_lower = text.lower()

        # 🔥 Проверка на ошибки логирования (РЕКУРСИЯ!)
        for pattern in self._ignore_patterns:
            if pattern.lower() in text_lower:
                return True

        # 🔥 Проверка на слишком частые сообщения (возможная рекурсия)
        self._message_counter += 1
        self._last_messages.append(text[:100])
        if len(self._last_messages) > 10:
            self._last_messages.pop(0)

        # Если последние 5 сообщений одинаковые - вероятно рекурсия
        if len(self._last_messages) >= 5 and len(set(self._last_messages[-5:])) == 1:
            return True

        return False

    def write(self, text):
        """Перехватывает вывод и логирует его"""
        # 🔥 ЗАЩИТА ОТ РЕКУРСИИ - если уже в режиме защиты, просто выводим
        if self._recursion_guard:
            self.original_stdout.write(text)
            return

        if not text.strip():  # Игнорируем пустые строки
            self.original_stdout.write(text)
            return

        text_str = text.rstrip('\n')

        # 🔥 НОВОЕ: Полностью игнорируем ML (joblib) логи
        if any(pattern in text_str for pattern in self._ml_ignore_patterns):
            # Просто выводим в консоль и ВОЗВРАЩАЕМСЯ - НЕ логируем!
            self.original_stdout.write(text)
            return

        # 🔥 ПРОВЕРКА: Игнорируем сообщения об ошибках логирования
        if self._should_ignore(text_str):
            self.original_stdout.write(text)
            return

        # 🔥 ПРОВЕРКА 1: Django HTTP лог [date] "GET /path HTTP/1.1" status size
        if text_str.startswith('[') and 'HTTP/1.1"' in text_str:
            formatted_log = self._format_django_log(text_str)

            if formatted_log:
                # 🔥 БЕЗОПАСНОЕ логирование с защитой от рекурсии
                try:
                    self._recursion_guard = True
                    logger.info(formatted_log)
                except Exception:
                    pass  # Молча игнорируем ошибки логирования
                finally:
                    self._recursion_guard = False
                return
            else:
                self.original_stdout.write(text)
                return

        # 🔥 ПРОВЕРКА 2: Другие Django системные сообщения (просто выводим)
        if any(msg in text_str for msg in self._pass_through_patterns):
            self.original_stdout.write(text)
            return

        # 🔥 ПРОВЕРКА 3: WSGI и инициализация Django
        if 'WSGI приложение Django инициализировано' in text_str:
            try:
                self._recursion_guard = True
                logger.info(text_str)
            except Exception:
                pass
            finally:
                self._recursion_guard = False
            self.captured_output.write(text_str + '\n')
            return

        # 🔥 ПРОВЕРКА 4: Игнорируем наши собственные логи
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
            return

        # 🔥 ОБРАБОТКА: Все остальные сообщения
        cleaned_text = text_str.strip()

        if cleaned_text:
            # Определяем уровень логирования по содержанию
            try:
                self._recursion_guard = True

                if any(word in cleaned_text.lower() for word in ['error', 'exception', 'failed', '❌']):
                    logger.error(cleaned_text[:200])  # Ограничиваем длину
                elif any(word in cleaned_text.lower() for word in ['warning', '⚠️', 'attention']):
                    logger.warning(cleaned_text[:200])
                elif any(word in cleaned_text.lower() for word in ['debug', '🔍']):
                    logger.debug(cleaned_text[:200])
                else:
                    # Обычные сообщения логируем как INFO, но ограничиваем
                    if len(cleaned_text) < 100:  # Только короткие сообщения
                        logger.info(cleaned_text)

            except Exception as e:
                # 🔥 КРИТИЧЕСКОЕ: если ошибка при логировании, выводим напрямую
                self.original_stdout.write(f"[CAPTURE ERROR] {e}\n")
            finally:
                self._recursion_guard = False

            self.captured_output.write(cleaned_text[:100] + '\n')

        # Выводим в оригинальный stdout
        self.original_stdout.write(text)

    def flush(self):
        """Flush буфера"""
        self.original_stdout.flush()

    def get_captured_output(self):
        """Возвращает перехваченный вывод для веб-интерфейсра"""
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
            # 🔥 Безопасное логирование
            try:
                self._recursion_guard = True
                logger.info("🧹 Буфер консоли очищен")
            except Exception:
                pass
            finally:
                self._recursion_guard = False


# Глобальный экземпляр
console_capturer = ConsoleOutputCapturer()