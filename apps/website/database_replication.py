import os
import shutil
import sqlite3
from datetime import datetime
import threading
import time


class DatabaseReplication:
    def __init__(self):
        self.primary_db = 'db.sqlite3'
        self.replica_db = 'db_replica.sqlite3'
        self.is_running = False
        self.replication_thread = None

    def start_replication(self):
        if self.is_running:
            return False

        self.is_running = True
        self.replication_thread = threading.Thread(target=self._replication_worker, daemon=True)
        self.replication_thread.start()
        return True

    def stop_replication(self):
        """Останавливает репликацию"""
        self.is_running = False
        if self.replication_thread:
            self.replication_thread.join(timeout=5)

    def _replication_worker(self):
        """Фоновая задача репликации"""
        while self.is_running:
            try:
                self.sync_databases()
                time.sleep(300)  # Синхронизация каждую минуту
            except Exception as e:
                add_to_console(f"Ошибка репликации: {e}")
                time.sleep(300)  # Ждем минуту при ошибке

    def sync_databases(self):
        """Синхронизирует основную и реплицированную базы"""
        if not os.path.exists(self.primary_db):
            return False

        # Создаем папку для бэкапов если ее нет
        if not os.path.exists('database_backups'):
            os.makedirs('database_backups')

        # Создаем резервную копию перед синхронизацией
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f'database_backups/replica_backup_{backup_time}.sqlite3'

        if os.path.exists(self.replica_db):
            shutil.copy2(self.replica_db, backup_path)

        # Копируем основную базу в реплику
        shutil.copy2(self.primary_db, self.replica_db)

        # Проверяем целостность реплики
        if self.verify_replica_integrity():
            add_to_console(f"✅ Репликация успешна: {datetime.now()}")
            return True
        else:
            # Восстанавливаем из бэкапа при ошибке
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, self.replica_db)
            print("❌ Ошибка репликации - восстановлен предыдущий бэкап")
            return False

    def verify_replica_integrity(self):
        """Проверяет целостность реплицированной базы"""
        try:
            conn = sqlite3.connect(self.replica_db)
            cursor = conn.cursor()

            # Проверяем основные таблицы
            tables_to_check = [
                'dashboard_founditem',
                'dashboard_searchquery',
                'dashboard_parsersettings',
                'auth_user'
            ]

            for table in tables_to_check:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    cursor.execute(f"SELECT COUNT(*) FROM {table} LIMIT 1")

            conn.close()
            return True
        except Exception as e:
            add_to_console(f"Ошибка проверки целостности: {e}")
            return False

    def get_replication_status(self):
        primary_size = 0
        replica_size = 0
        primary_exists = os.path.exists(self.primary_db)
        replica_exists = os.path.exists(self.replica_db)

        if primary_exists:
            primary_size = os.path.getsize(self.primary_db) / (1024 * 1024)  # MB

        if replica_exists:
            replica_size = os.path.getsize(self.replica_db) / (1024 * 1024)  # MB

        size_diff = abs(primary_size - replica_size)
        size_diff_percent = (size_diff / primary_size * 100) if primary_size > 0 else 0

        return {
            'is_running': self.is_running,
            'primary_size': f"{primary_size:.2f} MB",
            'replica_size': f"{replica_size:.2f} MB",
            'size_diff_percent': size_diff_percent,
            'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'primary_exists': primary_exists,
            'replica_exists': replica_exists
        }