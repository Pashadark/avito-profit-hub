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
import math

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
# ДИНАМИЧЕСКИЙ ПРОГРЕСС-БАР С ПРАВИЛЬНЫМ ВЫВОДОМ
# ============================================

class DynamicProgressBar:
    """Динамический прогресс-бар с желтыми кубиками для одной строки"""

    def __init__(self, total=100, width=50, title="Прогресс", color="yellow"):
        self.total = total
        self.width = width
        self.title = title
        self.current = 0
        self.color = color
        self.start_time = None
        self.last_update = 0
        self.finished = False
        self._last_line_length = 0

        # Коды цветов для терминала
        self.colors = {
            "yellow": "\033[93m",
            "green": "\033[92m",
            "red": "\033[91m",
            "blue": "\033[94m",
            "cyan": "\033[96m",
            "magenta": "\033[95m",
            "reset": "\033[0m"
        }

    def _get_color(self):
        """Получить цветовой код"""
        return self.colors.get(self.color, self.colors["yellow"])

    def _clear_line(self):
        """Очистить текущую строку в терминале"""
        sys.stdout.write('\r' + ' ' * self._last_line_length + '\r')
        sys.stdout.flush()
        self._last_line_length = 0

    def _write_progress(self, line):
        """Записать прогресс-бар с очисткой предыдущей строки"""
        self._clear_line()
        sys.stdout.write(line)
        sys.stdout.flush()
        self._last_line_length = len(line) - line.count('\033') * 9  # Учитываем escape-коды

    def start(self):
        """Начать отсчет времени"""
        self.start_time = time.time()
        self.current = 0
        self.finished = False
        self._draw(0)

    def update(self, value=None, step=None):
        """Обновить прогресс-бар"""
        current_time = time.time()

        # Защита от слишком частых обновлений (максимум 20 FPS)
        if current_time - self.last_update < 0.05:
            return

        self.last_update = current_time

        if value is not None:
            self.current = min(max(value, 0), self.total)
        elif step is not None:
            self.current = min(max(self.current + step, 0), self.total)

        self._draw(self.current)

    def increment(self, step=1):
        """Увеличить прогресс на шаг"""
        self.update(step=step)

    def _draw(self, current):
        """Отрисовать прогресс-бар в одной строке"""
        if self.finished:
            return

        # Вычисляем проценты
        percent = (current / self.total) * 100

        # Вычисляем заполненные и пустые позиции
        filled_width = int(self.width * current // self.total)
        empty_width = self.width - filled_width

        # Создаем строку прогресса с желтыми кубиками
        filled_chars = '█' * filled_width
        empty_chars = '░' * empty_width

        # Время выполнения
        elapsed = time.time() - self.start_time if self.start_time else 0

        # ETA (ожидаемое время завершения)
        eta = None
        if current > 0 and elapsed > 0:
            speed = current / elapsed
            if speed > 0:
                eta = (self.total - current) / speed

        # Форматируем время
        elapsed_str = self._format_time(elapsed)
        eta_str = self._format_time(eta) if eta else "--:--"

        # Собираем строку прогресс-бара
        color_code = self._get_color()
        reset_code = self.colors["reset"]

        # Динамическая строка в одной строке с возвратом каретки
        progress_line = f"\r{color_code}🎯 {self.title}: [{filled_chars}{empty_chars}] {percent:6.2f}% "
        progress_line += f"({current}/{self.total}) ⏱️ {elapsed_str} ⏳ ETA: {eta_str}{reset_code}"

        self._write_progress(progress_line)

        # Если достигли 100%, добавляем перенос строки
        if current >= self.total and not self.finished:
            self.finished = True
            sys.stdout.write("\n")
            sys.stdout.flush()

    def _format_time(self, seconds):
        """Форматировать время в MM:SS"""
        if seconds is None or seconds < 0:
            return "--:--"

        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def finish(self, message="✅ Завершено"):
        """Завершить прогресс-бар"""
        if not self.finished:
            self.update(self.total)
            self._clear_line()
            color_code = self._get_color()
            reset_code = self.colors["reset"]
            print(f"{color_code}{message}{reset_code}")
            self.finished = True

    def clear(self):
        """Очистить прогресс-бар"""
        self._clear_line()

    def __enter__(self):
        """Контекстный менеджер"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершение контекстного менеджера"""
        if exc_type is None:
            self.finish()
        else:
            self._clear_line()
            color_code = self.colors["red"]
            reset_code = self.colors["reset"]
            print(f"{color_code}❌ Прервано: {exc_val}{reset_code}")


# ============================================
# КАСТОМНЫЙ ХЕНДЛЕР ДЛЯ ЛОГГИНГА
# ============================================

class ProgressAwareLogHandler(logging.Handler):
    """Обработчик логов, который работает с прогресс-баром"""

    def __init__(self):
        super().__init__()
        self.formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
                                           datefmt='%H:%M:%S')
        self.progress_bar = None

    def set_progress_bar(self, progress_bar):
        """Установить ссылку на текущий прогресс-бар"""
        self.progress_bar = progress_bar

    def emit(self, record):
        """Вывод лога с учетом прогресс-бара"""
        try:
            # Форматируем сообщение
            msg = self.format(record)

            # Если есть активный прогресс-бар, очищаем его строку перед выводом лога
            if self.progress_bar and not self.progress_bar.finished:
                self.progress_bar.clear()

            # Выводим лог
            print(msg)

            # Если есть активный прогресс-бар, перерисовываем его после лога
            if self.progress_bar and not self.progress_bar.finished:
                self.progress_bar._draw(self.progress_bar.current)

        except Exception:
            self.handleError(record)


# ============================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================

INITIALIZED_MODULES = {
    'django': False,
    'parsing': False,
    'bot': False,
    'logging': False
}

# Создаем кастомный обработчик логов
progress_handler = ProgressAwareLogHandler()
progress_handler.setLevel(logging.INFO)

# Настраиваем корневой логгер
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(progress_handler)

# Создаем логгеры для системы
system_logger = logging.getLogger('system.run')
bot_logger = logging.getLogger('apps.bot')
django_logger = logging.getLogger('django')
scheduler_logger = logging.getLogger('scheduler')
console_logger = logging.getLogger('console.capture')

# Глобальный прогресс-бар для системы
system_progress = DynamicProgressBar(total=100, width=40, title="Система ProfitHub", color="yellow")

# Связываем обработчик с прогресс-баром
progress_handler.set_progress_bar(system_progress)


# ============================================
# ФУНКЦИЯ ДЛЯ ОТЛОЖЕННОГО ИМПОРТА BACKUP_MANAGER
# ============================================

def get_backup_manager():
    """Ленивая загрузка backup_manager после настройки Django"""
    try:
        from apps.core.utils.backup_manager import backup_manager
        return backup_manager
    except Exception as e:
        system_logger.error(f"Ошибка загрузки backup_manager: {e}")
        return None


# Функции для удобства с прогресс-баром
def print_success(text):
    """Вывод успешного сообщения с прогресс-баром"""
    system_progress.update(step=5)  # Прогресс при успехе
    system_logger.info(f"✅ {text}")


def print_error(text):
    """Вывод сообщения об ошибке"""
    system_progress.update(step=2)  # Небольшой прогресс даже при ошибке
    system_logger.error(f"❌ {text}")


def print_warning(text):
    """Вывод предупреждения"""
    system_progress.update(step=3)
    system_logger.warning(f"⚠️ {text}")


def print_info(text):
    """Вывод информационного сообщения"""
    system_progress.update(step=1)
    system_logger.info(f"ℹ️ {text}")


def print_banner(text):
    """Вывод баннера"""
    # Для баннеров временно отключаем прогресс-бар
    if system_progress and not system_progress.finished:
        system_progress.clear()
    print(f"\033[1;36m{text}\033[0m")
    # Перерисовываем прогресс-бар если он активен
    if system_progress and not system_progress.finished:
        system_progress._draw(system_progress.current)


def print_progress(message, progress_step=1):
    """Вывод прогресса с обновлением прогресс-бара"""
    system_progress.update(step=progress_step)
    system_logger.info(f"🔄 {message}")


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
        self.progress = DynamicProgressBar(total=100, width=40, title="Анализ файлов", color="cyan")

    def scan_all_files(self):
        """Сканирует все файлы в проекте"""
        print_info("Сканирование файлов проекта...")
        self.progress.start()

        all_files = list(self.project_root.rglob('*'))
        total_files = len(all_files)

        for i, file_path in enumerate(all_files):
            if file_path.is_file():
                # Пропускаем игнорируемые директории и файлы
                if any(ignored in str(file_path) for ignored in self.ignored_dirs):
                    continue
                if file_path.suffix in self.ignored_extensions:
                    continue

                self.all_files.add(str(file_path.relative_to(self.project_root)))

            # Обновляем прогресс каждые 10 файлов
            if i % 10 == 0:
                progress_percent = (i / total_files) * 100
                self.progress.update(progress_percent)

        self.progress.finish("✅ Сканирование завершено")
        print_success(f"Найдено файлов: {len(self.all_files)}")
        return self.all_files

    def analyze_project_dependencies(self):
        """Анализ зависимостей проекта через импорты"""
        print_info("Анализ зависимостей проекта...")
        self.progress.start()

        # Критически важные файлы, которые всегда используются
        critical_files = {
            # Core Django
            'manage.py', 'run.py',
            'apps/core/__init__.py', 'apps/core/settings.py', 'apps/core/urls.py',
            'apps/core/wsgi.py', 'apps/core/asgi.py', 'apps/core/logging_config.py',

            # Bot
            'apps/bot/__init__.py', 'apps/bot/bot.py', 'apps/bot/apps.py',
            'apps/bot/handlers/__init__.py', 'apps/bot/handlers/main_handlers.py',
            'apps/bot/services/__init__.py',

            # Parsing
            'apps/parsing/__init__.py', 'apps/parsing/apps.py',
            'apps/parsing/utils/__init__.py', 'apps.parsing.utils.selenium_parser.py',
            'apps/parsing/core/__init__.py', 'apps/parsing/core/settings_manager.py',

            # Website
            'apps/website/__init__.py', 'apps/website/apps.py', 'apps/website/models.py',
            'apps/website/views.py', 'apps/website/admin.py', 'apps/website/urls.py',
            'apps/website/forms.py', 'apps/website/middleware.py',
            'apps/website/context_processors.py',
            'apps/website/console_capture.py', 'apps/website/console_manager.py',
            'apps/website/database_replication.py', 'apps/website/log_viewer.py',

            # Management commands
            'apps/website/management/__init__.py', 'apps/website/management/commands/__init__.py',
            'apps/website/management/commands/daily_backup.py',
            'apps/website/management/commands/daily_subscription_charge.py',
            'apps/website/management/commands/deduct_daily_payments.py',
            'apps/website/management/commands/init_subscriptions.py',
            'apps/website/management/commands/test_logging.py',

            # Config files
            'requirements.txt', 'pyproject.toml', 'custom_user_agents.py'
        }

        # Добавляем критические файлы
        total_files = len(critical_files)
        for i, file in enumerate(critical_files):
            if (self.project_root / file).exists():
                self.used_files.add(file)
            progress_percent = (i / total_files) * 100
            self.progress.update(progress_percent)

        self.progress.finish("✅ Анализ зависимостей завершен")
        return self.used_files

    def analyze_django_apps(self):
        """Анализ Django приложений и их файлов"""
        try:
            from django.apps import apps

            print_info("Анализ Django приложений...")
            self.progress.start()

            app_configs = list(apps.get_app_configs())
            total_apps = len(app_configs)

            for app_idx, app_config in enumerate(app_configs):
                app_path = Path(app_config.path)
                if self.project_root in app_path.parents:
                    rel_path = app_path.relative_to(self.project_root)

                    # Добавляем все Python файлы приложения
                    py_files = list(app_path.rglob('*.py'))
                    total_py_files = len(py_files)

                    for file_idx, py_file in enumerate(py_files):
                        if py_file.is_file():
                            file_rel_path = py_file.relative_to(self.project_root)
                            self.used_files.add(str(file_rel_path))

                        # Обновляем прогресс
                        file_progress = (file_idx / total_py_files) * 100
                        app_progress = (app_idx / total_apps) * 100
                        total_progress = (app_progress + file_progress) / 2
                        self.progress.update(total_progress)

                # Прогресс между приложениями
                self.progress.update(((app_idx + 1) / total_apps) * 100)

            self.progress.finish("✅ Анализ Django приложений завершен")
            print_success(f"Проанализировано Django приложений: {total_apps}")

        except Exception as e:
            print_warning(f"Ошибка анализа Django приложений: {e}")

    def analyze_imports_recursively(self, start_module):
        """Рекурсивный анализ импортов из начального модуля"""
        try:
            visited = set()
            modules_to_analyze = [start_module]
            self.progress.start()

            total_analyzed = 0

            while modules_to_analyze:
                module_name = modules_to_analyze.pop(0)

                if module_name in visited:
                    continue

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
                                    if imp not in visited and imp not in modules_to_analyze:
                                        modules_to_analyze.append(imp)
                                        total_analyzed += 1

                                        # Обновляем прогресс
                                        progress = (len(visited) / (len(visited) + len(modules_to_analyze))) * 100
                                        self.progress.update(progress)

                        except Exception as e:
                            print_warning(f"Ошибка анализа файла {module.__file__}: {e}")

                except Exception as e:
                    print_warning(f"Ошибка анализа модуля {module_name}: {e}")

                # Обновляем прогресс
                if total_analyzed > 0:
                    progress = (len(visited) / total_analyzed) * 100
                    self.progress.update(progress)

            self.progress.finish("✅ Рекурсивный анализ импортов завершен")

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
# ОСНОВНЫЕ ФУНКЦИИ СИСТЕМЫ С ПРОГРЕСС-БАРОМ
# ============================================

def setup_django_safe():
    """Безопасная настройка Django без повторной инициализации с прогресс-баром"""
    global INITIALIZED_MODULES
    global system_progress

    if INITIALIZED_MODULES['django']:
        print_info("Django уже настроен ранее")
        system_progress.update(step=10)  # Быстрый прогресс если уже настроен
        return True

    try:
        system_progress.update(step=5)
        print_progress("Настройка Django...", progress_step=5)

        # Проверяем, не настроен ли уже Django
        from django.conf import settings
        if settings.configured:
            print_info("Django уже настроен системой")
            INITIALIZED_MODULES['django'] = True
            system_progress.update(step=10)

            # Инициализируем парсер после настройки Django (ОДИН РАЗ)
            if not INITIALIZED_MODULES['parsing']:
                initialize_parser_after_django()
            return True

        # Устанавливаем настройки Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')
        print_info(f"DJANGO_SETTINGS_MODULE = {os.environ.get('DJANGO_SETTINGS_MODULE')}")
        system_progress.update(step=5)

        # Настраиваем Django только если еще не настроен
        import django
        django.setup()

        system_progress.update(step=10)
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
    global system_progress

    if INITIALIZED_MODULES['parsing']:
        print_info("Парсер уже инициализирован ранее")
        system_progress.update(step=5)
        return

    try:
        system_progress.update(step=3)
        print_progress("Инициализация парсера...", progress_step=3)

        # 🔥 ИСПРАВЛЕНИЕ: Используем get_selenium_parser() вместо initialize_parser
        from apps.parsing import get_selenium_parser
        parser = get_selenium_parser()

        if parser:
            # Инициализируем настройки Django
            parser.initialize_with_django()
            INITIALIZED_MODULES['parsing'] = True
            system_progress.update(step=7)
            print_success("Парсер инициализирован с настройками Django")
        else:
            print_warning("Не удалось создать парсер")
    except Exception as e:
        print_warning(f"Ошибка инициализации парсера: {e}")


def start_subscription_scheduler():
    """Запуск планировщика подписок (замена Celery) с прогресс-баром"""
    print_info("Запуск системы автоматического списания...")

    # Временно отключаем прогресс-бар для вывода логов планировщика
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Система списания", color="green") as progress:
        # Устанавливаем этот прогресс-бар для обработчика логов
        progress_handler.set_progress_bar(progress)

        progress.update(10)

        try:
            from apps.website.scheduler import scheduler

            if scheduler.is_running:
                progress.update(50)
                print_warning("⚠️ Система списания уже запущена")
                progress.finish("✅ Уже запущено")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True

            progress.update(30)
            print_progress("Запуск планировщика...", progress_step=20)

            success = scheduler.start()
            progress.update(80)

            if success:
                progress.finish("✅ Система списания запущена!")
                print_info("🤖 Умное списание будет выполняться ежедневно в 06:00")
                print_info("🔧 Проверка здоровья подписок в 00:30")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True
            else:
                print_error("❌ Не удалось запустить систему списания")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

        except Exception as e:
            print_error(f"❌ Ошибка запуска системы списания: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def stop_subscription_scheduler():
    """Остановка планировщика подписок с прогресс-баром"""
    print_info("Остановка системы автоматического списания...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Остановка списания", color="red") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(20)

        try:
            # ✅ Проверяем, настроен ли Django перед импортом
            from django.conf import settings
            if not settings.configured:
                progress.update(60)
                print_warning("⚠️ Django не настроен, пропускаем остановку планировщика")
                progress.finish("✅ Пропущено")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True

            progress.update(40)
            from apps.website.scheduler import scheduler

            if not scheduler.is_running:
                progress.update(80)
                print_warning("⚠️ Система списания уже остановлена")
                progress.finish("✅ Уже остановлено")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True

            progress.update(60)
            success = scheduler.stop()
            progress.update(90)

            if success:
                progress.finish("✅ Система списания остановлена!")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True
            else:
                print_error("❌ Не удалось остановить систему списания")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

        except Exception as e:
            print_warning(f"⚠️ Ошибка остановки системы списания: {e}")
            progress.finish("⚠️ Завершено с ошибками")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True


def test_subscription_tasks():
    """Тестирование задач списания (замена тестирования Celery) с прогресс-баром"""
    print_info("Тестирование системы автоматического списания...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Тестирование списания", color="blue") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            if not setup_django_safe():
                progress.update(30)
                print_error("Не удалось настроить Django")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

            progress.update(20)
            from apps.website.scheduler import scheduler
            from django.contrib.auth.models import User
            from apps.website.models import UserProfile

            # Проверим текущий баланс
            progress.update(30)
            admin_user = User.objects.get(username='admin')
            profile = UserProfile.objects.get(user=admin_user)
            print_info(f"💰 Текущий баланс: {profile.balance}₽")

            # Тестируем списание
            progress.update(40)
            print_info("🔄 Запуск тестового списания...")
            result1 = scheduler.run_daily_charge()
            progress.update(60)

            if result1:
                print_success("✅ Тестовое списание завершено успешно")
            else:
                print_warning("⚠️ Тестовое списание завершено с проблемами")

            # Тестируем проверку здоровья
            progress.update(70)
            print_info("🔄 Запуск проверки здоровья...")
            result2 = scheduler.run_health_check()
            progress.update(80)

            if result2:
                print_success("✅ Проверка здоровья завершена успешно")
            else:
                print_warning("⚠️ Проверка здоровья завершена с проблемами")

            # Проверим баланс после теста
            progress.update(90)
            profile.refresh_from_db()
            print_success(f"💰 Баланс после теста: {profile.balance}₽")

            progress.finish("✅ Тестирование завершено")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"❌ Ошибка тестирования: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def get_scheduler_status():
    """Получить статус планировщика с прогресс-баром"""
    print_info("=== СТАТУС СИСТЕМЫ АВТОМАТИЧЕСКОГО СПИСАНИЯ ===")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Проверка статуса", color="cyan") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(30)

        try:
            from apps.website.scheduler import scheduler
            progress.update(60)
            status = scheduler.get_status()
            progress.update(90)

            print_info(f"Статус: {status['status']}")
            print_info(f"Заданий в расписании: {status['jobs_count']}")
            print_info(f"Следующий запуск: {status['next_run']}")

            if status['running']:
                progress.finish("✅ Система работает нормально")
            else:
                progress.finish("⚠️ Система остановлена")

            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"❌ Ошибка получения статуса: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def start_telegram_bot():
    """Запуск Telegram бота в отдельном процессе с прогресс-баром"""
    global INITIALIZED_MODULES
    global system_progress

    if INITIALIZED_MODULES['bot']:
        print_info("🤖 Telegram бот уже запущен ранее")
        system_progress.update(step=10)
        return True

    print_info("🤖 Запуск Telegram бота...")

    # Временно отключаем прогресс-бар для вывода логов бота
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Telegram бот", color="green") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            progress.update(20)
            kill_existing_bot_processes()
            progress.update(40)

            # Запускаем бота в отдельном процессе
            def run_bot():
                try:
                    # ✅ ИМПОРТИРУЕМ НОВЫЙ МОДУЛЬ БОТА
                    from apps.bot.bot import main as run_new_bot
                    INITIALIZED_MODULES['bot'] = True

                    # ✅ ЗАПУСКАЕМ НОВЫЙ БОТ
                    print("🚀 Запускаю новый ProfitHub бота...")
                    success = run_new_bot()

                    if success:
                        bot_logger.info("✅ Новый бот запущен успешно")
                    else:
                        bot_logger.error("❌ Не удалось запустить новый бот")

                except Exception as e:
                    bot_logger.error(f"❌ Ошибка запуска бота: {e}")
                    import traceback
                    traceback.print_exc()
                    INITIALIZED_MODULES['bot'] = False

            progress.update(60)
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            progress.update(80)

            time.sleep(3)  # Даем время боту запуститься
            progress.update(95)

            bot_logger.info("✅ Telegram бот запущен успешно")
            progress.finish("✅ Бот запущен")

            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка запуска бота: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def start_parser_system(timer_hours=None, browser_windows=1, site='avito'):
    """Запуск системы парсера с новыми параметрами и прогресс-баром"""
    print_info("Запуск системы парсера с параметрами:")
    print_info(f"   • Таймер: {timer_hours} часов" if timer_hours else "   • Таймер: не установлен")
    print_info(f"   • Окна браузера: {browser_windows}")
    print_info(f"   • Сайт: {site}")

    # Временно отключаем прогресс-бар для вывода баннера
    progress_handler.set_progress_bar(None)
    print_banner("=" * 50)

    with DynamicProgressBar(total=100, width=40, title="Система парсера", color="yellow") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            # Настраиваем Django если еще не настроен
            if not INITIALIZED_MODULES['django']:
                progress.update(20)
                setup_django_safe()
                progress.update(30)

            # Запускаем парсер в отдельном процессе
            def run_parser():
                try:
                    # Импортируем внутри потока чтобы избежать циклических импортов
                    from apps.parsing.utils.selenium_parser import selenium_parser
                    progress.update(40)

                    # Создаем новое событийное loop для этого потока
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    progress.update(50)

                    async def async_run():
                        # ЗАМЕНИЛ НА ПРАВИЛЬНЫЙ МЕТОД - check_prices_and_notify
                        progress.update(60)
                        await selenium_parser.check_prices_and_notify()
                        progress.update(80)

                    loop.run_until_complete(async_run())
                    progress.update(90)

                except Exception as e:
                    print_error(f"Ошибка запуска парсера: {e}")
                    import traceback
                    traceback.print_exc()

            progress.update(70)
            parser_thread = threading.Thread(target=run_parser, daemon=True)
            parser_thread.start()
            progress.update(95)

            print_success("Система парсера запущена успешно")
            progress.finish("✅ Парсер запущен")

            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка запуска системы парсера: {e}")
            import traceback
            traceback.print_exc()
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def test_parser_system():
    """Тестирование парсера с демо-режимом и прогресс-баром"""
    print_info("Тестирование системы парсера...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Тестирование парсера", color="blue") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            if not setup_django_safe():
                progress.update(30)
                print_error("Не удалось настроить Django")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

            # Импортируем парсер
            progress.update(40)
            from apps.parsing.utils.selenium_parser import selenium_parser

            print_info("Инициализация парсера...")
            progress.update(60)
            print_success("Парсер загружен успешно")
            print_info(f"Поисковые запросы: {selenium_parser.search_queries}")
            print_info(f"Исключаемые слова: {selenium_parser.exclude_keywords}")
            progress.update(70)

            # Тестируем настройки
            test_settings = {
                'keywords': 'iPhone, MacBook, Видеокарта',
                'exclude_keywords': 'б/у, сломан',
                'min_price': 1000,
                'max_price': 50000
            }

            result = selenium_parser.update_settings(test_settings)
            progress.update(85)

            if result:
                print_success("Настройки успешно обновлены")
            else:
                print_error("Ошибка обновления настроек")

            progress.finish("✅ Тестирование завершено")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка тестирования системы парсера: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def test_components():
    """Тестирование компонентов системы с прогресс-баром"""
    print_info("Тестирование компонентов...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Тестирование системы", color="cyan") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            if not setup_django_safe():
                progress.update(30)
                print_error("Не удалось настроить Django")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

            # Проверяем базовые импорты
            progress.update(20)
            try:
                from django.db import connection
                connection.ensure_connection()
                print_success("База данных подключена")
                progress.update(30)
            except Exception as e:
                print_error(f"Ошибка БД: {e}")

            progress.update(40)
            try:
                from apps.website.models import UserProfile
                user_count = UserProfile.objects.count()
                print_success(f"Модели загружены (пользователей: {user_count})")
                progress.update(50)
            except Exception as e:
                print_warning(f"Ошибка моделей: {e}")

            # ТЕСТИРУЕМ ПАРСЕР
            progress.update(60)
            try:
                from apps.parsing.utils.selenium_parser import SeleniumAvitoParser
                parser = SeleniumAvitoParser()
                print_success(f"Парсер загружен (запросы: {len(parser.search_queries)})")
                progress.update(70)
            except Exception as e:
                print_error(f"Ошибка загрузки парсера: {e}")

            # ТЕСТИРУЕМ МОДУЛИ
            progress.update(80)
            try:
                from apps.parsing.core.settings_manager import SettingsManager
                settings = SettingsManager()
                print_success("Менеджер настроек загружен")
                progress.update(90)
            except Exception as e:
                print_error(f"Ошибка загрузки менеджера настроек: {e}")

            progress.finish("✅ Все компоненты загружены")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка тестирования: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def start_django_server():
    """Запуск Django сервера с доступом по WiFi и прогресс-баром"""
    print_info("Запуск Django сервера...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Django сервер", color="green") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            # Получаем локальный IP адрес автоматически
            def get_local_ip():
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.connect(("8.8.8.8", 80))
                        return s.getsockname()[0]
                except:
                    return "192.168.3.15"  # fallback на ваш IP

            progress.update(20)
            local_ip = get_local_ip()

            print_info(f"Локальный IP: {local_ip}")
            print_info(f"Ссылка для телефона: http://{local_ip}:8000")
            progress.update(40)

            # Запускаем сервер на всех интерфейсах
            server_process = subprocess.Popen([
                sys.executable, 'manage.py', 'runserver',
                f'{local_ip}:8000', '--noreload'
            ])
            progress.update(60)

            # Даем время серверу запуститься
            time.sleep(5)
            progress.update(80)

            # Проверяем, запустился ли сервер
            import requests
            try:
                response = requests.get(f'http://{local_ip}:8000/', timeout=10)
                if response.status_code == 200:
                    progress.update(95)
                    print_success(f"Django сервер запущен на http://{local_ip}:8000")
                    print_info(f"Откройте на телефона: http://{local_ip}:8000")
                    progress.finish("✅ Сервер запущен")
                    # Возвращаем системный прогресс-бар
                    progress_handler.set_progress_bar(system_progress)
                    return True
            except Exception as e:
                progress.update(90)
                print_warning(f"Сервер запускается... Проверьте: http://{local_ip}:8000")
                print_info("Если не открывается, проверьте брандмауэр")
                progress.finish("⚠️ Проверьте подключение")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True

            progress.finish("✅ Запущено")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка запуска Django сервера: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def kill_existing_bot_processes():
    """Безопасная проверка и остановка процессов бота - ИСПРАВЛЕННАЯ с прогресс-баром"""
    print_info("Проверка запущенных процессов...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Очистка процессов", color="red") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            current_pid = os.getpid()
            print_info(f"Текущий PID: {current_pid}")
            progress.update(20)

            processes_found = []
            current_cmdline = ""

            # Сначала получаем наш cmdline
            try:
                current_process = psutil.Process(current_pid)
                current_cmdline = ' '.join(current_process.cmdline()) if current_process.cmdline() else ""
                print_info(f"Наш процесс: {current_cmdline[:80]}...")
                progress.update(30)
            except:
                pass

            # Сканируем процессы
            progress.update(40)
            all_processes = list(psutil.process_iter(['pid', 'name', 'cmdline']))
            total_processes = len(all_processes)

            for i, proc in enumerate(all_processes):
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

                # Обновляем прогресс сканирования
                if i % 10 == 0:
                    scan_progress = 40 + (i / total_processes) * 30
                    progress.update(scan_progress)

            progress.update(70)
            # Останавливаем только найденные конфликтующие процессы
            stopped = []
            total_found = len(processes_found)

            for j, (pid, cmdline) in enumerate(processes_found):
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

                # Обновляем прогресс остановки
                if total_found > 0:
                    stop_progress = 70 + ((j + 1) / total_found) * 25
                    progress.update(stop_progress)

            progress.update(95)
            if stopped:
                print_success(f"✅ Остановлено конфликтующих процессов: {len(stopped)}")
            else:
                print_success("✅ Конфликтующих процессов не найдено")

            progress.finish("✅ Очистка завершена")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_warning(f"⚠️ Ошибка проверки процессов: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True


def stop_all_processes():
    """Остановка всех процессов системы - ИСПРАВЛЕННАЯ с прогресс-баром"""
    global INITIALIZED_MODULES
    global system_progress

    print_info("Остановка всех процессов ProfitHub...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Остановка системы", color="red") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            current_pid = os.getpid()
            print_info(f"Текущий PID: {current_pid}")
            progress.update(20)

            # ПРОСТОЙ СПОСОБ: останавливаем только явно конфликтующие процессы
            processes_to_check = ['bot.py', 'manage.py runserver']
            progress.update(30)

            all_processes = list(psutil.process_iter(['pid', 'name', 'cmdline']))
            total_processes = len(all_processes)
            stopped_count = 0

            progress.update(40)
            for i, proc in enumerate(all_processes):
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
                            stopped_count += 1
                        except:
                            pass

                except:
                    continue

                # Обновляем прогресс
                if i % 10 == 0:
                    scan_progress = 40 + (i / total_processes) * 40
                    progress.update(scan_progress)

            progress.update(85)
            print_success(f"✅ Запрошена остановка {stopped_count} процессов")

            # ✅ Пробуем остановить планировщик
            progress.update(90)
            try:
                stop_subscription_scheduler()
            except:
                print_warning("⚠️ Не удалось остановить планировщик")

            # ✅ Сбрасываем флаги
            progress.update(95)
            for key in INITIALIZED_MODULES:
                INITIALIZED_MODULES[key] = False

            # Сбрасываем системный прогресс
            system_progress = DynamicProgressBar(total=100, width=40, title="Система ProfitHub", color="yellow")

            progress.finish("✅ Система остановлена")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"❌ Ошибка: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True


def clean_cache():
    """Очистка кеша и временных файлов с прогресс-баром"""
    print_info("Очистка кеша...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Очистка кэша", color="blue") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            # Очищаем pycache
            progress.update(20)
            pycache_dirs = []
            for root, dirs, files in os.walk('.'):
                for dir in dirs:
                    if dir == '__pycache__':
                        pycache_dirs.append(os.path.join(root, dir))

            total_dirs = len(pycache_dirs)
            for i, pycache_path in enumerate(pycache_dirs):
                try:
                    import shutil
                    shutil.rmtree(pycache_path, ignore_errors=True)
                except:
                    pass

                # Обновляем прогресс
                dir_progress = 20 + (i / total_dirs) * 40
                progress.update(dir_progress)

            progress.update(70)
            # Очищаем логи
            if os.path.exists('profithub.log'):
                try:
                    with open('profithub.log', 'w') as f:
                        f.write('')
                except:
                    pass

            progress.update(85)
            # Очищаем другие временные файлы
            temp_files = ['.DS_Store', 'Thumbs.db', '*.pyc', '*.log']
            for pattern in temp_files:
                for file in Path('.').rglob(pattern):
                    try:
                        file.unlink()
                    except:
                        pass

            progress.finish("✅ Кэш очищен")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка очистка кеша: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def run_migrations():
    """Применение миграций базы данных с прогресс-баром"""
    print_info("Применение миграций...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Миграции БД", color="green") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        try:
            # Сначала настраиваем Django
            if not setup_django_safe():
                progress.update(30)
                print_error("Не удалось настроить Django")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

            progress.update(40)
            result = subprocess.run(['python', 'manage.py', 'migrate'],
                                    capture_output=True, text=True)
            progress.update(80)

            if result.returncode == 0:
                progress.finish("✅ Миграции применены")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True
            else:
                print_error(f"Ошибка миграций: {result.stderr}")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

        except Exception as e:
            print_error(f"Ошибка выполнения миграций: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


# ============================================
# НОВАЯ ФУНКЦИЯ ДЛЯ BACKUP - ИСПРАВЛЕННАЯ
# ============================================

def backup_system():
    """Новая функция бэкапа с отложенной загрузкой менеджера и прогресс-баром"""
    print_info("🔄 Запуск системы бэкапов...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Система бэкапов", color="yellow") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(10)

        # Настраиваем Django перед созданием бэкапа
        if not setup_django_safe():
            progress.update(30)
            print_error("Не удалось настроить Django для бэкапа")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False

        progress.update(20)
        try:
            # Только теперь импортируем backup_manager
            backup_manager = get_backup_manager()
            if backup_manager is None:
                progress.update(40)
                print_error("Не удалось загрузить backup_manager")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

            progress.update(50)
            result = backup_manager.create_full_backup()
            progress.update(80)

            if result and any(result.values()):
                progress.finish("✅ Бэкап завершен")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return True
            else:
                print_error("❌ Ошибка в системе бэкапов")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False
        except Exception as e:
            print_error(f"❌ Ошибка при создании бэкапа: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def show_status():
    """Показать статус всех процессов с прогресс-баром"""
    print_info("Статус процессов ProfitHub...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Проверка статуса", color="cyan") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(20)

        try:
            # Проверяем Django сервер
            progress.update(30)
            import requests
            try:
                response = requests.get('http://127.0.0.1:8000/', timeout=5)
                web_status = "✅ Работает" if response.status_code == 200 else "❌ Ошибка"
                progress.update(40)
            except:
                web_status = "❌ Не запущен"

            # Проверяем бота
            progress.update(50)
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
            progress.update(60)
            scheduler_status = "❌ Не запущена"
            try:
                from apps.website.scheduler import scheduler
                status = scheduler.get_status()
                scheduler_status = f"✅ {status['status']}" if status['running'] else "❌ Остановлена"
                progress.update(70)
            except:
                scheduler_status = "❌ Ошибка проверки"

            # Статус инициализации
            progress.update(80)
            init_status = []
            for key, value in INITIALIZED_MODULES.items():
                status = "✅" if value else "❌"
                init_status.append(f"{key}: {status}")

            progress.update(90)
            print_info(f"Django сервер: {web_status}")
            print_info(f"Telegram бот:  {bot_status}")
            print_info(f"Система списания: {scheduler_status}")
            print_info("Статус инициализации: " + ", ".join(init_status))
            print_info(f"Время системы: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            progress.finish("✅ Статус проверен")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return True

        except Exception as e:
            print_error(f"Ошибка проверки статуса: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def analyze_file_usage():
    """Анализ использования файлов в проекте с прогресс-баром"""
    print_info("Запуск анализа использования файлов...")

    tracker = FileUsageTracker()

    # Временно отключаем системный прогресс-бар
    progress_handler.set_progress_bar(None)

    # Создаем общий прогресс-бар для всего анализа
    with DynamicProgressBar(total=100, width=40, title="Анализ файлов проекта", color="cyan") as overall_progress:
        progress_handler.set_progress_bar(overall_progress)
        overall_progress.update(10)

        # Сканируем все файлы
        tracker.scan_all_files()
        overall_progress.update(30)

        # Анализируем зависимости проекта
        tracker.analyze_project_dependencies()
        overall_progress.update(50)

        # Запускаем минимальную инициализацию для трекинга
        if setup_django_safe():
            tracker.analyze_django_apps()
            overall_progress.update(70)
            tracker.analyze_imports_recursively('apps.core')
            overall_progress.update(85)
        else:
            overall_progress.update(70)

        # Генерируем отчет
        report = tracker.generate_report()
        # Временно отключаем прогресс-бар для вывода отчета
        progress_handler.set_progress_bar(None)
        print(report)
        progress_handler.set_progress_bar(overall_progress)
        overall_progress.update(95)

        # Сохраняем отчет в файл
        try:
            with open('file_usage_report.txt', 'w', encoding='utf-8') as f:
                f.write(report)
            print_success("Отчет сохранен в file_usage_report.txt")
        except Exception as e:
            print_error(f"Ошибка сохранения отчета: {e}")

        overall_progress.finish("✅ Анализ завершен")
        # Возвращаем системный прогресс-бар
        progress_handler.set_progress_bar(system_progress)

    return len(tracker.get_unused_files())


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def check_postgresql_connection_simple():
    """Простая проверка подключения к PostgreSQL с прогресс-баром"""
    print_info("🔍 Проверка подключения PostgreSQL...")

    # Временно отключаем прогресс-бар для вывода логов
    progress_handler.set_progress_bar(None)

    with DynamicProgressBar(total=100, width=40, title="Проверка PostgreSQL", color="blue") as progress:
        progress_handler.set_progress_bar(progress)
        progress.update(20)

        try:
            if not setup_django_safe():
                progress.update(40)
                print_error("Не удалось настроить Django")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

            progress.update(50)
            from django.db import connection

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]
                    progress.update(80)
                    print_success(f"✅ PostgreSQL подключен: {version[:50]}...")
                    progress.finish("✅ Подключение успешно")
                    # Возвращаем системный прогресс-бар
                    progress_handler.set_progress_bar(system_progress)
                    return True
            except Exception as e:
                progress.update(70)
                print_error(f"❌ Ошибка подключения к PostgreSQL: {e}")
                # Возвращаем системный прогресс-бар
                progress_handler.set_progress_bar(system_progress)
                return False

        except Exception as e:
            print_error(f"❌ Ошибка при проверке PostgreSQL: {e}")
            # Возвращаем системный прогресс-бар
            progress_handler.set_progress_bar(system_progress)
            return False


def create_backup():
    """Функция для бэкапа БД (совместимость)"""
    return backup_system()


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
    # Временно отключаем прогресс-бар для вывода команд
    progress_handler.set_progress_bar(None)
    for line in commands.split('\n'):
        print_banner(line)
    # Возвращаем системный прогресс-бар
    progress_handler.set_progress_bar(system_progress)


def show_interactive_menu():
    """Интерактивное меню выбора режима (чистый вывод без времени)"""

    # Временно отключаем прогресс-бар для вывода меню
    progress_handler.set_progress_bar(None)

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

    # Возвращаем системный прогресс-бар
    progress_handler.set_progress_bar(system_progress)


# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================

def main():
    """Основная функция запуска"""
    global system_progress
    global progress_handler

    # Инициализируем системный прогресс-бар
    system_progress = DynamicProgressBar(total=100, width=40, title="Система ProfitHub", color="yellow")
    progress_handler.set_progress_bar(system_progress)

    # Начинаем прогресс-бар
    system_progress.start()
    system_progress.update(5)

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
        system_progress.update(step=2)

    # Если нет аргументов - показываем интерактивный режим
    if len(sys.argv) == 1:
        system_progress.finish("✅ Система готова")
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
                    system_progress = DynamicProgressBar(total=100, width=40, title="Полный запуск системы",
                                                         color="yellow")
                    progress_handler.set_progress_bar(system_progress)
                    system_progress.start()
                    system_progress.update(10)

                    if not setup_django_safe():
                        system_progress.update(30)
                        print("Не удалось настроить Django. Выход.")
                        return

                    system_progress.update(40)
                    start_telegram_bot()
                    system_progress.update(60)
                    start_django_server()
                    system_progress.update(80)
                    start_subscription_scheduler()
                    system_progress.update(90)
                    system_progress.finish("✅ Система запущена")
                    break

                elif choice == '2':
                    # Только сайт + списание
                    system_logger.info("Запуск только Django сайта + списание")
                    system_progress = DynamicProgressBar(total=100, width=40, title="Запуск сайта", color="green")
                    progress_handler.set_progress_bar(system_progress)
                    system_progress.start()
                    system_progress.update(20)

                    if not setup_django_safe():
                        system_progress.update(40)
                        print("Не удалось настроить Django. Выход.")
                        return

                    system_progress.update(60)
                    start_django_server()
                    system_progress.update(80)
                    start_subscription_scheduler()
                    system_progress.update(95)
                    system_progress.finish("✅ Сайт запущен")
                    break

                elif choice == '3':
                    # Только бот + списание
                    system_logger.info("Запуск только Telegram бота + списание")
                    system_progress = DynamicProgressBar(total=100, width=40, title="Запуск бота", color="blue")
                    progress_handler.set_progress_bar(system_progress)
                    system_progress.start()
                    system_progress.update(20)

                    if not setup_django_safe():
                        system_progress.update(40)
                        print("Не удалось настроить Django. Выход.")
                        return

                    system_progress.update(60)
                    start_telegram_bot()
                    system_progress.update(80)
                    start_subscription_scheduler()
                    system_progress.update(95)
                    system_progress.finish("✅ Бот запущен")
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

                        # ОБНОВЛЯЕМ НАСТРОКИ
                        from apps.parsing.utils.selenium_parser import selenium_parser
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
                    backup_system()
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
        system_progress.update(20)
        system_logger.info("Запуск анализа файлов")
        unused_count = analyze_file_usage()
        system_progress.update(90)

        if unused_count > 0:
            system_logger.warning(f"Найдено {unused_count} возможно неиспользуемых файлов")
            print(f"Найдено {unused_count} возможно неиспользуемых файлов!")
            print("Проверьте отчет в file_usage_report.txt")

        system_progress.finish("✅ Анализ завершен")
        return

    # Валидация параметров парсера
    if args.windows and (args.windows < 1 or args.windows > 10):
        system_progress.update(30)
        system_logger.error(f"Некорректное количество окон: {args.windows}")
        print("Количество окон должно быть от 1 до 10")
        return

    if args.timer and (args.timer < 1 or args.timer > 24):
        system_progress.update(40)
        system_logger.error(f"Некорректный таймер: {args.timer}")
        print("Таймер должен быть от 1 до 24 часов")
        return

    # Обработка команд управления системой (выполняются и завершаются)
    if args.stop:
        system_progress.update(30)
        system_logger.info("Остановка всех процессов")
        stop_all_processes()
        system_progress.finish("✅ Система остановлена")
        return

    if args.status:
        system_progress.update(40)
        system_logger.info("Показать статус процессов")
        show_status()
        system_progress.finish("✅ Статус проверен")
        return

    if args.clean:
        system_progress.update(50)
        system_logger.info("Очистка кеша")
        clean_cache()
        system_progress.finish("✅ Кэш очищен")
        return

    if args.migrate:
        system_progress.update(60)
        system_logger.info("Применение миграций БД")
        run_migrations()
        system_progress.finish("✅ Миграции применены")
        return

    if args.backup:
        system_progress.update(70)
        system_logger.info("Создание бэкапа БД")
        backup_system()
        system_progress.finish("✅ Бэкап создан")
        return

    if args.test:
        system_progress.update(80)
        system_logger.info("Тестирование компонентов системы")
        if not setup_django_safe():
            system_progress.update(90)
            print("Не удалось настроить Django.")
            return
        test_components()
        system_progress.finish("✅ Тестирование завершено")
        return

    if args.test_parser:
        system_progress.update(85)
        system_logger.info("Тестирование парсера")
        print("Тестирование парсера...")
        if not setup_django_safe():
            system_progress.update(90)
            print("Не удалось настроить Django.")
            return
        test_parser_system()
        system_progress.finish("✅ Тестирование парсера завершено")
        return

    if args.restart:
        system_progress.update(90)
        system_logger.info("Перезапуск системы")
        print("Перезапуск системы...")
        stop_all_processes()
        time.sleep(2)

    # 🔥 ПРИОРИТЕТ 1: Если указаны параметры парсера, запускаем ТОЛЬКО парсер
    if args.timer or args.windows > 1 or args.site != 'avito':
        system_progress.update(20)
        system_logger.info(
            f"Запуск парсера с параметрами: timer={args.timer}, windows={args.windows}, site={args.site}")
        print("Режим: Запуск только системы парсера")

        # Настраиваем Django если еще не настроен
        if not setup_django_safe():
            system_progress.update(40)
            print("Не удалось настроить Django.")
            return

        # ОБНОВЛЯЕМ НАСТРОКИ ПЕРЕД ЗАПУСКОМ
        from apps.parsing.utils.selenium_parser import selenium_parser
        if args.timer:
            system_progress.update(60)
            system_logger.info(f"Установлен таймер на {args.timer} часов")
            print(f"Установлен таймер на {args.timer} часов")
        if args.windows:
            selenium_parser.browser_windows = args.windows
            system_progress.update(70)
            system_logger.info(f"Установлено окон браузера: {args.windows}")
            print(f"Установлено окон браузера: {args.windows}")

        system_progress.update(80)
        start_parser_system(
            timer_hours=args.timer,
            browser_windows=args.windows,
            site=args.site
        )
        system_progress.update(90)

        # Ждем завершения работы парсера
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            system_progress.update(95)
            system_logger.info("Остановка парсера по запросу пользователя")
            print("Остановка системы парсера...")
            selenium_parser.stop()
            stop_all_processes()

        system_progress.finish("✅ Парсер завершен")
        return

    # 🔥 ПРИОРИТЕТ 2: Запуск веб-сайта и/или бота (стандартный режим)

    # Определяем режим запуска
    run_web = args.web or not (args.web or args.bot)
    run_bot = args.bot or not (args.web or args.bot)

    if args.web and not args.bot:
        system_progress.update(30)
        system_logger.info("Режим: Только Django сайт")
        print("Режим: Только Django сайт")
    elif args.bot and not args.web:
        system_progress.update(40)
        system_logger.info("Режим: Только Telegram бот")
        print("Режим: Только Telegram бот")
    else:
        system_progress.update(50)
        system_logger.info("Режим: Полная система (сайт + бот)")
        print("Режим: Полная система (сайт + бot)")

    print("=" * 60)

    # Настраиваем Django
    if not setup_django_safe():
        system_progress.update(60)
        print("Не удалось настроить Django. Выход.")
        return

    # Запуск компонентов
    bot_started = False
    web_started = False

    if run_bot:
        system_progress.update(70)
        bot_started = start_telegram_bot()

    if run_web:
        system_progress.update(80)
        web_started = start_django_server()

    # Вывод итогового статуса
    system_progress.update(90)
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
            system_progress.finish("✅ Система запущена")
            while True:
                time.sleep(1)
        else:
            system_progress.finish("✅ Команда выполнена")
            print("Для запуска системы используйте команды выше")

    except KeyboardInterrupt:
        system_logger.info("Остановка системы по запросу пользователя")
        print("Остановка системы...")
        stop_all_processes()
        print("До свидания!")


if __name__ == "__main__":
    main()