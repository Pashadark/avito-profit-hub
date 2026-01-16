import os
import re
import threading
import time
from datetime import datetime
from django.conf import settings
import logging
from .console_capture import console_capturer


class LogViewer:
    def __init__(self):
        self.log_files = self.find_log_files()
        self.last_positions = {}
        self.update_interval = 2
        self.is_monitoring = False
        self.console_history = []
        self.max_history_lines = 500  # Увеличиваем лимит

        # Запускаем перехват консоли
        console_capturer.start_capture()

        # Настраиваем логирование Django для перехвата
        self.setup_log_capture()

    def setup_log_capture(self):
        """Настраивает перехват логов Django"""

        class LogHandler(logging.Handler):
            def __init__(self, log_viewer):
                super().__init__()
                self.log_viewer = log_viewer
                self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

            def emit(self, record):
                try:
                    message = self.format(record)
                    self.log_viewer.add_to_history(message, record.levelname)
                except:
                    pass

        # Создаем handler и добавляем его к root logger
        handler = LogHandler(self)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def add_to_history(self, message, level='INFO'):
        """Добавляет сообщение в историю"""
        colored_message = self.format_log_line(message, level)
        with threading.Lock():
            self.console_history.append(colored_message)

            # Ограничиваем размер истории
            if len(self.console_history) > self.max_history_lines:
                self.console_history = self.console_history[-self.max_history_lines:]

    def find_log_files(self):
        """Находит все log файлы в проекте"""
        log_files = []
        project_root = settings.BASE_DIR

        # Стандартные пути для логов
        possible_paths = [
            os.path.join(project_root, 'logs/apps/debug.log'),
            os.path.join(project_root, 'logs/django/django.log'),
            os.path.join(project_root, 'logs/parsing/parser.log'),
            os.path.join(project_root, 'logs/bot/bot.log'),
            os.path.join(project_root, 'logs/apps/debug.log'),
            os.path.join(project_root, 'logs/django/django.log'),
            os.path.join(project_root, 'logs/apps/application.log'),
        ]

        for log_path in possible_paths:
            if os.path.exists(log_path):
                log_files.append(log_path)

        # Также ищем любые .log файлы в проекте
        for root, dirs, files in os.walk(project_root):
            for file in files:
                if file.endswith('.log'):
                    full_path = os.path.join(root, file)
                    if full_path not in log_files:
                        log_files.append(full_path)

        return log_files

    def read_logs(self):
        """Читает новые записи из всех log файлов"""
        all_lines = []

        for log_file in self.log_files:
            try:
                if not os.path.exists(log_file):
                    continue

                current_size = os.path.getsize(log_file)

                if log_file not in self.last_positions:
                    # При первом чтении читаем только последние 50 строк
                    self.last_positions[log_file] = self.get_file_position_for_tail(log_file, 50)

                if current_size < self.last_positions[log_file]:
                    self.last_positions[log_file] = 0

                if current_size > self.last_positions[log_file]:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_positions[log_file])
                        new_lines = f.readlines()
                        for line in new_lines:
                            all_lines.append((line, 'FILE'))
                        self.last_positions[log_file] = f.tell()

            except Exception as e:
                add_to_console(f"Ошибка чтения лога {log_file}: {e}")
                continue

        return all_lines

    def get_file_position_for_tail(self, file_path, lines_count=50):
        """Находит позицию в файле для чтения последних lines_count строк"""
        try:
            with open(file_path, 'rb') as f:
                # Перемещаемся в конец файла
                f.seek(0, 2)
                file_size = f.tell()

                # Читаем файл с конца
                buffer_size = 4096
                position = file_size
                lines_found = 0
                buffer = b''

                while position > 0 and lines_found < lines_count:
                    # Определяем размер следующего блока для чтения
                    if position - buffer_size < 0:
                        buffer_size = position
                        position = 0
                    else:
                        position -= buffer_size

                    f.seek(position)
                    buffer = f.read(buffer_size) + buffer

                    # Считаем переводы строк
                    lines_found = buffer.count(b'\n')

                # Находим начало нужной позиции
                if lines_found >= lines_count:
                    # Находим начало n-й строки с конца
                    lines = buffer.split(b'\n')
                    start_pos = len(b'\n'.join(lines[-(lines_count + 1):]))
                    return file_size - start_pos
                else:
                    return 0

        except Exception as e:
            add_to_console(f"Ошибка определения позиции файла: {e}")
            return 0

    def get_console_output(self):
        """Получает вывод консоли из всех источников"""
        try:
            all_lines = []

            # 1. Получаем перехваченный вывод консоли
            console_lines = console_capturer.get_captured_output()
            for line in console_lines:
                if line.strip():
                    formatted = self.format_log_line(line.strip(), 'INFO')
                    if formatted:
                        all_lines.append(formatted)

            # 2. Получаем логи из файлов
            file_lines = self.read_logs()
            for line, source in file_lines:
                if line.strip():
                    formatted = self.format_log_line(line.strip(), self.get_log_level(line))
                    if formatted:
                        all_lines.append(formatted)

            # 3. Добавляем историю из памяти
            with threading.Lock():
                all_lines.extend(self.console_history[-100:])

            # Уникальные строки (избегаем дублирования)
            unique_lines = []
            seen_lines = set()

            for line in all_lines:
                # Извлекаем чистый текст без HTML для проверки уникальности
                clean_text = re.sub(r'<[^>]+>', '', line)
                if clean_text not in seen_lines and len(clean_text) > 5:  # Игнорируем очень короткие строки
                    seen_lines.add(clean_text)
                    unique_lines.append(line)

            # Если ничего нет, показываем информационное сообщение
            if not unique_lines:
                return self.get_info_message()

            return unique_lines[-100:]  # Последние 100 строк

        except Exception as e:
            return [f'<span style="color: #ff6b6b;">❌ Ошибка получения логов: {str(e)}</span>']

    def get_log_level(self, line):
        """Определяет уровень лога по строке"""
        line_lower = line.lower()
        if any(word in line_lower for word in ['error', 'failed', 'exception', 'ошибка', 'fallback']):
            return 'ERROR'
        elif any(word in line_lower for word in ['warning', 'предупреждение', '⚠', 'debug']):
            return 'WARNING'
        elif any(word in line_lower for word in ['success', 'успех', 'complete', '✅', 'загружен', 'сохранен']):
            return 'SUCCESS'
        elif any(word in line_lower for word in ['info', 'инфо', '🔍', '📨', '🌐']):
            return 'INFO'
        else:
            return 'INFO'

    def get_info_message(self):
        """Возвращает информационное сообщение"""
        current_time = datetime.now().strftime("%H:%M:%S")
        return [
            f'<span style="color: #339af0;">[{current_time}] 🌐 Система мониторинга запущена</span>',
            f'<span style="color: #339af0;">[{current_time}] 📊 Ожидание данных от сервисов...</span>',
            f'<span style="color: #ffd43b;">[{current_time}] ⚠️ Запустите сервисы для получения логов</span>',
            f'<span style="color: #339af0;">[{current_time}] 💡 Используйте run.py или панель управления</span>'
        ]

    def format_log_line(self, line, level='INFO'):
        """Форматирует строку лога"""
        if not line.strip():
            return None

        line = line.strip()

        # Добавляем временную метку если её нет
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line[:19]):
            current_time = datetime.now().strftime("%H:%M:%S")
            line = f"[{current_time}] {line}"

        # Цвета в зависимости от уровня
        colors = {
            'ERROR': '#ff6b6b',
            'WARNING': '#ffd43b',
            'SUCCESS': '#51cf66',
            'INFO': '#339af0'
        }

        color = colors.get(level, '#dee2e6')
        return f'<span style="color: {color};">{self.escape_html(line)}</span>'

    def escape_html(self, text):
        """Экранирует HTML символы"""
        return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#039;'))

    def get_demo_output(self):
        """Возвращает демо-вывод если логов нет"""
        current_time = datetime.now().strftime("%H:%M:%S")
        return [
            f'<span style="color: #ffd43b;">[{current_time}] ⚠️ Лог-файлы не найдены. Запустите парсер для получения реальных логов.</span>',
            f'<span style="color: #339af0;">[{current_time}] 💡 Для тестирования перейдите в раздел "Парсер" и запустите поиск</span>'
        ]

    def start_monitoring(self):
        """Запускает мониторинг"""
        if not self.is_monitoring:
            self.is_monitoring = True

    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_monitoring = False


# Глобальный экземпляр
log_viewer = LogViewer()