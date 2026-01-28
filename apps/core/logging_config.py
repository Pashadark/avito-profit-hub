import logging
import logging.config
import sys
import os
import time
import atexit
import threading
from colorama import Fore, Style, init

# Инициализация colorama для цветного вывода
init()

# ✅ Глобальные переменные для отслеживания
_logging_initialized = False
_active_handlers = []
_lock = threading.RLock()


# 🔐 Реестр для отслеживания открытых файловых дескрипторов
class FileDescriptorRegistry:
    _instance = None
    _descriptors = {}
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, filename, handler):
        with self._lock:
            self._descriptors[filename] = {
                'handler': handler,
                'last_activity': time.time(),
                'pid': os.getpid()
            }

    def unregister(self, filename):
        with self._lock:
            if filename in self._descriptors:
                del self._descriptors[filename]

    def is_file_open(self, filename):
        with self._lock:
            return filename in self._descriptors

    def close_all(self):
        with self._lock:
            for filename, info in list(self._descriptors.items()):
                try:
                    if hasattr(info['handler'], 'stream') and info['handler'].stream:
                        info['handler'].stream.close()
                        info['handler'].stream = None
                except:
                    pass
            self._descriptors.clear()


# Глобальный реестр
_registry = FileDescriptorRegistry()


# 🛡️ Безопасный обработчик файлов с максимальной защитой
class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Железобетонный обработчик файлов с защитой от блокировки файлов"""

    def __init__(self, *args, **kwargs):
        # Всегда используем delay=True и добавляем таймаут
        kwargs['delay'] = True
        kwargs.setdefault('encoding', 'utf-8')

        # 🔥 ДОБАВЛЕНО: Для Windows добавляем PID к имени файла
        original_filename = kwargs.get('filename') or args[0] if args else None
        if original_filename and os.name == 'nt':
            pid = os.getpid()
            base, ext = os.path.splitext(original_filename)
            kwargs['filename'] = f"{base}.{pid}{ext}"

        super().__init__(*args, **kwargs)

        self._last_rollover_check = time.time()
        self._rollover_check_interval = 60
        self._max_retries = 5
        self._retry_delay = 0.5
        self._rotate_on_startup = False
        self._file_lock = threading.RLock()

        # Регистрируем обработчик при создании
        with _lock:
            _active_handlers.append(self)

    def _open(self):
        """Открытие файла с защитой от блокировок."""
        with self._file_lock:
            # Если файл уже открыт - возвращаем его
            if self.stream is not None and not self.stream.closed:
                return self.stream

            # Пробуем несколько раз открыть файл
            for attempt in range(self._max_retries):
                try:
                    # Проверяем, не открыт ли файл другим процессом/потоком
                    if _registry.is_file_open(self.baseFilename):
                        if attempt < self._max_retries - 1:
                            time.sleep(self._retry_delay)
                            continue
                        else:
                            # 🔥 ИСПРАВЛЕНО: Файл заблокирован после всех попыток
                            # Создаем временный файл для этого процесса
                            temp_filename = f"{self.baseFilename}.tmp.{os.getpid()}"
                            error_msg = f"File {self.baseFilename} is locked, using {temp_filename}"
                            sys.stderr.write(f"WARNING: {error_msg}\n")

                            # Создаем директорию если не существует
                            os.makedirs(os.path.dirname(temp_filename) or '.', exist_ok=True)
                            return open(temp_filename, mode=self.mode, encoding=self.encoding)

                    # Файл не заблокирован, открываем нормально
                    stream = super()._open()
                    _registry.register(self.baseFilename, self)
                    return stream

                except (OSError, IOError, PermissionError) as e:
                    if attempt == self._max_retries - 1:
                        error_msg = f"Cannot open log file {self.baseFilename}: {e}"
                        sys.stderr.write(f"ERROR: {error_msg}\n")
                        raise
                    time.sleep(self._retry_delay)

            # 🔥 ИСПРАВЛЕНО: Всегда возвращаем или выбрасываем исключение
            raise IOError(f"Failed to open log file after {self._max_retries} attempts")

    def _close_file(self):
        """Безопасное закрытие файла"""
        with self._file_lock:
            if self.stream and not self.stream.closed:
                try:
                    self.stream.flush()
                    self.stream.close()
                    _registry.unregister(self.baseFilename)
                except:
                    pass
                finally:
                    self.stream = None

    def _safe_do_rollover(self):
        """Абсолютно безопасная ротация файлов"""
        with self._file_lock:
            original_name = self.baseFilename

            # 1. Сначала создаём новый файл с временным именем
            temp_name = f"{original_name}.{int(time.time())}.tmp"
            new_name = f"{original_name}.1"

            try:
                # 2. Копируем содержимое в новый файл (если существует)
                if os.path.exists(original_name):
                    for attempt in range(self._max_retries):
                        try:
                            with open(original_name, 'rb') as f_in:
                                with open(temp_name, 'wb') as f_out:
                                    f_out.write(f_in.read())
                            break
                        except PermissionError:
                            if attempt == self._max_retries - 1:
                                sys.stderr.write(f"⚠️ Не удалось прочитать файл для ротации: {original_name}\n")
                                return False
                            time.sleep(self._retry_delay)

                # 3. Закрываем текущий файл
                self._close_file()

                # 4. Переименовываем временный файл в ротированный
                if os.path.exists(temp_name):
                    for attempt in range(self._max_retries):
                        try:
                            if os.path.exists(new_name):
                                os.remove(new_name)
                            os.rename(temp_name, new_name)
                            break
                        except PermissionError:
                            if attempt == self._max_retries - 1:
                                sys.stderr.write(f"⚠️ Не удалось переименовать файл: {temp_name} -> {new_name}\n")
                                # Удаляем временный файл
                                try:
                                    os.remove(temp_name)
                                except:
                                    pass
                                return False
                            time.sleep(self._retry_delay)

                # 5. Очищаем текущий файл (создаём пустой)
                for attempt in range(self._max_retries):
                    try:
                        with open(original_name, 'w', encoding='utf-8') as f:
                            f.write('')
                        break
                    except PermissionError:
                        if attempt == self._max_retries - 1:
                            sys.stderr.write(f"⚠️ Не удалось очистить основной файл логов: {original_name}\n")
                            return False
                        time.sleep(self._retry_delay)

                # 6. Открываем файл заново
                self.stream = self._open()
                return True

            except Exception as e:
                sys.stderr.write(f"❌ Критическая ошибка при ротации: {e}\n")

                # Восстанавливаем работу любой ценой
                try:
                    self._close_file()
                    self.stream = self._open()
                except:
                    pass
                return False

    def emit(self, record):
        """Абсолютно безопасная запись лога"""
        try:
            # Проверяем ротацию (но не чаще чем раз в interval)
            current_time = time.time()
            if current_time - self._last_rollover_check > self._rollover_check_interval:
                if self.shouldRollover(record):
                    self._safe_do_rollover()
                self._last_rollover_check = current_time

            # Записываем лог
            with self._file_lock:
                if self.stream is None:
                    self.stream = self._open()
                super().emit(record)

        except Exception as e:
            # Критическая ошибка - пишем в stderr
            sys.stderr.write(f"🔥 КРИТИЧЕСКАЯ ОШИБКА ЛОГИРОВАНИЯ: {e}\n")
            sys.stderr.write(f"📝 Сообщение: {record.getMessage() if hasattr(record, 'getMessage') else str(record)}\n")

            # Пытаемся восстановить
            try:
                self._close_file()
                time.sleep(0.1)
                self.stream = self._open()

                # Пробуем записать снова
                with self._file_lock:
                    super().emit(record)
            except:
                # Финальный fallback
                sys.stderr.write(f"📝 [FALLBACK] {record.getMessage()}\n")

    def close(self):
        """Безопасное закрытие обработчика"""
        with self._file_lock:
            self._close_file()
            # Удаляем из списка активных обработчиков
            with _lock:
                if self in _active_handlers:
                    _active_handlers.remove(self)
            super().close()


class CustomFormatter(logging.Formatter):
    """Кастомный форматтер с цветами для разных компонентов системы"""

    LEVEL_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    COMPONENT_COLORS = {
        'parser': Fore.MAGENTA,
        'bot': Fore.BLUE,
        'django': Fore.CYAN,
        'apps.core': Fore.GREEN,
        'utils': Fore.YELLOW,
        'website': Fore.WHITE,
        'management': Fore.LIGHTBLUE_EX,
        'user': Fore.LIGHTGREEN_EX,
        'apps': Fore.LIGHTCYAN_EX,
        'core': Fore.LIGHTGREEN_EX,
        'system': Fore.LIGHTYELLOW_EX,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._formatting = False

    def format(self, record):
        if self._formatting:
            return f"{record.levelname}: {record.getMessage()}"

        self._formatting = True
        try:
            level_color = self.LEVEL_COLORS.get(record.levelname, Fore.WHITE)
            component = record.name.split('.')[0] if '.' in record.name else record.name
            component_color = self.COMPONENT_COLORS.get(component, Fore.WHITE)

            record.levelcolor = level_color
            record.componentcolor = component_color
            record.reset = Style.RESET_ALL

            return super().format(record)
        except Exception:
            return f"{record.levelname}: {record.getMessage()}"
        finally:
            self._formatting = False


class DjangoServerLogFilter(logging.Filter):
    """Фильтр для парсинга и преобразования логов Django development server"""

    def __init__(self):
        super().__init__()
        self._filtering = False

    def filter(self, record):
        if self._filtering:
            return True

        self._filtering = True
        try:
            if record.name == 'django.server' and hasattr(record, 'msg'):
                original_message = record.msg
                if isinstance(original_message, str) and (
                        'HTTP' in original_message or '"GET' in original_message or '"POST' in original_message):
                    try:
                        message_clean = original_message
                        if '] "' in original_message:
                            message_clean = original_message.split('] "', 1)[1]
                            message_clean = '"' + message_clean

                        parts = message_clean.split('"')
                        if len(parts) >= 3:
                            request_part = parts[1]
                            status_part = parts[2].strip()
                            status_parts = status_part.split()
                            status_code = status_parts[0] if status_parts else '???'
                            response_size = status_parts[1] if len(status_parts) > 1 else '0'

                            status_int = int(status_code) if status_code.isdigit() else 200
                            if 500 <= status_int <= 599:
                                record.levelno = logging.ERROR
                                record.levelname = 'ERROR'
                                status_emoji = '❌'
                            elif 400 <= status_int <= 499:
                                record.levelno = logging.WARNING
                                record.levelname = 'WARNING'
                                status_emoji = '⚠️'
                            elif 300 <= status_int <= 399:
                                record.levelno = logging.INFO
                                record.levelname = 'INFO'
                                status_emoji = '📄'
                            else:
                                record.levelno = logging.INFO
                                record.levelname = 'INFO'
                                status_emoji = '✅'

                            method = request_part.split()[0] if ' ' in request_part else '???'
                            path = request_part.split()[1] if len(request_part.split()) > 1 else '???'

                            if '?' in path:
                                base_path, params = path.split('?', 1)
                                if len(base_path) > 30:
                                    path = base_path[:27] + '...?' + params
                                else:
                                    path = base_path + '?...'
                            elif len(path) > 50:
                                path = path[:47] + '...'

                            try:
                                size_int = int(response_size)
                                if size_int > 1024 * 1024:
                                    size_str = f"{size_int / (1024 * 1024):.1f}MB"
                                elif size_int > 1024:
                                    size_str = f"{size_int / 1024:.1f}KB"
                                else:
                                    size_str = f"{size_int}B"
                            except:
                                size_str = f"{response_size}B"

                            record.msg = f"{status_emoji} {method} {path} → {status_code} ({size_str})"

                    except Exception:
                        record.msg = f"🌐 {original_message}"

            return True
        finally:
            self._filtering = False


def _cleanup_logging():
    """Функция очистки при выходе"""
    print(f"{Fore.YELLOW}🛑 Завершение системы логирования...{Style.RESET_ALL}")

    # Закрываем все обработчики
    with _lock:
        for handler in _active_handlers[:]:
            try:
                handler.close()
            except:
                pass
        _active_handlers.clear()

    # Очищаем реестр
    _registry.close_all()

    print(f"{Fore.GREEN}✅ Система логирования завершена{Style.RESET_ALL}")


def setup_logging(process_name=None):
    """Настройка единой системы логирования для всего проекта"""
    global _logging_initialized

    if process_name:
        init_key = f"process_{process_name}_{os.getpid()}"
    else:
        if _logging_initialized:
            return
        _logging_initialized = True
        init_key = "global"

    # Регистрируем cleanup при выходе
    atexit.register(_cleanup_logging)

    # Создаем папки для логов
    log_dirs = ['logs', 'logs/system', 'logs/bot', 'logs/django',
                'logs/parsing', 'logs/website', 'logs/apps', 'logs/postgresql']

    for log_dir in log_dirs:
        os.makedirs(log_dir, exist_ok=True)

    if process_name:
        process_log_dir = f'logs/process_{process_name}'
        os.makedirs(process_log_dir, exist_ok=True)

    pid = os.getpid()
    detailed_format = f'%(asctime)s | PID:{pid} | %(levelname)-8s | %(name)-25s | %(message)s'

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'django_server_filter': {
                '()': DjangoServerLogFilter,
            },
        },
        'formatters': {
            'colored': {
                '()': CustomFormatter,
                'format': '%(asctime)s | %(levelcolor)s%(levelname)-8s%(reset)s | %(componentcolor)s%(name)-25s%(reset)s | %(message)s',
                'datefmt': '%H:%M:%S'
            },
            'detailed': {
                'format': detailed_format,
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'django_server': {
                '()': CustomFormatter,
                'format': '%(asctime)s | %(levelcolor)s%(levelname)-8s%(reset)s | %(componentcolor)s%(name)-25s%(reset)s | %(message)s',
                'datefmt': '%H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s: %(message)s'
            },
        },

        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'formatter': 'colored',
                'level': 'INFO'
            },
            'django_console': {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'formatter': 'django_server',
                'level': 'INFO',
                'filters': ['django_server_filter']
            },

            'postgresql_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/postgresql/postgresql.log',
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
                'formatter': 'detailed',
                'level': 'DEBUG',
            },
            'system_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/system/system.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
            },
            'bot_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/bot/bot.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
            },
            'django_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/django/django.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
            },
            'parsing_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/parsing/parsing.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
            },
            'website_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/website/website.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
            },
            'apps_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/apps/general.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
            },
            'error_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/apps/errors.log',
                'maxBytes': 5 * 1024 * 1024,
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'WARNING',
            },
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'loggers': {
            # 🌐 Django
            'django.server': {
                'handlers': ['django_console', 'django_file'],
                'level': 'INFO',
                'propagate': False,
                'filters': ['django_server_filter']
            },
            'django': {
                'handlers': ['console', 'django_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'django.db.backends': {
                'handlers': ['console', 'apps_file', 'postgresql_file'],
                'level': 'DEBUG',
                'propagate': False
            },

            # 🤖 Парсер
            'parser': {
                'handlers': ['console', 'parsing_file'],
                'level': 'INFO',
                'propagate': False
            },
            'parser.selenium': {
                'handlers': ['console', 'parsing_file'],
                'level': 'INFO',
                'propagate': False
            },
            'parser.ai': {
                'handlers': ['console', 'parsing_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 📱 Бот
            'bot': {
                'handlers': ['console', 'bot_file'],
                'level': 'INFO',
                'propagate': False
            },
            'bot.telegram': {
                'handlers': ['console', 'bot_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 🏢 Система
            'system.run': {
                'handlers': ['console', 'system_file'],
                'level': 'INFO',
                'propagate': False
            },
            'settings.system': {
                'handlers': ['console', 'system_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 📊 Сайт
            'website': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },

            # ⚙️ Core
            'apps.core': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 🔧 Utils
            'utils': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO',
                'propagate': False
            },

            # ⚡ HTTP библиотеки
            'httpx': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'urllib3': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'selenium': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },

            # 🎯 Корневой логгер
            '': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO'
            }
        }
    }

    if process_name:
        LOGGING_CONFIG['handlers'][f'{process_name}_file'] = {
            '()': SafeRotatingFileHandler,
            'filename': f'logs/process_{process_name}/{process_name}.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'detailed',
            'level': 'INFO',
        }

        for logger_name in LOGGING_CONFIG['loggers']:
            if logger_name:
                if 'handlers' in LOGGING_CONFIG['loggers'][logger_name]:
                    LOGGING_CONFIG['loggers'][logger_name]['handlers'].append(f'{process_name}_file')

    # Применяем конфигурацию
    logging.config.dictConfig(LOGGING_CONFIG)

    # Тестовое сообщение
    logger = logging.getLogger('system.run')
    logger.info(f"🎨 Система логирования инициализирована (процесс: {process_name or 'global'}, PID: {pid})")


# Вспомогательные функции
def print_success(text):
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")


def print_error(text):
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")


def print_warning(text):
    print(f"{Fore.YELLOW}⚠️ {text}{Style.RESET_ALL}")


def print_info(text):
    print(f"{Fore.BLUE}ℹ️ {text}{Style.RESET_ALL}")


def print_banner(text):
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")


def print_step(text):
    print(f"{Fore.MAGENTA}🚀 {text}{Style.RESET_ALL}")


def print_divider():
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")


# Утилиты
def get_logger(name):
    return logging.getLogger(name)


def set_log_level(level_name):
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.getLogger().setLevel(level)
    for logger_name in logging.root.manager.loggerDict:
        logging.getLogger(logger_name).setLevel(level)


def get_run_logger():
    return logging.getLogger('system.run')


def get_parser_logger():
    return logging.getLogger('parser.selenium')


def get_bot_logger():
    return logging.getLogger('bot.telegram')


# 🛠️ Дополнительная утилита для принудительной очистки логов
def force_clean_logs():
    """Принудительная очистка всех логов перед запуском"""
    import glob

    print_warning("🧹 Принудительная очистка логов...")

    # Ищем все .log файлы
    log_files = glob.glob('logs/**/*.log', recursive=True)
    log_files += glob.glob('logs/**/*.log.*', recursive=True)

    for log_file in log_files:
        try:
            # Пробуем удалить
            for attempt in range(3):
                try:
                    os.remove(log_file)
                    print_info(f"Удалён: {log_file}")
                    break
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.5)
                        continue
                    print_warning(f"Не удалось удалить: {log_file}")
        except Exception as e:
            print_error(f"Ошибка удаления {log_file}: {e}")

    print_success("Очистка логов завершена")


def test_logging_system():
    """Тестирование системы логирования"""
    print_divider()
    print_banner("🎯 ТЕСТИРОВАНИЕ СИСТЕМЫ ЛОГИРОВАНИЯ")
    print_divider()

    test_cases = [
        ('parser.selenium', "🚀 Тест парсера - INFO"),
        ('parser.selenium', "⚠️ Тест парсера - WARNING", logging.WARNING),
        ('bot.telegram', "🤖 Тест бота - INFO"),
        ('system.run', "🏢 Тест системы - INFO"),
        ('settings.system', "🔧 Тест настроек системы - INFO"),
    ]

    for logger_name, message, *level in test_cases:
        logger = get_logger(logger_name)
        if level:
            log_method = getattr(logger, logging.getLevelName(level[0]).lower())
            log_method(message)
        else:
            logger.info(message)

    print_divider()
    print_success("Тестирование завершено!")
    print_divider()


if __name__ == "__main__":
    # Тестирование системы логирования
    setup_logging()
    test_logging_system()