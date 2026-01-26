import os
import shutil
import psycopg2
from psycopg2 import pool
from datetime import datetime
import threading
import time
import subprocess
import tempfile


class DatabaseReplication:
    def __init__(self, primary_config, replica_config=None):
        """
        Инициализация репликации PostgreSQL

        Args:
            primary_config (dict): Конфигурация основной базы данных PostgreSQL
                Пример: {
                    'dbname': 'primary_db',
                    'user': 'postgres',
                    'password': 'password',
                    'host': 'localhost',
                    'port': '5432'
                }
            replica_config (dict, optional): Конфигурация реплики
                Если не указана, будет использоваться та же конфигурация с другим dbname
        """
        self.primary_config = primary_config

        if replica_config:
            self.replica_config = replica_config
        else:
            # Создаем конфигурацию реплики на основе основной
            self.replica_config = primary_config.copy()
            if 'dbname' in self.replica_config:
                self.replica_config['dbname'] = f"{self.replica_config['dbname']}_replica"

        self.is_running = False
        self.replication_thread = None

        # Пул соединений
        self.primary_pool = None
        self.replica_pool = None
        self._init_connection_pools()

    def _init_connection_pools(self):
        """Инициализация пулов соединений PostgreSQL"""
        try:
            self.primary_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                **{k: v for k, v in self.primary_config.items() if k != 'dbname'}
            )

            self.replica_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                **{k: v for k, v in self.replica_config.items() if k != 'dbname'}
            )
            print("✅ Пул соединений PostgreSQL инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации пула соединений: {e}")

    def start_replication(self):
        """Запуск репликации"""
        if self.is_running:
            print("⚠️ Репликация уже запущена")
            return False

        # Создаем реплику если ее нет
        if not self._check_database_exists(self.replica_config['dbname']):
            print(f"Создание реплики {self.replica_config['dbname']}...")
            if not self._create_replica_database():
                print("❌ Не удалось создать реплику")
                return False

        self.is_running = True
        self.replication_thread = threading.Thread(
            target=self._replication_worker,
            daemon=True
        )
        self.replication_thread.start()
        print("✅ Репликация PostgreSQL запущена")
        return True

    def stop_replication(self):
        """Останавливает репликацию"""
        if not self.is_running:
            return

        print("🛑 Остановка репликации...")
        self.is_running = False
        if self.replication_thread:
            self.replication_thread.join(timeout=10)

        # Закрываем пулы соединений
        if self.primary_pool:
            self.primary_pool.closeall()
        if self.replica_pool:
            self.replica_pool.closeall()

        print("✅ Репликация остановлена")

    def _replication_worker(self):
        """Фоновая задача репликации"""
        while self.is_running:
            try:
                success = self.sync_databases()
                if success:
                    self._log_to_console(f"✅ Репликация успешна: {datetime.now()}")
                else:
                    self._log_to_console(f"⚠️ Репликация не выполнена")

                time.sleep(300)  # Синхронизация каждые 5 минут
            except Exception as e:
                self._log_to_console(f"❌ Ошибка репликации: {e}")
                time.sleep(60)  # Ждем минуту при ошибке

    def sync_databases(self):
        """Синхронизирует основную базу и реплику"""
        if not self._check_database_exists(self.primary_config['dbname']):
            self._log_to_console(f"❌ Основная база {self.primary_config['dbname']} не существует")
            return False

        # Создаем папку для бэкапов если ее нет
        if not os.path.exists('database_backups'):
            os.makedirs('database_backups')

        # Создаем резервную копию структуры реплики
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f'database_backups/replica_backup_{backup_time}.sql'

        try:
            # 1. Создаем дамп реплики (только структура)
            self._create_database_dump(self.replica_config, backup_path, schema_only=True)

            # 2. Очищаем реплику
            self._clear_replica_database()

            # 3. Создаем дамп основной базы
            primary_dump = tempfile.mktemp(suffix='.sql')
            self._create_database_dump(self.primary_config, primary_dump)

            # 4. Восстанавливаем дамп в реплику
            self._restore_database_dump(self.replica_config, primary_dump)

            # 5. Проверяем целостность
            if self.verify_replica_integrity():
                self._log_to_console(f"✅ Репликация успешна")
                return True
            else:
                # 6. Восстанавливаем из бэкапа при ошибке
                self._log_to_console(f"❌ Ошибка целостности, восстанавливаем из бэкапа")
                self._restore_database_dump(self.replica_config, backup_path)
                return False

        except Exception as e:
            self._log_to_console(f"❌ Ошибка синхронизации: {e}")

            # Попытка восстановления из бэкапа
            if os.path.exists(backup_path):
                try:
                    self._restore_database_dump(self.replica_config, backup_path)
                except Exception as restore_error:
                    self._log_to_console(f"❌ Ошибка восстановления из бэкапа: {restore_error}")

            return False

    def verify_replica_integrity(self):
        """Проверяет целостность реплицированной базы"""
        try:
            conn = self.replica_pool.getconn()
            cursor = conn.cursor()

            # Проверяем основные таблицы
            tables_to_check = [
                'dashboard_founditem',
                'dashboard_searchquery',
                'dashboard_parsersettings',
                'auth_user'
            ]

            for table in tables_to_check:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table,))

                if not cursor.fetchone()[0]:
                    self.replica_pool.putconn(conn)
                    return False

                # Проверяем, что таблица не пустая (хотя бы 1 запись)
                cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")

            conn.commit()
            self.replica_pool.putconn(conn)
            return True

        except Exception as e:
            self._log_to_console(f"❌ Ошибка проверки целостности: {e}")
            return False
        finally:
            try:
                self.replica_pool.putconn(conn)
            except:
                pass

    def _check_database_exists(self, dbname):
        """Проверяет существование базы данных"""
        try:
            # Подключаемся к базе данных postgres для проверки
            check_config = self.primary_config.copy()
            check_config['dbname'] = 'postgres'

            conn = psycopg2.connect(**check_config)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return exists
        except Exception as e:
            self._log_to_console(f"❌ Ошибка проверки существования БД {dbname}: {e}")
            return False

    def _create_replica_database(self):
        """Создает базу данных для реплики"""
        try:
            # Подключаемся к postgres для создания БД
            admin_config = self.primary_config.copy()
            admin_config['dbname'] = 'postgres'

            conn = psycopg2.connect(**admin_config)
            conn.autocommit = True
            cursor = conn.cursor()

            # Создаем базу данных
            cursor.execute(f"CREATE DATABASE {self.replica_config['dbname']}")

            # Копируем структуру из основной базы
            temp_dump = tempfile.mktemp(suffix='.sql')
            self._create_database_dump(self.primary_config, temp_dump, schema_only=True)

            # Восстанавливаем структуру в новую базу
            restore_config = self.replica_config.copy()
            self._restore_database_dump(restore_config, temp_dump)

            # Удаляем временный файл
            if os.path.exists(temp_dump):
                os.remove(temp_dump)

            cursor.close()
            conn.close()

            self._log_to_console(f"✅ Создана реплика: {self.replica_config['dbname']}")
            return True

        except Exception as e:
            self._log_to_console(f"❌ Ошибка создания реплики: {e}")
            return False

    def _create_database_dump(self, db_config, output_path, schema_only=False):
        """Создает дамп базы данных PostgreSQL"""
        try:
            # Формируем команду pg_dump
            cmd = [
                'pg_dump',
                '-h', db_config.get('host', 'localhost'),
                '-p', str(db_config.get('port', '5432')),
                '-U', db_config.get('user', 'postgres'),
                '-d', db_config.get('dbname', 'postgres'),
                '-f', output_path,
                '-F', 'p'  # plain text format
            ]

            if schema_only:
                cmd.append('-s')  # только структура

            # Устанавливаем переменную окружения с паролем
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config.get('password', '')

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # таймаут 5 минут
            )

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            raise Exception("Таймаут при создании дампа")
        except Exception as e:
            raise Exception(f"Ошибка создания дампа: {e}")

    def _restore_database_dump(self, db_config, dump_path):
        """Восстанавливает базу данных из дампа"""
        try:
            if not os.path.exists(dump_path):
                raise Exception(f"Файл дампа не существует: {dump_path}")

            # Формируем команду psql
            cmd = [
                'psql',
                '-h', db_config.get('host', 'localhost'),
                '-p', str(db_config.get('port', '5432')),
                '-U', db_config.get('user', 'postgres'),
                '-d', db_config.get('dbname', 'postgres'),
                '-f', dump_path
            ]

            # Устанавливаем переменную окружения с паролем
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config.get('password', '')

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # таймаут 5 минут
            )

            if result.returncode != 0:
                raise Exception(f"psql restore failed: {result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            raise Exception("Таймаут при восстановлении из дампа")
        except Exception as e:
            raise Exception(f"Ошибка восстановления из дампа: {e}")

    def _clear_replica_database(self):
        """Очищает реплику (удаляет все данные, сохраняя структуру)"""
        try:
            conn = self.replica_pool.getconn()
            conn.autocommit = True
            cursor = conn.cursor()

            # Отключаем всех пользователей от базы
            cursor.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
            """, (self.replica_config['dbname'],))

            # Получаем все таблицы в публичной схеме
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """)

            tables = cursor.fetchall()

            # Удаляем данные из всех таблиц (TRUNCATE быстрее чем DELETE)
            for table in tables:
                try:
                    cursor.execute(f'TRUNCATE TABLE "{table[0]}" CASCADE')
                except Exception as e:
                    self._log_to_console(f"⚠️ Не удалось очистить таблицу {table[0]}: {e}")

            conn.autocommit = False
            self.replica_pool.putconn(conn)
            return True

        except Exception as e:
            self._log_to_console(f"❌ Ошибка очистки реплики: {e}")
            return False
        finally:
            try:
                self.replica_pool.putconn(conn)
            except:
                pass

    def get_replication_status(self):
        """Возвращает статус репликации"""
        try:
            # Получаем размеры баз данных
            primary_size = self._get_database_size(self.primary_config)
            replica_size = self._get_database_size(self.replica_config)

            primary_exists = self._check_database_exists(self.primary_config['dbname'])
            replica_exists = self._check_database_exists(self.replica_config['dbname'])

            size_diff = abs(primary_size - replica_size) if primary_size and replica_size else 0
            size_diff_percent = (size_diff / primary_size * 100) if primary_size > 0 else 0

            return {
                'is_running': self.is_running,
                'primary_size': f"{primary_size:.2f} MB" if primary_size else "N/A",
                'replica_size': f"{replica_size:.2f} MB" if replica_size else "N/A",
                'size_diff_percent': round(size_diff_percent, 2),
                'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'primary_exists': primary_exists,
                'replica_exists': replica_exists,
                'primary_db': self.primary_config.get('dbname'),
                'replica_db': self.replica_config.get('dbname')
            }

        except Exception as e:
            self._log_to_console(f"❌ Ошибка получения статуса: {e}")
            return {
                'is_running': self.is_running,
                'error': str(e)
            }

    def _get_database_size(self, db_config):
        """Получает размер базы данных в мегабайтах"""
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_database_size(%s) / (1024 * 1024) as size_mb
            """, (db_config['dbname'],))
            size_mb = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return float(size_mb)
        except:
            return 0

    def _log_to_console(self, message):
        """Логирование сообщений (замените на вашу реализацию)"""
        # Здесь должна быть ваша функция add_to_console
        # Пока просто выводим в консоль
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def __del__(self):
        """Деструктор для очистки ресурсов"""
        self.stop_replication()


# Пример использования
if __name__ == "__main__":
    # Конфигурация основной базы
    primary_config = {
        'dbname': 'avito_profit_hub',
        'user': 'postgres',
        'password': 'your_password',
        'host': 'localhost',
        'port': '5432'
    }

    # Создаем объект репликации
    replicator = DatabaseReplication(primary_config)

    # Запускаем репликацию
    replicator.start_replication()

    # Получаем статус
    status = replicator.get_replication_status()
    print("Статус репликации:", status)

    # Даем поработать некоторое время
    time.sleep(10)

    # Останавливаем репликацию
    replicator.stop_replication()