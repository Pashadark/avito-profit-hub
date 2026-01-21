import logging
import logging.config
import sys
import os
import time
from colorama import Fore, Style, init

# Инициализация colorama для цветного вывода
init()

# ✅ Глобальная переменная для отслеживания инициализации
_logging_initialized = False


class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Безопасный обработчик файлов с защитой от блокировки файлов"""

    def __init__(self, *args, **kwargs):
        # Всегда используем delay=True чтобы избежать блокировки файлов
        kwargs['delay'] = True
        super().__init__(*args, **kwargs)

    def doRollover(self):
        """Безопасная ротация файлов с обработкой ошибок"""
        try:
            super().doRollover()
        except (OSError, IOError) as e:
            # Если не удалось сделать ротацию, пишем в текущий файл
            print(f"⚠️ Не удалось сделать ротацию логов: {e}", file=sys.stderr)


class CustomFormatter(logging.Formatter):
    """Кастомный форматтер с цветами для разных компонентов системы"""

    # Цвета для разных типов сообщений
    LEVEL_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    # Цвета для разных компонентов системы
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
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._formatting = False  # 🔥 ЗАЩИТА ОТ РЕКУРСИИ

    def format(self, record):
        # 🔥 ЗАЩИТА ОТ РЕКУРСИИ - если уже в процессе форматирования, возвращаем простой формат
        if self._formatting:
            return f"{record.levelname}: {record.getMessage()}"

        self._formatting = True
        try:
            # Добавляем цвет в зависимости от уровня
            level_color = self.LEVEL_COLORS.get(record.levelname, Fore.WHITE)

            # Добавляем цвет для компонента (первая часть имени логгера)
            component = record.name.split('.')[0] if '.' in record.name else record.name
            component_color = self.COMPONENT_COLORS.get(component, Fore.WHITE)

            # Создаем форматированное сообщение
            record.levelcolor = level_color
            record.componentcolor = component_color
            record.reset = Style.RESET_ALL

            return super().format(record)
        except Exception as e:
            # 🔥 ВАЖНО: при ошибке НЕ логируем, а возвращаем простой формат
            return f"{record.levelname}: {record.getMessage()}"
        finally:
            self._formatting = False


class DjangoServerLogFilter(logging.Filter):
    """Фильтр для парсинга и преобразования логов Django development server"""

    def __init__(self):
        super().__init__()
        self._filtering = False  # 🔥 ЗАЩИТА ОТ РЕКУРСИИ

    def filter(self, record):
        # 🔥 ЗАЩИТА ОТ РЕКУРСИИ
        if self._filtering:
            return True

        self._filtering = True
        try:
            # Если это лог от django.server, парсим его
            if record.name == 'django.server' and hasattr(record, 'msg'):
                original_message = record.msg

                # Пытаемся распарсить разные форматы Django логов
                if isinstance(original_message, str) and (
                        'HTTP' in original_message or '"GET' in original_message or '"POST' in original_message):
                    try:
                        # Формат 1: "GET /search/ HTTP/1.1" 200 43754
                        # Формат 2: [30/Sep/2025 18:52:30] "GET / HTTP/1.1" 302 0

                        # Убираем временную метку если есть
                        message_clean = original_message
                        if '] "' in original_message:
                            # Убираем часть с временем [30/Sep/2025 18:52:30]
                            message_clean = original_message.split('] "', 1)[1]
                            message_clean = '"' + message_clean

                        # Разбираем сообщение на компоненты
                        parts = message_clean.split('"')
                        if len(parts) >= 3:
                            request_part = parts[1]  # "GET / HTTP/1.1"
                            status_part = parts[2].strip()  # "200 43754"

                            # Парсим статус
                            status_parts = status_part.split()
                            status_code = status_parts[0] if status_parts else '???'
                            response_size = status_parts[1] if len(status_parts) > 1 else '0'

                            # Определяем уровень логирования по статусу
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

                            # Создаем красивое сообщение
                            method = request_part.split()[0] if ' ' in request_part else '???'
                            path = request_part.split()[1] if len(request_part.split()) > 1 else '???'

                            # Обрезаем длинные пути и параметы
                            if '?' in path:
                                base_path, params = path.split('?', 1)
                                if len(base_path) > 30:
                                    path = base_path[:27] + '...?' + params
                                else:
                                    path = base_path + '?...'
                            elif len(path) > 50:
                                path = path[:47] + '...'

                            # Форматируем размер ответа
                            try:
                                size_int = int(response_size)
                                if size_int > 1024 * 1024:  # > 1MB
                                    size_str = f"{size_int / (1024 * 1024):.1f}MB"
                                elif size_int > 1024:  # > 1KB
                                    size_str = f"{size_int / 1024:.1f}KB"
                                else:
                                    size_str = f"{size_int}B"
                            except:
                                size_str = f"{response_size}B"

                            record.msg = f"{status_emoji} {method} {path} → {status_code} ({size_str})"

                    except Exception as e:
                        # Если не удалось распарсить, оставляем как есть но добавляем эмодзи
                        record.msg = f"🌐 {original_message}"

            return True
        finally:
            self._filtering = False


def setup_logging():
    """Настройка единой системы логирования для всего проекта"""
    global _logging_initialized

    # ✅ Защита от повторной инициализации
    if _logging_initialized:
        return

    _logging_initialized = True

    # Создаем папку для логов если её нет
    os.makedirs('logs', exist_ok=True)
    # Создаем подпапки для разных компонентов
    os.makedirs('logs/system', exist_ok=True)
    os.makedirs('logs/bot', exist_ok=True)
    os.makedirs('logs/django', exist_ok=True)
    os.makedirs('logs/parsing', exist_ok=True)
    os.makedirs('logs/website', exist_ok=True)
    os.makedirs('logs/apps', exist_ok=True)

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
                'format': '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
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
            'postgresql_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/postgresql/postgresql.log',
                'maxBytes': 10 * 1024 * 1024,  # 10 MB
                'backupCount': 5,
                'formatter': 'detailed',
                'level': 'DEBUG',
                'encoding': 'utf-8',
            },
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
            # 🎯 ФАЙЛОВЫЕ ОБРАБОТЧИКИ ДЛЯ РАЗНЫХ КОМПОНЕНТОВ
            'system_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/system/system.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8',
            },
            'bot_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/bot/bot.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8',
            },
            'django_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/django/django.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8',
            },
            'parsing_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/parsing/parsing.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8',
            },
            'website_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/website/website.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8',
            },
            'apps_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/apps/general.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'INFO',
                'encoding': 'utf-8',
            },
            'error_file': {
                '()': SafeRotatingFileHandler,
                'filename': 'logs/apps/errors.log',
                'maxBytes': 5 * 1024 * 1024,  # 5 MB
                'backupCount': 3,
                'formatter': 'detailed',
                'level': 'WARNING',
                'encoding': 'utf-8',
            },
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'loggers': {
            # 🌐 Django development server
            'django.server': {
                'handlers': ['django_console', 'django_file'],
                'level': 'INFO',
                'propagate': False,
                'filters': ['django_server_filter']
            },

            # 👤 Логи действий пользователей
            'user.actions': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO',
                'propagate': False,
            },

            # ⚙️ Management commands
            'website.management': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },
            'website.management.commands': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },
            'website.management.commands.create_backup': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },
            'website.management.commands.deduct_daily_payments': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },
            'django.requests': {
                'handlers': ['console', 'django_file'],
                'level': 'INFO',
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
            'parser.utils': {
                'handlers': ['console', 'parsing_file'],
                'level': 'INFO',
                'propagate': False
            },
            'parser.core': {
                'handlers': ['console', 'parsing_file'],
                'level': 'INFO',
                'propagate': False
            },
            'parser.timer': {
                'handlers': ['console', 'parsing_file'],
                'level': 'INFO',
                'propagate': False
            },
            'parser.validator': {
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
            'bot.handlers': {
                'handlers': ['console', 'bot_file'],
                'level': 'INFO',
                'propagate': False
            },
            'bot.services': {
                'handlers': ['console', 'bot_file'],
                'level': 'INFO',
                'propagate': False
            },
            'bot.group_manager': {
                'handlers': ['console', 'bot_file'],
                'level': 'INFO',
                'propagate': False
            },
            'bot.system': {
                'handlers': ['console', 'bot_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 🏢 Система запуска
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

            # 🌐 Django
            'django': {
                'handlers': ['console', 'django_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'django.system': {
                'handlers': ['console', 'django_file'],
                'level': 'INFO',
                'propagate': False
            },
            'django.db.backends': {
                'handlers': ['console', 'apps_file', 'postgresql_file'],
                'level': 'DEBUG',
                'propagate': False
            },

            # 🎯 Сайт
            'website': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },
            'apps.website': {
                'handlers': ['console', 'website_file'],
                'level': 'INFO',
                'propagate': False
            },

            # ⚙️ Core компоненты
            'apps.core': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO',
                'propagate': False
            },
            'apps': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 🔧 Utils компоненты
            'utils': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 📊 WSGI
            'wsgi': {
                'handlers': ['console', 'system_file'],
                'level': 'INFO',
                'propagate': False
            },

            # ⚡ HTTP библиотеки
            'httpx': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'httpcore': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'telegram': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'selenium': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },
            'urllib3': {
                'handlers': ['console', 'apps_file'],
                'level': 'WARNING',
                'propagate': False
            },

            # 🎯 Другие важные логгеры
            'scheduler': {
                'handlers': ['console', 'system_file'],
                'level': 'INFO',
                'propagate': False
            },

            # 🎯 Корневой логгер для всего остального
            '': {
                'handlers': ['console', 'apps_file'],
                'level': 'INFO'
            }
        }
    }

    # Применяем конфигурацию
    logging.config.dictConfig(LOGGING_CONFIG)

    # Тестовое сообщение
    logger = logging.getLogger('system.run')
    logger.info("🎨 Система логирования инициализирована (консоль + файлы)")

# Простые функции для красивого вывода (для run.py)
def print_success(text):
    """Красивые успешные сообщения"""
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")


def print_error(text):
    """Красивые сообщения об ошибках"""
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")


def print_warning(text):
    """Красивые предупреждения"""
    print(f"{Fore.YELLOW}⚠️ {text}{Style.RESET_ALL}")


def print_info(text):
    """Красивые информационные сообщения"""
    print(f"{Fore.BLUE}ℹ️ {text}{Style.RESET_ALL}")


def print_banner(text):
    """Красивые баннеры"""
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")


def print_step(text):
    """Красивые сообщения о шагах выполнения"""
    print(f"{Fore.MAGENTA}🚀 {text}{Style.RESET_ALL}")


def print_divider():
    """Разделитель для визуального отделения секций"""
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")


# Утилиты для работы с логгерами в других модулях
def get_logger(name):
    """Получить настроенный логгер по имени"""
    return logging.getLogger(name)


def set_log_level(level_name):
    """Установить уровень логирования для всех логгеров"""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.getLogger().setLevel(level)
    for logger_name in logging.root.manager.loggerDict:
        logging.getLogger(logger_name).setLevel(level)


def get_run_logger():
    """Получить логгер для run.py и основных системных сообщений"""
    return logging.getLogger('system.run')


def get_parser_logger():
    """Получить логгер для парсера"""
    return logging.getLogger('parser.selenium')


def get_bot_logger():
    """Получить логгер для бота"""
    return logging.getLogger('bot.telegram')


def get_django_logger():
    """Получить логгер для Django"""
    return logging.getLogger('django')


def get_settings_logger():
    """Получить логгер для настроек"""
    return logging.getLogger('settings.system')


def get_website_logger():
    """Получить логгер для веб-сайта"""
    return logging.getLogger('apps.website')


def test_logging_system():
    """Тестирование системы логирования"""
    print_divider()
    print_banner("🎯 ТЕСТИРОВАНИЕ СИСТЕМЫ ЛОГИРОВАНИЯ (консоль + файлы)")
    print_divider()

    # Тестируем разные логгеры
    test_cases = [
        ('parser.selenium', "🚀 Тест парсера - INFO"),
        ('parser.selenium', "⚠️ Тест парсера - WARNING", logging.WARNING),
        ('bot.telegram', "🤖 Тест бота - INFO"),
        ('bot.telegram', "❌ Тест бота - ERROR", logging.ERROR),
        ('apps.core', "⚙️ Тест настроек - INFO"),
        ('apps.website', "📊 Тест сайта - INFO"),
        ('system.run', "🏢 Тест системы - INFO"),
        ('settings.system', "🔧 Тест настроек системы - INFO"),
        ('django', "🌐 Тест Django - WARNING", logging.WARNING),
        ('scheduler', "⏰ Тест планировщика - INFO"),
    ]

    for logger_name, message, *level in test_cases:
        logger = get_logger(logger_name)
        if level:
            log_method = getattr(logger, logging.getLevelName(level[0]).lower())
            log_method(message)
        else:
            logger.info(message)

    print_divider()
    print_success("Тестирование завершено! Логи сохраняются в папку logs/")
    print_divider()


if __name__ == "__main__":
    # Тестирование системы логирования
    setup_logging()
    test_logging_system()