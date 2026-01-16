# utils/status_sync.py
import json
import os
from datetime import datetime

class StatusManager:
    _instance = None
    _statuses = {
        'website': {'status': 'stopped', 'details': {'message': 'Не запущен'}},
        'bot': {'status': 'stopped', 'details': {'message': 'Не запущен'}},
        'parser': {'status': 'stopped', 'details': {'message': 'Не запущен'}}
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StatusManager, cls).__new__(cls)
        return cls._instance

    def update_status(self, service, status, details=None):
        """Обновляет статус сервиса"""
        self._statuses[service] = {
            'status': status,
            'details': details or {},
            'last_update': datetime.now().isoformat()
        }
        self._save_to_file()

    def get_statuses(self):
        """Возвращает текущие статусы"""
        return self._statuses

    def _save_to_file(self):
        """Сохраняет статусы в файл"""
        try:
            with open('service_status.json', 'w', encoding='utf-8') as f:
                json.dump(self._statuses, f, indent=2, ensure_ascii=False)
        except Exception as e:
            add_to_console(f"Ошибка сохранения статусов: {e}")

    def load_from_file(self):
        """Загружает статусы из файла"""
        try:
            if os.path.exists('service_status.json'):
                with open('service_status.json', 'r', encoding='utf-8') as f:
                    self._statuses = json.load(f)
        except:
            pass

# Глобальный экземпляр
status_manager = StatusManager()