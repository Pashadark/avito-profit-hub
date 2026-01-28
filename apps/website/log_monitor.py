# apps/website/log_monitor.py
import hashlib
import time
import os
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import TodoBoard, TodoCard

User = get_user_model()


class LogMonitor:
    """Мониторинг логов и автоматическое создание задач"""

    @staticmethod
    def create_task_from_error(user, error_message, log_file='system.log', task_type='error'):
        """Создать задачу из ошибки в логах"""
        try:
            # Создаем хэш ошибки для предотвращения дублирования
            error_hash = hashlib.sha256(error_message.encode()).hexdigest()

            # Проверяем, нет ли уже такой ошибки
            if TodoCard.objects.filter(error_hash=error_hash).exists():
                return None

            # Получаем или создаем доску пользователя
            board, created = TodoBoard.objects.get_or_create(
                user=user,
                defaults={'name': 'Мои задачи'}
            )

            # Создаем карточку
            title = f"Ошибка в логах: {error_message[:50]}..."
            description = f"""
            🚨 Обнаружена ошибка в логах

            Файл: {log_file}
            Время: {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}

            Сообщение ошибки:
            {error_message}

            ---
            Автоматически создано системой мониторинга логов
            """

            card = TodoCard.objects.create(
                board=board,
                title=title,
                description=description.strip(),
                status='todo',
                priority=4,  # Критический приоритет
                task_type=task_type,
                error_hash=error_hash,
                created_by=user
            )

            return card

        except Exception as e:
            print(f"❌ Ошибка создания задачи из логов: {e}")
            return None

    @staticmethod
    def parse_log_file(file_path, user, max_lines=100):
        """Парсит файл логов и создает задачи для ошибок"""
        if not os.path.exists(file_path):
            return []

        created_tasks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-max_lines:]  # Читаем последние N строк

                for line in lines:
                    line = line.strip()

                    # Ищем ошибки
                    if any(error_word in line.lower() for error_word in ['error', 'exception', 'traceback', 'failed']):
                        # Ищем WARNING отдельно
                        task_type = 'warning' if 'warning' in line.lower() else 'error'

                        # Создаем задачу
                        task = LogMonitor.create_task_from_error(
                            user=user,
                            error_message=line[:200],  # Ограничиваем длину
                            log_file=os.path.basename(file_path),
                            task_type=task_type
                        )

                        if task:
                            created_tasks.append(task)

            return created_tasks

        except Exception as e:
            print(f"❌ Ошибка парсинга логов: {e}")
            return []