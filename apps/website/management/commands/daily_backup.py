import os
import shutil
import logging
import subprocess
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
import psycopg2
from django.conf import settings

# ✅ Создаем логгер для команды бэкапа
logger = logging.getLogger('dashboard.management.commands.create_backup')


class Command(BaseCommand):
    help = 'Создает ежедневный бэкап базы данных PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-days',
            type=int,
            default=7,
            help='Количество дней для хранения бэкапов (по умолчанию: 7)',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            default=True,
            help='Сжимать бэкап в .gz формат',
        )
        parser.add_argument(
            '--only-schema',
            action='store_true',
            default=False,
            help='Бэкапировать только схему (без данных)',
        )

    def handle(self, *args, **options):
        logger.info("💾 Начало создания бэкапа базы данных PostgreSQL")

        backup_dir = 'database_backups'
        keep_days = options['keep_days']
        compress = options['compress']
        only_schema = options['only_schema']

        try:
            # Получаем конфигурацию базы данных из Django settings
            db_config = self._get_database_config()

            if not db_config:
                logger.error("❌ Не удалось получить конфигурацию базы данных")
                self.stdout.write(
                    self.style.ERROR('❌ Не удалось получить конфигурацию базы данных')
                )
                return

            # Создаем папку для бэкапов если ее нет
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                logger.info(f"📁 Создана папка для бэкапов: {backup_dir}")

            # Создаем новый бэкап
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_name = db_config.get('NAME', 'unknown_db')

            if only_schema:
                backup_filename = f"schema_backup_{db_name}_{timestamp}.sql"
            else:
                backup_filename = f"full_backup_{db_name}_{timestamp}.sql"

            if compress:
                backup_filename += '.gz'

            backup_path = os.path.join(backup_dir, backup_filename)

            # Создаем дамп базы данных
            success = self._create_postgres_dump(
                db_config,
                backup_path,
                compress=compress,
                schema_only=only_schema
            )

            if not success:
                logger.error("❌ Не удалось создать бэкап базы данных")
                self.stdout.write(
                    self.style.ERROR('❌ Не удалось создать бэкап базы данных')
                )
                return

            # Проверяем размер бэкапа
            if os.path.exists(backup_path):
                backup_size = os.path.getsize(backup_path)
                backup_size_mb = backup_size / (1024 * 1024)

                logger.info(f"✅ Бэкап создан: {backup_filename}")
                logger.info(f"📊 Размер бэкапа: {backup_size_mb:.2f} MB")
                logger.info(f"📅 Бэкапы хранятся: {keep_days} дней")
                logger.info(f"🗄️ База данных: {db_name}")

                if only_schema:
                    logger.info("📋 Тип бэкапа: Только схема (без данных)")
                else:
                    logger.info("📋 Тип бэкапа: Полный (с данными)")
            else:
                logger.error(f"❌ Файл бэкапа не создан: {backup_path}")
                self.stdout.write(
                    self.style.ERROR(f'❌ Файл бэкапа не создан: {backup_path}')
                )
                return

            # Удаляем старые бэкапы
            deleted_count = self.clean_old_backups(backup_dir, keep_days, db_name)

            if deleted_count > 0:
                logger.info(f"🧹 Удалено старых бэкапов: {deleted_count}")

            # Статистика оставшихся бэкапов
            remaining_backups = len([
                f for f in os.listdir(backup_dir)
                if f'_{db_name}_' in f and (f.endswith('.sql') or f.endswith('.sql.gz'))
            ])

            total_size_mb = sum(
                os.path.getsize(os.path.join(backup_dir, f)) / (1024 * 1024)
                for f in os.listdir(backup_dir)
                if f'_{db_name}_' in f and (f.endswith('.sql') or f.endswith('.sql.gz'))
            )

            logger.info(f"📦 Всего бэкапов {db_name}: {remaining_backups}")
            logger.info(f"📦 Общий размер бэкапов: {total_size_mb:.2f} MB")

            logger.info("🎯 Создание бэкапа PostgreSQL завершено успешно")

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Бэкап PostgreSQL создан: {backup_filename} ({backup_size_mb:.2f} MB)\n'
                    f'   База данных: {db_name}\n'
                    f'   Тип: {"Схема" if only_schema else "Полный"}\n'
                    f'   Сжатие: {"Да" if compress else "Нет"}'
                )
            )

        except Exception as e:
            logger.error(f"❌ Ошибка создания бэкапа: {str(e)}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка создания бэкапа: {str(e)}')
            )

    def _get_database_config(self):
        """Получает конфигурацию базы данных из Django settings"""
        try:
            # Используем дефолтную базу данных из настроек Django
            db_settings = settings.DATABASES.get('default', {})

            if not db_settings:
                logger.error("❌ Не найдена конфигурация базы данных в settings.DATABASES")
                return None

            # Проверяем, что используется PostgreSQL
            engine = db_settings.get('ENGINE', '')
            if 'postgresql' not in engine:
                logger.error(f"❌ Не PostgreSQL база данных: {engine}")
                return None

            config = {
                'NAME': db_settings.get('NAME'),
                'USER': db_settings.get('USER'),
                'PASSWORD': db_settings.get('PASSWORD'),
                'HOST': db_settings.get('HOST', 'localhost'),
                'PORT': db_settings.get('PORT', '5432'),
                'ENGINE': engine
            }

            # Проверяем обязательные параметры
            missing = [k for k in ['NAME', 'USER', 'PASSWORD'] if not config.get(k)]
            if missing:
                logger.error(f"❌ Отсутствуют обязательные параметры: {missing}")
                return None

            logger.info(f"✅ Конфигурация БД получена: {config['NAME']} на {config['HOST']}:{config['PORT']}")
            return config

        except Exception as e:
            logger.error(f"❌ Ошибка получения конфигурации БД: {str(e)}")
            return None

    def _create_postgres_dump(self, db_config, output_path, compress=False, schema_only=False):
        """Создает дамп базы данных PostgreSQL"""
        try:
            # Временный файл для дампа
            temp_dump = output_path
            if compress:
                temp_dump = output_path.replace('.gz', '')

            # Формируем команду pg_dump
            cmd = [
                'pg_dump',
                '-h', db_config.get('HOST', 'localhost'),
                '-p', str(db_config.get('PORT', '5432')),
                '-U', db_config.get('USER'),
                '-d', db_config.get('NAME'),
                '-F', 'p',  # plain text format
                '-f', temp_dump
            ]

            if schema_only:
                cmd.append('-s')  # только схема

            # Добавляем опции для более надежного бэкапа
            cmd.extend([
                '--no-owner',  # не указывать владельца
                '--no-privileges',  # не включать привилегии
                '--clean',  # добавить команды DROP перед CREATE
                '--if-exists'  # использовать IF EXISTS в DROP командах
            ])

            # Устанавливаем переменную окружения с паролем
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config.get('PASSWORD', '')

            logger.info(f"🔄 Создание дампа: {db_config['NAME']} -> {temp_dump}")
            if schema_only:
                logger.info("📋 Режим: только схема")

            # Выполняем команду
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # таймаут 1 час для больших БД
            )

            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Неизвестная ошибка"
                logger.error(f"❌ Ошибка pg_dump: {error_msg}")
                # Удаляем частично созданный файл
                if os.path.exists(temp_dump):
                    os.remove(temp_dump)
                return False

            # Сжимаем если нужно
            if compress and os.path.exists(temp_dump):
                import gzip
                with open(temp_dump, 'rb') as f_in:
                    with gzip.open(output_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(temp_dump)
                logger.info(f"✅ Дамп сжат: {output_path}")
            elif os.path.exists(temp_dump) and temp_dump != output_path:
                shutil.move(temp_dump, output_path)

            logger.info(f"✅ Дамп успешно создан: {output_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ Таймаут при создании дампа (1 час)")
            # Удаляем частично созданный файл
            if 'temp_dump' in locals() and os.path.exists(temp_dump):
                os.remove(temp_dump)
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка создания дампа: {str(e)}", exc_info=True)
            # Удаляем частично созданный файл
            if 'temp_dump' in locals() and os.path.exists(temp_dump):
                os.remove(temp_dump)
            return False

    def clean_old_backups(self, backup_dir, keep_days, db_name):
        """Удаляет бэкапы старше указанного количества дней для конкретной БД"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0

            for filename in os.listdir(backup_dir):
                # Проверяем, что это бэкап нужной базы данных
                if f'_{db_name}_' in filename and (filename.endswith('.sql') or filename.endswith('.sql.gz')):
                    filepath = os.path.join(backup_dir, filename)

                    try:
                        file_time = datetime.fromtimestamp(os.path.getctime(filepath))

                        if file_time < cutoff_date:
                            file_size = os.path.getsize(filepath)
                            file_size_mb = file_size / (1024 * 1024)

                            os.remove(filepath)
                            deleted_count += 1

                            logger.info(f"🗑️ Удален старый бэкап: {filename} ({file_size_mb:.2f} MB)")
                            self.stdout.write(f'🗑️ Удален старый бэкап: {filename}')
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось обработать файл {filename}: {str(e)}")
                        continue

            return deleted_count

        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых бэкапов: {str(e)}")
            return 0

    def verify_backup_integrity(self, backup_path, db_config):
        """Проверяет целостность бэкапа (опционально)"""
        try:
            if backup_path.endswith('.gz'):
                import gzip
                with gzip.open(backup_path, 'rb') as f:
                    first_line = f.readline().decode('utf-8', errors='ignore')
            else:
                with open(backup_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline()

            # Проверяем, что это валидный SQL дамп PostgreSQL
            if 'PostgreSQL database dump' in first_line or 'SET statement_timeout' in first_line:
                logger.info(f"✅ Бэкап валиден: {backup_path}")
                return True
            else:
                logger.warning(f"⚠️ Неизвестный формат бэкапа: {backup_path}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки целостности бэкапа: {str(e)}")
            return False


# Пример команды для планировщика задач (cron):
"""
# Ежедневный полный бэкап в 2:00 ночи
0 2 * * * cd /path/to/your/project && python manage.py create_backup --compress

# Еженедельный бэкап только схемы в воскресенье в 3:00
0 3 * * 0 cd /path/to/your/project && python manage.py create_backup --only-schema --keep-days 30

# Бэкап с сохранением 14 дней
0 4 * * * cd /path/to/your/project && python manage.py create_backup --keep-days 14
"""