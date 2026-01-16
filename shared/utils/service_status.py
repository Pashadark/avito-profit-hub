import json
import os
import time
from datetime import datetime


def safe_update_service_status(service, status, details=None):
    """Безопасное обновление статуса с повторными попытками"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            status_file = 'service_status.json'
            data = {}

            # Читаем существующие данные
            if os.path.exists(status_file):
                with open(status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # Обновляем статус
            data[service] = {
                'status': status,
                'last_update': datetime.now().isoformat(),
                'details': details or {}
            }

            # Пишем с временным файлом чтобы избежать блокировок
            temp_file = status_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Заменяем оригинальный файл
            if os.path.exists(status_file):
                os.remove(status_file)
            os.rename(temp_file, status_file)

            return True

        except (IOError, OSError, json.JSONDecodeError) as e:
            if attempt == max_retries - 1:
                add_to_console(f"Ошибка обновления статуса после {max_retries} попыток: {e}")
                return False
            time.sleep(0.1)


def get_service_statuses():
    """Безопасное чтение статусов"""
    try:
        status_file = 'service_status.json'
        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Если файла нет, создаем начальные статусы
        initial_statuses = {
            'website': {'status': 'stopped', 'last_update': datetime.now().isoformat()},
            'bot': {'status': 'stopped', 'last_update': datetime.now().isoformat()},
            'parser': {'status': 'stopped', 'last_update': datetime.now().isoformat()}
        }
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(initial_statuses, f, indent=2, ensure_ascii=False)
        return initial_statuses
    except Exception as e:
        add_to_console(f"Ошибка чтения статусов: {e}")
        return {
            'website': {'status': 'unknown', 'error': str(e)},
            'bot': {'status': 'unknown', 'error': str(e)},
            'parser': {'status': 'unknown', 'error': str(e)}
        }