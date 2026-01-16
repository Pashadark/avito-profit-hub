#!/usr/bin/env python3
"""
Запуск системы ProfitHub
Улучшенная версия с трекингом используемых файлов
"""

import os
import sys
import logging
import asyncio
import threading
import schedule
import subprocess
import signal
import psutil
from datetime import datetime
import time
import argparse
import socket
import importlib
import inspect
from pathlib import Path
import builtins
from apps.core.logging_config import get_logger
logger = get_logger('system.run')

# ============================================
# НАСТРОЙКА ПУТЕЙ ИМПОРТА ПЕРЕД ВСЕМИ ИМПОРТАМИ
# ============================================

# Получаем корневую директорию проекта
BASE_DIR = Path(__file__).resolve().parent

# 1. Добавляем корневую директорию проекта
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 2. Добавляем папку apps для импорта apps.core
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# 3. Добавляем текущую директорию для импорта модулей из корня
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# ============================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================

INITIALIZED_MODULES = {
    'django': False,
    'parsing': False,  # ИЗМЕНЕНО: было 'parser'
    'bot': False,
    'logging': False
}


# ============================================
# НАСТРОЙКА ЛОГГИРОВАНИЯ - ПРАВИЛЬНЫЙ ИМПОРТ
# ============================================

# Сначала создаем простые логгеры как запасной вариант
def create_fallback_logging():
    """Создание запасной системы логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    def get_logger(name):
        logger = logging.getLogger(name)
        # Убедимся что у логгера есть обработчики
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)
        return logger

    def setup_logging():
        pass

    return setup_logging, get_logger


# Пробуем импортировать логирование
LOGGING_SETUP = False
setup_logging = None
get_logger = None
system_logger = None
bot_logger = None
parsing_logger = None  # ИЗМЕНЕНО: было parser_logger
django_logger = None

try:
    # Пробуем импорт из новой структуры
    from apps.core.logging_config import setup_logging, get_logger

    LOGGING_SETUP = True
    logger.info(f"✅ Успешно импортирован apps.core.logging_config")
except ImportError:
    try:
        # Пробуем импорт из старой структуры
        from apps.core.logging_config import setup_logging

        LOGGING_SETUP = True
        logger.info(f"✅ Успешно импортирован core.logging_config")
    except ImportError:
        # Используем запасной вариант
        logger.info(f"⚠️  Используем запасную систему логирования")
        setup_logging, get_logger = create_fallback_logging()
        LOGGING_SETUP = True

# Настраиваем логирование
if LOGGING_SETUP and not INITIALIZED_MODULES['logging']:
    try:
        setup_logging()
        INITIALIZED_MODULES['logging'] = True
    except Exception as e:
        logger.info(f"⚠️  Ошибка настройки логирования: {e}")
        # Все равно создаем логгеры

# Создаем логгеры
system_logger = get_logger('system.run')
bot_logger = get_logger('bot.telegram')
parsing_logger = get_logger('apps.parsing')  # ИЗМЕНЕНО: было 'parser.selenium'
django_logger = get_logger('django.system')


# Функции для удобства
def print_success(text):
    system_logger.info(f"✅ {text}")



def print_error(text):
    system_logger.error(f"❌ {text}")



def print_warning(text):
    system_logger.warning(f"⚠️ {text}")



def print_info(text):
    system_logger.info(f"ℹ️ {text}")



def print_banner(text):
    system_logger.info(f"🎯 {text}")
    print(f"\033[1;36m{text}\033[0m")


# ============================================
# ТРЕКИНГ ФАЙЛОВ
# ============================================

class FileUsageTracker:
    """Трекинг используемых файлов в проекте"""

    def __init__(self):
        self.used_files = set()
        self.all_files = set()
        self.project_root = Path(__file__).parent
        self.ignored_dirs = {
            'venv', '.venv', '__pycache__', '.git', 'node_modules',
            '.idea', 'migrations', '.vscode', '.pytest_cache',
            'static', 'media', 'logs', 'temp', 'database_backups'
        }
        self.ignored_extensions = {'.pyc', '.log', '.sqlite3', '.db', '.tmp', '.cache', '.joblib', '.pt', '.encrypted'}

    def scan_all_files(self):
        """Сканирует все файлы в проекте"""
        print_info("Сканирование файлов проекта...")

        for file_path in self.project_root.rglob('*'):
            if file_path.is_file():
                # Пропускаем игнорируемые директории и файлы
                if any(ignored in str(file_path) for ignored in self.ignored_dirs):
                    continue
                if file_path.suffix in self.ignored_extensions:
                    continue

                self.all_files.add(str(file_path.relative_to(self.project_root)))

        print_success(f"Найдено файлов: {len(self.all_files)}")
        return self.all_files

    def analyze_project_dependencies(self):
        """Анализ зависимостей проекта через импорты"""
        print_info("Анализ зависимостей проекта...")

        # Критически важные файлы, которые всегда используются
        critical_files = {
            # Core Django
            'manage.py', 'run.py',
            'apps/core/__init__.py', 'apps/core/settings.py', 'apps/core/urls.py',
            'apps/core/wsgi.py', 'apps/core/asgi.py', 'apps/core/logging_config.py',

            # Bot
            'apps/bot/__init__.py', 'apps/bot/bot.py', 'apps/bot/apps.py',
            'apps/bot/handlers/__init__.py', 'apps/bot/handlers/main_handlers.py',
            'apps/bot/handlers/smart_handlers.py', 'apps/bot/handlers/conversation_handlers.py',
            'apps/bot/keyboards/__init__.py', 'apps/bot/keyboards/vision_keyboards.py',
            'apps/bot/services/__init__.py',

            # Parsing (ИЗМЕНЕНО: было parser)
            'apps/parsing/__init__.py', 'apps/parsing/apps.py',
            'apps/parsing/utils/__init__.py', 'apps/parsing/utils/selenium_parser.py',
            'apps/parsing/core/__init__.py', 'apps/parsing/core/settings_manager.py',

            # Website (ИЗМЕНЕНО: было dashboard)
            'apps/website/__init__.py', 'apps/website/apps.py', 'apps/website/models.py',
            'apps/website/views.py', 'apps/website/admin.py', 'apps/website/urls.py',
            'apps/website/forms.py', 'apps/website/middleware.py',
            'apps/website/context_processors.py', 'apps/website/encryption.py',
            'apps/website/console_capture.py', 'apps/website/console_manager.py',
            'apps/website/database_replication.py', 'apps/website/log_viewer.py',

            # Management commands
            'apps/website/management/__init__.py', 'apps/website/management/commands/__init__.py',
            'apps/website/management/commands/daily_backup.py',
            'apps/website/management/commands/daily_subscription_charge.py',
            'apps/website/management/commands/deduct_daily_payments.py',
            'apps/website/management/commands/fix_admin.py',
            'apps/website/management/commands/fix_default_settings.py',
            'apps/website/management/commands/init_subscriptions.py',
            'apps/website/management/commands/test_logging.py',

            # Config files
            'requirements.txt', 'pyproject.toml', 'custom_user_agents.py'
        }

        # Добавляем критические файлы
        for file in critical_files:
            if (self.project_root / file).exists():
                self.used_files.add(file)
                print_success(f"Добавлен критический файл: {file}")

    def analyze_django_apps(self):
        """Анализ Django приложений и их файлов"""
        try:
            from django.apps import apps

            print_info("Анализ Django приложений...")

            for app_config in apps.get_app_configs():
                app_path = Path(app_config.path)
                if self.project_root in app_path.parents:
                    rel_path = app_path.relative_to(self.project_root)

                    # Добавляем все Python файлы приложения
                    for py_file in app_path.rglob('*.py'):
                        if py_file.is_file():
                            file_rel_path = py_file.relative_to(self.project_root)
                            self.used_files.add(str(file_rel_path))
                            print_success(f"Добавлен файл приложения: {file_rel_path}")

        except Exception as e:
            print_warning(f"Ошибка анализа Django приложений: {e}")

    def analyze_imports_recursively(self, start_module):
        """Рекурсивный анализ импортов из начального модуля"""
        try:
            visited = set()

            def analyze_module(module_name):
                if module_name in visited:
                    return
                visited.add(module_name)

                try:
                    module = importlib.import_module(module_name)

                    # Получаем путь к файлу модуля
                    if hasattr(module, '__file__') and module.__file__:
                        file_path = Path(module.__file__)
                        if self.project_root in file_path.parents:
                            rel_path = file_path.relative_to(self.project_root)
                            self.used_files.add(str(rel_path))

                            # Добавляем __init__.py для пакетов
                            if rel_path.name != '__init__.py':
                                init_file = rel_path.parent / '__init__.py'
                                if init_file.exists():
                                    self.used_files.add(str(init_file))

                    # Анализируем импорты модуля
                    if hasattr(module, '__file__'):
                        try:
                            with open(module.__file__, 'r', encoding='utf-8') as f:
                                content = f.read()

                            # Ищем импорты в коде
                            import re
                            imports = re.findall(r'^(?:import|from)\s+(\S+)', content, re.MULTILINE)

                            for imp in imports:
                                # Очищаем импорт
                                imp = imp.split(' ')[0].split(',')[0].strip()
                                if imp and not imp.startswith('.') and not imp.startswith('_'):
                                    try:
                                        # Пробуем импортировать найденный модуль
                                        analyze_module(imp)
                                    except:
                                        # Пробуем с префиксом проекта
                                        project_imports = [
                                            f'apps.bot.{imp}', f'apps.parsing.{imp}',  # ИЗМЕНЕНО
                                            f'apps.website.{imp}', f'apps.core.{imp}'  # ИЗМЕНЕНО
                                        ]
                                        for project_imp in project_imports:
                                            try:
                                                analyze_module(project_imp)
                                                break
                                            except:
                                                continue

                        except Exception as e:
                            print_warning(f"Ошибка анализа файла {module.__file__}: {e}")

                except Exception as e:
                    print_warning(f"Ошибка анализа модуля {module_name}: {e}")

            # Запускаем анализ с корневых модулей
            root_modules = ['apps.core', 'apps.bot', 'apps.parsing', 'apps.website']  # ИЗМЕНЕНО
            for root_mod in root_modules:
                try:
                    analyze_module(root_mod)
                except:
                    continue

        except Exception as e:
            print_warning(f"Ошибка рекурсивного анализа: {e}")

    def get_unused_files(self):
        """Получить список неиспользуемых файлов"""
        unused_files = self.all_files - self.used_files

        # Исключаем временные и backup файлы
        exclude_patterns = {
            'backup', 'patch', 'export', '.patch', 'unnamed'
        }

        return [f for f in unused_files if not any(pattern in f.lower() for pattern in exclude_patterns)]

    def generate_report(self):
        """Генерация отчета об использовании файлов"""
        unused_files = self.get_unused_files()

        report = []
        report.append("=" * 60)
        report.append("📊 ОТЧЕТ ОБ ИСПОЛЬЗОВАНИИ ФАЙЛОВ")
        report.append("=" * 60)
        report.append(f"📁 Всего файлов в проекте: {len(self.all_files)}")
        report.append(f"🔧 Используется файлов: {len(self.used_files)}")
        report.append(f"🗑️  Неиспользуемых файлов: {len(unused_files)}")
        report.append("")

        if unused_files:
            report.append("🚨 ВОЗМОЖНО НЕИСПОЛЬЗУЕМЫЕ ФАЙЛЫ:")
            for file in sorted(unused_files)[:20]:
                report.append(f"  ❌ {file}")

            if len(unused_files) > 20:
                report.append(f"  ... и еще {len(unused_files) - 20} файлов")
        else:
            report.append("✅ Все файлы используются!")

        report.append("")
        report.append("💡 Совет: Проверьте файлы перед удалением!")
        report.append("=" * 60)

        return "\n".join(report)


# ============================================
# ОСНОВНЫЕ ФУНКЦИИ СИСТЕМЫ
# ============================================

def setup_django_safe():
    """Безопасная настройка Django без повторной инициализации"""
    global INITIALIZED_MODULES

    if INITIALIZED_MODULES['django']:
        print_info("Django уже настроен ранее")
        return True

    try:
        # Проверяем, не настроен ли уже Django
        from django.conf import settings
        if settings.configured:
            print_info("Django уже настроен системой")
            INITIALIZED_MODULES['django'] = True
            # Инициализируем парсер после настройки Django (ОДИН РАЗ)
            if not INITIALIZED_MODULES['parsing']:
                initialize_parser_after_django()
            return True

        # Устанавливаем настройки Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')
        print_info(f"DJANGO_SETTINGS_MODULE = {os.environ.get('DJANGO_SETTINGS_MODULE')}")

        # Настраиваем Django только если еще не настроен
        import django
        django.setup()

        print_success("Django настроен успешно")

        INITIALIZED_MODULES['django'] = True

        # Инициализируем парсер после настройки Django (ОДИН РАЗ)
        if not INITIALIZED_MODULES['parsing']:
            initialize_parser_after_django()

        return True

    except Exception as e:
        print_error(f"Ошибка настройки Django: {e}")
        import traceback
        traceback.print_exc()
        return False

def initialize_parser_after_django():
    """Инициализирует парсер после настройки Django"""
    global INITIALIZED_MODULES

    if INITIALIZED_MODULES['parsing']:
        print_info("Парсер уже инициализирован ранее")
        return

    try:
        from apps.parsing.utils.selenium_parser import selenium_parser  # ИЗМЕНЕНО
        selenium_parser.initialize_with_django()
        INITIALIZED_MODULES['parsing'] = True
        print_success("Парсер инициализирован с настройками Django")
    except Exception as e:
        print_warning(f"Ошибка инициализации парсера: {e}")

def start_subscription_scheduler():
    """Запуск планировщика подписок (замена Celery)"""
    print_info("Запуск системы автоматического списания...")

    try:
        from apps.website.scheduler import scheduler  # ИЗМЕНЕНО

        if scheduler.is_running:
            print_warning("⚠️ Система списания уже запущена")
            return True

        success = scheduler.start()

        if success:
            print_success("✅ Система автоматического списания запущена!")
            print_info("🤖 Умное списание будет выполняться ежедневно в 06:00")
            print_info("🔧 Проверка здоровья подписок в 00:30")
            return True
        else:
            print_error("❌ Не удалось запустить систему списания")
            return False

    except Exception as e:
        print_error(f"❌ Ошибка запуска системы списания: {e}")
        return False


def stop_subscription_scheduler():
    """Остановка планировщика подписок"""
    print_info("Остановка системы автоматического списания...")

    try:
        # ✅ Проверяем, настроен ли Django перед импортом
        from django.conf import settings
        if not settings.configured:
            print_warning("⚠️ Django не настроен, пропускаем остановку планировщика")
            return True

        from apps.website.scheduler import scheduler

        if not scheduler.is_running:
            print_warning("⚠️ Система списания уже остановлена")
            return True

        success = scheduler.stop()

        if success:
            print_success("✅ Система автоматического списания остановлена!")
            return True
        else:
            print_error("❌ Не удалось остановить систему списания")
            return False

    except Exception as e:
        print_warning(f"⚠️ Ошибка остановки системы списания: {e}")
        return True  # ✅ Все равно возвращаем True чтобы продолжить остановку


def test_subscription_tasks():
    """Тестирование задач списания (замена тестирования Celery)"""
    print_info("Тестирование системы автоматического списания...")

    try:
        if not setup_django_safe():
            print_error("Не удалось настроить Django")
            return False

        from apps.website.scheduler import scheduler  # ИЗМЕНЕНО
        from django.contrib.auth.models import User
        from apps.website.models import UserProfile  # ИЗМЕНЕНО

        # Проверим текущий баланс
        admin_user = User.objects.get(username='admin')
        profile = UserProfile.objects.get(user=admin_user)
        print_info(f"💰 Текущий баланс: {profile.balance}₽")

        # Тестируем списание
        print_info("🔄 Запуск тестового списания...")
        result1 = scheduler.run_daily_charge()

        if result1:
            print_success("✅ Тестовое списание завершено успешно")
        else:
            print_warning("⚠️ Тестовое списание завершено с проблемами")

        # Тестируем проверку здоровья
        print_info("🔄 Запуск проверки здоровья...")
        result2 = scheduler.run_health_check()

        if result2:
            print_success("✅ Проверка здоровья завершена успешно")
        else:
            print_warning("⚠️ Проверка здоровья завершена с проблемами")

        # Проверим баланс после теста
        profile.refresh_from_db()
        print_success(f"💰 Баланс после теста: {profile.balance}₽")

        return True

    except Exception as e:
        print_error(f"❌ Ошибка тестирования: {e}")
        return False


def get_scheduler_status():
    """Получить статус планировщика"""
    try:
        from apps.website.scheduler import scheduler  # ИЗМЕНЕНО
        status = scheduler.get_status()

        print_info("=== СТАТУС СИСТЕМЫ АВТОМАТИЧЕСКОГО СПИСАНИЯ ===")
        print_info(f"Статус: {status['status']}")
        print_info(f"Заданий в расписании: {status['jobs_count']}")
        print_info(f"Следующий запуск: {status['next_run']}")

        if status['running']:
            print_success("✅ Система работает нормально")
        else:
            print_warning("⚠️ Система остановлена")

        return True

    except Exception as e:
        print_error(f"❌ Ошибка получения статуса: {e}")
        return False


def start_telegram_bot():
    """Запуск Telegram бота в отдельном процессе"""
    global INITIALIZED_MODULES

    if INITIALIZED_MODULES['bot']:
        print_info("🤖 Telegram бот уже запущен ранее")
        return True

    system_logger.info("🤖 Запуск Telegram бота...")

    try:
        kill_existing_bot_processes()

        # Запускаем бота в отдельном процессе
        def run_bot():
            try:
                # Импортируем и запускаем бота в отдельном процессе
                from apps.bot.bot import initialize_bot  # ИЗМЕНЕНО
                INITIALIZED_MODULES['bot'] = True
                initialize_bot()
            except Exception as e:
                bot_logger.error(f"Ошибка бота: {e}")
                INITIALIZED_MODULES['bot'] = False

        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()

        time.sleep(3)  # Даем время боту запуститься
        bot_logger.info("✅ Telegram бот запущен успешно")
        return True

    except Exception as e:
        system_logger.error(f"Ошибка запуска бота: {e}")
        return False


def start_parser_system(timer_hours=None, browser_windows=1, site='avito'):
    """Запуск системы парсера с новыми параметрами"""
    print_info("Запуск системы парсера с параметрами:")
    print_info(f"   • Таймер: {timer_hours} часов" if timer_hours else "   • Таймер: не установлен")
    print_info(f"   • Окна браузера: {browser_windows}")
    print_info(f"   • Сайт: {site}")
    print_banner("=" * 50)

    try:
        # Настраиваем Django если еще не настроен
        if not INITIALIZED_MODULES['django']:
            setup_django_safe()

        # Запускаем парсер в отдельном процессе
        def run_parser():
            try:
                # Импортируем внутри потока чтобы избежать циклических импортов
                from apps.parsing.utils.selenium_parser import selenium_parser  # ИЗМЕНЕНО

                # Создаем новое событийное loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def async_run():
                    # ЗАМЕНИЛ НА ПРАВИЛЬНЫЙ МЕТОД - check_prices_and_notify
                    await selenium_parser.check_prices_and_notify()

                loop.run_until_complete(async_run())
            except Exception as e:
                print_error(f"Ошибка запуска парсера: {e}")
                import traceback
                traceback.print_exc()

        parser_thread = threading.Thread(target=run_parser, daemon=True)
        parser_thread.start()

        print_success("Система парсера запущена успешно")
        return True

    except Exception as e:
        print_error(f"Ошибка запуска системы парсера: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parser_system():
    """Тестирование парсера с демо-режимом"""
    print_info("Тестирование системы парсера...")

    try:
        if not setup_django_safe():
            print_error("Не удалось настроить Django")
            return False

        # Импортируем парсер
        from apps.parsing.utils.selenium_parser import selenium_parser  # ИЗМЕНЕНО

        print_info("Инициализация парсера...")
        print_success("Парсер загружен успешно")
        print_info(f"Поисковые запросы: {selenium_parser.search_queries}")
        print_info(f"Исключаемые слова: {selenium_parser.exclude_keywords}")

        # Тестируем настройки
        test_settings = {
            'keywords': 'iPhone, MacBook, Видеокарта',
            'exclude_keywords': 'б/у, сломан',
            'min_price': 1000,
            'max_price': 50000
        }

        result = selenium_parser.update_settings(test_settings)
        if result:
            print_success("Настройки успешно обновлены")
        else:
            print_error("Ошибка обновления настроек")

        print_success("Тестирование завершено успешно!")
        return True

    except Exception as e:
        print_error(f"Ошибка тестирования системы парсера: {e}")
        return False


def test_components():
    """Тестирование компонентов системы"""
    print_info("Тестирование компонентов...")

    try:
        if not setup_django_safe():
            print_error("Не удалось настроить Django")
            return False

        # Проверяем базовые импорты
        try:
            from django.db import connection
            connection.ensure_connection()
            print_success("База данных подключена")
        except Exception as e:
            print_error(f"Ошибка БД: {e}")

        try:
            from apps.website.models import UserProfile  # ИЗМЕНЕНО
            user_count = UserProfile.objects.count()
            print_success(f"Модели загружены (пользователей: {user_count})")
        except Exception as e:
            print_warning(f"Ошибка моделей: {e}")

        # ТЕСТИРУЕМ ПАРСЕР
        try:
            from apps.parsing.utils.selenium_parser import SeleniumAvitoParser  # ИЗМЕНЕНО
            parser = SeleniumAvitoParser()
            print_success(f"Парсер загружен (запросы: {len(parser.search_queries)})")
        except Exception as e:
            print_error(f"Ошибка загрузки парсера: {e}")

        # ТЕСТИРУЕМ МОДУЛИ
        try:
            from apps.parsing.core.settings_manager import SettingsManager  # ИЗМЕНЕНО
            settings = SettingsManager()
            print_success("Менеджер настроек загружен")
        except Exception as e:
            print_error(f"Ошибка загрузки менеджера настроек: {e}")

        print_success("Все основные компоненты загружены")
        return True

    except Exception as e:
        print_error(f"Ошибка тестирования: {e}")
        return False


def start_django_server():
    """Запуск Django сервера с доступом по WiFi"""
    print_info("Запуск Django сервера...")

    try:
        # Получаем локальный IP адрес автоматически
        def get_local_ip():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    return s.getsockname()[0]
            except:
                return "192.168.3.15"  # fallback на ваш IP

        local_ip = get_local_ip()

        print_info(f"Локальный IP: {local_ip}")
        print_info(f"Ссылка для телефона: http://{local_ip}:8000")

        # Запускаем сервер на всех интерфейсах
        server_process = subprocess.Popen([
            sys.executable, 'manage.py', 'runserver',
            f'{local_ip}:8000', '--noreload'
        ])

        # Даем время серверу запуститься
        time.sleep(5)

        # Проверяем, запустился ли сервер
        import requests
        try:
            response = requests.get(f'http://{local_ip}:8000/', timeout=10)
            if response.status_code == 200:
                print_success(f"Django сервер запущен на http://{local_ip}:8000")
                print_info(f"Откройте на телефоне: http://{local_ip}:8000")
                return True
        except Exception as e:
            print_warning(f"Сервер запускается... Проверьте: http://{local_ip}:8000")
            print_info("Если не открывается, проверьте брандмауэр")
            return True

        return True

    except Exception as e:
        print_error(f"Ошибка запуска Django сервера: {e}")
        return False


def kill_existing_bot_processes():
    """Безопасная проверка и остановка процессов бота - ИСПРАВЛЕННАЯ"""
    print_info("Проверка запущенных процессов...")

    try:
        current_pid = os.getpid()
        print_info(f"Текущий PID: {current_pid}")

        processes_found = []
        current_cmdline = ""

        # Сначала получаем наш cmdline
        try:
            current_process = psutil.Process(current_pid)
            current_cmdline = ' '.join(current_process.cmdline()) if current_process.cmdline() else ""
            print_info(f"Наш процесс: {current_cmdline[:80]}...")
        except:
            pass

        # Сканируем процессы
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pid = proc.info['pid']

                # АБСОЛЮТНО пропускаем текущий процесс
                if pid == current_pid:
                    continue

                # Пропускаем если нет cmdline
                if not proc.info['cmdline']:
                    continue

                cmdline = ' '.join(proc.info['cmdline'])

                # ОЧЕНЬ ТОЧНАЯ проверка - это наш проект?
                is_our_bot = 'bot.py' in cmdline and 'apps/bot' in cmdline
                is_our_django = 'manage.py' in cmdline and 'runserver' in cmdline

                if is_our_bot or is_our_django:
                    processes_found.append((pid, cmdline[:80]))

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Останавливаем только найденные конфликтующие процессы
        stopped = []
        for pid, cmdline in processes_found:
            try:
                print_warning(f"⚠️ Останавливаем конфликтующий процесс: PID={pid}, cmd={cmdline}")
                p = psutil.Process(pid)
                p.terminate()

                # Ждем немного но не блокируем
                try:
                    p.wait(timeout=1)
                except:
                    try:
                        p.kill()
                    except:
                        pass

                stopped.append(pid)

            except Exception as e:
                print_warning(f"⚠️ Не удалось остановить {pid}: {e}")

        if stopped:
            print_success(f"✅ Остановлено конфликтующих процессов: {len(stopped)}")
        else:
            print_success("✅ Конфликтующих процессов не найдено")

        return True

    except Exception as e:
        print_warning(f"⚠️ Ошибка проверки процессов: {e}")
        return True  # ✅ Все равно продолжаем


def stop_all_processes():
    """Остановка всех процессов системы - ИСПРАВЛЕННАЯ"""
    global INITIALIZED_MODULES

    print_info("Остановка всех процессов ProfitHub...")

    try:
        current_pid = os.getpid()
        print_info(f"Текущий PID: {current_pid}")

        # ПРОСТОЙ СПОСОБ: останавливаем только явно конфликтующие процессы
        processes_to_check = ['bot.py', 'manage.py runserver']

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pid = proc.info['pid']

                # НИКОГДА не останавливаем текущий процесс
                if pid == current_pid:
                    continue

                if not proc.info['cmdline']:
                    continue

                cmdline = ' '.join(proc.info['cmdline'])

                # Проверяем только конкретные процессы
                should_stop = False

                if 'manage.py' in cmdline and 'runserver' in cmdline:
                    should_stop = True
                elif 'bot.py' in cmdline and 'apps/bot' in cmdline:
                    should_stop = True
                elif 'python' in cmdline and ('--timer' in cmdline or '--windows' in cmdline):
                    should_stop = True

                if should_stop:
                    print_warning(f"⚠️ Останавливаем PID: {pid}")
                    try:
                        proc.terminate()
                        # Даем 0.5 секунды, потом kill если нужно
                        try:
                            proc.wait(timeout=0.5)
                        except:
                            proc.kill()
                    except:
                        pass

            except:
                continue

        print_success("✅ Запрошена остановка конфликтующих процессов")

        # ✅ Пробуем остановить планировщик
        try:
            stop_subscription_scheduler()
        except:
            print_warning("⚠️ Не удалось остановить планировщик")

        # ✅ Сбрасываем флаги
        for key in INITIALIZED_MODULES:
            INITIALIZED_MODULES[key] = False

        return True

    except Exception as e:
        print_error(f"❌ Ошибка: {e}")
        return True


def clean_cache():
    """Очистка кеша и временных файлов"""
    print_info("Очистка кеша...")

    try:
        # Очищаем pycache
        for root, dirs, files in os.walk('.'):
            for dir in dirs:
                if dir == '__pycache__':
                    pycache_path = os.path.join(root, dir)
                    try:
                        import shutil
                        shutil.rmtree(pycache_path, ignore_errors=True)
                    except:
                        pass

        # Очищаем логи
        if os.path.exists('profithub.log'):
            try:
                with open('profithub.log', 'w') as f:
                    f.write('')
            except:
                pass

        print_success("Кеш и временные файлы очищены")
        return True

    except Exception as e:
        print_error(f"Ошибка очистка кеша: {e}")
        return False


def run_migrations():
    """Применение миграций базы данных"""
    print_info("Применение миграций...")

    try:
        # Сначала настраиваем Django
        if not setup_django_safe():
            print_error("Не удалось настроить Django")
            return False

        result = subprocess.run(['python', 'manage.py', 'migrate'],
                                capture_output=True, text=True)

        if result.returncode == 0:
            print_success("Миграции применены успешно")
            return True
        else:
            print_error(f"Ошибка миграций: {result.stderr}")
            return False

    except Exception as e:
        print_error(f"Ошибка выполнения миграций: {e}")
        return False


def create_backup():
    """Создание резервной копии базы данных"""
    print_info("Создание бэкапа БД...")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}.sqlite3"

        if os.path.exists('db.sqlite3'):
            import shutil
            shutil.copy2('db.sqlite3', backup_file)
            print_success(f"Бэкап создан: {backup_file}")
            return True
        else:
            print_error("Файл БД не найден")
            return False

    except Exception as e:
        print_error(f"Ошибка создания бэкапа: {e}")
        return False


def show_status():
    """Показать статус всех процессов"""
    print_info("Статус процессов ProfitHub...")

    try:
        # Проверяем Django сервер
        import requests
        try:
            response = requests.get('http://127.0.0.1:8000/', timeout=5)
            web_status = "✅ Работает" if response.status_code == 200 else "❌ Ошибка"
        except:
            web_status = "❌ Не запущен"

        # Проверяем бота
        bot_status = "❌ Не запущен"
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['cmdline'] and
                        any('bot.py' in cmd for cmd in proc.info['cmdline'])):
                    bot_status = f"✅ Работает (PID: {proc.info['pid']})"
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Проверяем систему списания
        scheduler_status = "❌ Не запущена"
        try:
            from apps.website.scheduler import scheduler  # ИЗМЕНЕНО
            status = scheduler.get_status()
            scheduler_status = f"✅ {status['status']}" if status['running'] else "❌ Остановлена"
        except:
            scheduler_status = "❌ Ошибка проверки"

        # Статус инициализации
        init_status = []
        for key, value in INITIALIZED_MODULES.items():
            status = "✅" if value else "❌"
            init_status.append(f"{key}: {status}")

        print_info(f"Django сервер: {web_status}")
        print_info(f"Telegram бот:  {bot_status}")
        print_info(f"Система списания: {scheduler_status}")
        print_info("Статус инициализации: " + ", ".join(init_status))
        print_info(f"Время системы: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return True

    except Exception as e:
        print_error(f"Ошибка проверки статуса: {e}")
        return False


def analyze_file_usage():
    """Анализ использования файлов в проекте"""
    print_info("Запуск анализа использования файлов...")

    tracker = FileUsageTracker()

    # Сканируем все файлы
    tracker.scan_all_files()

    # Анализируем зависимости проекта
    tracker.analyze_project_dependencies()

    # Запускаем минимальную инициализацию для трекинга
    if setup_django_safe():
        tracker.analyze_django_apps()
        tracker.analyze_imports_recursively('apps.core')  # ИЗМЕНЕНО

    # Генерируем отчет
    report = tracker.generate_report()
    print(report)

    # Сохраняем отчет в файл
    try:
        with open('file_usage_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        print_success("Отчет сохранен в file_usage_report.txt")
    except Exception as e:
        print_error(f"Ошибка сохранения отчета: {e}")

    return len(tracker.get_unused_files())


# ============================================
# КОМАНДЫ И МЕНЮ
# ============================================

def show_commands():
    """Печать доступных команд"""
    commands = """
📋 ДОСТУПНЫЕ КОМАНДЫ:

🌀  Запуск системы:
  python run.py                       - Запуск всего (сайт + бот)
  python run.py --web                 - Только Django сайт  
  python run.py --bot                 - Только Telegram бот
  python run.py --web --bot           - Сайт + бот (полная система)

⚡ Управление процессов:
  python run.py --stop                - Остановить все процессы
  python run.py --status              - Показать статус процессов
  python run.py --restart             - Перезапустить систему

🔍 Анализ проекта:
  python run.py --analyze-files       - 📊 Анализ используемых файлов 🆕

🧹 Очистка и обслуживание:
  python run.py --clean               - Очистка кеша и временных файлов
  python run.py --migrate             - Применить миграции БД
  python run.py --backup              - Создать бэкап БД

🔧 Отладка:
  python run.py --debug               - Запуск с подробным логированием
  python run.py --test                - Тестирование компонентов

🎯 НОВЫЕ ВОЗМОЖНОСТИ ПАРСЕРА:
  python run.py --timer 2 --windows 3 --site avito
  python run.py --windows 1 --site avito
  python run.py --timer 4

💡 Использование: python run.py [КОМАНДА]
Пример: python run.py --status
Пример: python run.py --analyze-files
Пример: python run.py --timer 2 --windows 3 --site avito
"""
    for line in commands.split('\n'):
        print_banner(line)


def show_interactive_menu():
    """Интерактивное меню выбора режима (чистый вывод без времени)"""

    # БАННЕР - чистый вывод (только один раз)
    print("""
╔══════════════════════════════════════════════════════════════╗
║                   SELIBRY SYSTEM v4.0                        ║
║          Система запуска приложений из консоли!              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # МЕНЮ - чистый вывод
    print("🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("=" * 50)

    menu_options = [
        "1.  🚀 Полный запуск (сайт + бот + списание)",
        "2.  🌐 Только Django сайт + списание",
        "3.  🤖 Только Telegram бот + списание",
        "4.  🎯 Запуск парсера с параметрами",
        "5.  ⚡ Показать статус процессов",
        "6.  📊 Анализ используемых файлов 🆕",
        "7.  🗃️  Проверить подключение PostgreSQL 🆕",
        "8.  🤖 Запуск системы автоматического списания 🆕",
        "9.  🧪 Тестирование задач списания 🆕",
        "10. 📋 Статус системы списания 🆕",
        "11. 🛑 Остановить все процессы",
        "12. 🧹 Очистка кеша",
        "13. 📦 Применить миграции БД",
        "14. 💾 Создать бэкап БД",
        "15. 🔧 Тестирование системы",
        "0.  ❌ Выход"
    ]

    for option in menu_options:
        print(option)

    print("=" * 50)


# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    """Основная функция запуска"""
    parser = argparse.ArgumentParser(description='ProfitHub System Manager')
    parser.add_argument('--web', action='store_true', help='Запустить только Django сайт')
    parser.add_argument('--bot', action='store_true', help='Запустить только Telegram бота')
    parser.add_argument('--stop', action='store_true', help='Остановить все процессы')
    parser.add_argument('--status', action='store_true', help='Показать статус процессов')
    parser.add_argument('--restart', action='store_true', help='Перезапустить систему')
    parser.add_argument('--clean', action='store_true', help='Очистка кеша')
    parser.add_argument('--migrate', action='store_true', help='Применить миграции БД')
    parser.add_argument('--backup', action='store_true', help='Создать бэкап БД')
    parser.add_argument('--debug', action='store_true', help='Подробное логирование')
    parser.add_argument('--test', action='store_true', help='Тестирование компонентов')

    # 🔥 НОВЫЙ АРГУМЕНТ ДЛЯ АНАЛИЗА ФАЙЛОВ
    parser.add_argument('--analyze-files', action='store_true', help='Анализ используемых файлов')

    # Новые параметры для парсера
    parser.add_argument('--timer', type=int, help='Время работы парсера в часах')
    parser.add_argument('--windows', type=int, default=1, help='Количество окон браузера (1-10)')
    parser.add_argument('--site', type=str, default='avito', help='Сайт для парсинга (avito)')
    parser.add_argument('--test-parser', action='store_true', help='Тестирование парсера')

    args = parser.parse_args()

    # Логируем запуск системы
    system_logger.info("🚀 Запуск Selibry System v4.0")

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        system_logger.info("Режим отладки включен")

    # Если нет аргументов - показываем интерактивный режим
    if len(sys.argv) == 1:
        show_interactive_menu()

        # Основной цикл меню
        while True:
            try:
                choice = input("\033[1;36mВыберите вариант (0-15): \033[0m").strip()

                # Логируем выбор пользователя
                system_logger.info(f"Пользователь выбрал опцию: {choice}")

                if choice == '0':
                    system_logger.info("Завершение работы системы")
                    print("До свидания!")
                    return

                elif choice == '1':
                    # Полный запуск (сайт + бот + списание)
                    system_logger.info("Запуск полной системы: сайт + бот + списание")
                    if not setup_django_safe():
                        print("Не удалось настроить Django. Выход.")
                        return
                    start_telegram_bot()
                    start_django_server()
                    start_subscription_scheduler()
                    break

                elif choice == '2':
                    # Только сайт + списание
                    system_logger.info("Запуск только Django сайта + списание")
                    if not setup_django_safe():
                        print("Не удалось настроить Django. Выход.")
                        return
                    start_django_server()
                    start_subscription_scheduler()
                    break

                elif choice == '3':
                    # Только бот + списание
                    system_logger.info("Запуск только Telegram бота + списание")
                    if not setup_django_safe():
                        print("Не удалось настроить Django. Выход.")
                        return
                    start_telegram_bot()
                    start_subscription_scheduler()
                    break

                elif choice == '4':
                    # Запуск парсера с параметрами
                    system_logger.info("Запуск парсера с параметрами")
                    print("Настройка параметров парсера:")
                    try:
                        timer = input("⏰  Таймер работы (часы, Enter для бесконечного): ").strip()
                        timer = int(timer) if timer else None

                        windows = input("🖥️  Количество окон (1-10, по умолчанию 1): ").strip()
                        windows = int(windows) if windows else 1

                        # Настраиваем Django если еще не настроен
                        if not setup_django_safe():
                            print("Не удалось настроить Django. Выход.")
                            return

                        # ОБНОВЛЯЕМ НАСТРОЙКИ
                        from apps.parsing.utils.selenium_parser import selenium_parser  # ИЗМЕНЕНО
                        selenium_parser.browser_windows = windows

                        print("Запуск парсера с параметрами:")
                        print(f"   • Таймер: {timer} часов" if timer else "   • Таймер: бесконечный режим")
                        print(f"   • Окна браузера: {windows}")
                        print("=" * 50)

                        # Запускаем парсер и ждем его завершения
                        start_parser_system(
                            timer_hours=timer,
                            browser_windows=windows,
                            site='avito'
                        )

                        # Ждем завершения работы парсера или Ctrl+C
                        try:
                            while True:
                                time.sleep(1)
                        except KeyboardInterrupt:
                            system_logger.info("Остановка системы парсера по запросу пользователя")
                            print("Остановка системы парсера...")
                            selenium_parser.stop()
                            stop_all_processes()
                            print("Парсер остановлен. Возврат в меню...")
                            # После остановки возвращаемся в меню
                            show_interactive_menu()
                            continue

                    except ValueError:
                        system_logger.error("Неверный формат числа при настройке парсера")
                        print("Неверный формат числа")
                        continue

                elif choice == '5':
                    if not setup_django_safe():
                        print("Не удалось настроить Django.")
                        continue
                    show_status()
                    continue

                elif choice == '6':
                    analyze_file_usage()
                    continue

                elif choice == '7':
                    # 🔥 Проверка PostgreSQL
                    system_logger.info("Проверка подключения PostgreSQL")
                    if not setup_django_safe():
                        print("Не удалось настроить Django.")
                        continue
                    check_postgresql_connection_simple()
                    continue

                elif choice == '8':
                    if not setup_django_safe():
                        print("Не удалось настроить Django.")
                        continue
                    start_subscription_scheduler()
                    continue

                elif choice == '9':
                    if not setup_django_safe():
                        print("Не удалось настроить Django.")
                        continue
                    test_subscription_tasks()
                    continue

                elif choice == '10':
                    if not setup_django_safe():
                        print("Не удалось настроить Django.")
                        continue
                    get_scheduler_status()
                    continue

                elif choice == '11':
                    stop_all_processes()
                    continue

                elif choice == '12':
                    clean_cache()
                    continue

                elif choice == '13':
                    run_migrations()
                    continue

                elif choice == '14':
                    create_backup()
                    continue

                elif choice == '15':
                    system_logger.info("Запуск тестирования системы")
                    if not setup_django_safe():
                        print("Не удалось настроить Django.")
                        continue
                    test_components()
                    continue

                else:
                    system_logger.warning(f"Неверный выбор пользователя: {choice}")
                    print("Неверный выбор. Попробуйте снова.")
                    continue

            except KeyboardInterrupt:
                system_logger.info("Завернение работы по запросу пользователя (Ctrl+C)")
                print("До свидания!")
                return
            except Exception as e:
                system_logger.error(f"Ошибка в интерактивном меню: {e}")
                print(f"Ошибка: {e}")
                continue

        # Если выбрали запуск сайта/бота - ждем Ctrl+C
        if choice in ['1', '2', '3', '8']:
            print("=" * 50)
            print("Система запущена! Для остановки нажмите Ctrl+C")
            print("Для возврата в меню нажмите 'm' + Enter")
            print("=" * 50)

            try:
                while True:
                    # Ждем либо Ctrl+C, либо команду 'm' для возврата в меню
                    user_input = input()
                    if user_input.lower() == 'm':
                        system_logger.info("Возврат в главное меню по запросу пользователя")
                        print("Возврат в меню...")
                        stop_all_processes()
                        show_interactive_menu()
                        return
            except KeyboardInterrupt:
                system_logger.info("Остановка системы по запросу пользователя")
                print("Остановка системы...")
                stop_all_processes()

        return

    # 🔥 ОБРАБОТКА НОВОЙ КОМАНДЫ
    if args.analyze_files:
        system_logger.info("Запуск анализа файлов")
        unused_count = analyze_file_usage()
        if unused_count > 0:
            system_logger.warning(f"Найдено {unused_count} возможно неиспользуемых файлов")
            print(f"Найдено {unused_count} возможно неиспользуемых файлов!")
            print("Проверьте отчет в file_usage_report.txt")
        return

    # Валидация параметров парсера
    if args.windows and (args.windows < 1 or args.windows > 10):
        system_logger.error(f"Некорректное количество окон: {args.windows}")
        print("Количество окон должно быть от 1 до 10")
        return

    if args.timer and (args.timer < 1 or args.timer > 24):
        system_logger.error(f"Некорректный таймер: {args.timer}")
        print("Таймер должен быть от 1 до 24 часов")
        return

    # Обработка команд управления системой (выполняются и завершаются)
    if args.stop:
        system_logger.info("Остановка всех процессов")
        stop_all_processes()
        return

    if args.status:
        system_logger.info("Показать статус процессов")
        show_status()
        return

    if args.clean:
        system_logger.info("Очистка кеша")
        clean_cache()
        return

    if args.migrate:
        system_logger.info("Применение миграций БД")
        run_migrations()
        return

    if args.backup:
        system_logger.info("Создание бэкапа БД")
        create_backup()
        return

    if args.test:
        system_logger.info("Тестирование компонентов системы")
        if not setup_django_safe():
            print("Не удалось настроить Django.")
            return
        test_components()
        return

    if args.test_parser:
        system_logger.info("Тестирование парсера")
        print("Тестирование парсера...")
        if not setup_django_safe():
            print("Не удалось настроить Django.")
            return
        test_parser_system()
        return

    if args.restart:
        system_logger.info("Перезапуск системы")
        print("Перезапуск системы...")
        stop_all_processes()
        time.sleep(2)

    # 🔥 ПРИОРИТЕТ 1: Если указаны параметры парсера, запускаем ТОЛЬКО парсер
    if args.timer or args.windows > 1 or args.site != 'avito':
        system_logger.info(
            f"Запуск парсера с параметрами: timer={args.timer}, windows={args.windows}, site={args.site}")
        print("Режим: Запуск только системы парсера")

        # Настраиваем Django если еще не настроен
        if not setup_django_safe():
            print("Не удалось настроить Django.")
            return

        # ОБНОВЛЯЕМ НАСТРОКИ ПЕРЕД ЗАПУСКОМ
        from apps.parsing.utils.selenium_parser import selenium_parser  # ИЗМЕНЕНО
        if args.timer:
            system_logger.info(f"Установлен таймер на {args.timer} часов")
            print(f"Установлен таймер на {args.timer} часов")
        if args.windows:
            selenium_parser.browser_windows = args.windows
            system_logger.info(f"Установлено окон браузера: {args.windows}")
            print(f"Установлено окон браузера: {args.windows}")

        start_parser_system(
            timer_hours=args.timer,
            browser_windows=args.windows,
            site=args.site
        )

        # Ждем завершения работы парсера
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            system_logger.info("Остановка парсера по запросу пользователя")
            print("Остановка системы парсера...")
            selenium_parser.stop()
            stop_all_processes()
        return

    # 🔥 ПРИОРИТЕТ 2: Запуск веб-сайта и/или бота (стандартный режим)

    # Определяем режим запуска
    run_web = args.web or not (args.web or args.bot)
    run_bot = args.bot or not (args.web or args.bot)

    if args.web and not args.bot:
        system_logger.info("Режим: Только Django сайт")
        print("Режим: Только Django сайт")
    elif args.bot and not args.web:
        system_logger.info("Режим: Только Telegram бот")
        print("Режим: Только Telegram бот")
    else:
        system_logger.info("Режим: Полная система (сайт + бот)")
        print("Режим: Полная система (сайт + бot)")

    print("=" * 60)

    # Настраиваем Django
    if not setup_django_safe():
        print("Не удалось настроить Django. Выход.")
        return

    # Запуск компонентов
    bot_started = False
    web_started = False

    if run_bot:
        bot_started = start_telegram_bot()

    if run_web:
        web_started = start_django_server()

    # Вывод итогового статуса
    print("=" * 60)
    print("Система запущена!")
    print("Итоговый статус:")

    if run_web and web_started:
        print("   • Django сервер:  http://127.0.0.1:8000")
        print("   • Админка:        http://127.0.0.1:8000/admin")

    if run_bot and bot_started:
        print("   • Telegram бот:   Активен и готов к работе")

    print("Для остановки нажмите Ctrl+C")
    print("=" * 60)

    try:
        # Бесконечный цикл для поддержания работы
        if run_web or run_bot:
            while True:
                time.sleep(1)
        else:
            print("Для запуска системы используйте команды выше")

    except KeyboardInterrupt:
        system_logger.info("Остановка системы по запросу пользователя")
        print("Остановка системы...")
        stop_all_processes()
        print("До свидания!")


if __name__ == "__main__":
    main()