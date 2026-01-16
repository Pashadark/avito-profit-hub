import os
import shutil
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

# ✅ Создаем логгер для команды бэкапа
logger = logging.getLogger('dashboard.management.commands.create_backup')


class Command(BaseCommand):
    help = 'Создает ежедневный бэкап базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-days',
            type=int,
            default=7,
            help='Количество дней для хранения бэкапов (по умолчанию: 7)',
        )

    def handle(self, *args, **options):
        logger.info("💾 Начало создания бэкапа базы данных")

        backup_dir = 'database_backups'
        keep_days = options['keep_days']

        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                logger.info(f"📁 Создана папка для бэкапов: {backup_dir}")

            # Создаем новый бэкап
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"auto_backup_{timestamp}.sqlite3"
            backup_path = os.path.join(backup_dir, backup_filename)

            # Проверяем существование исходной базы
            if not os.path.exists('db.sqlite3'):
                logger.error("❌ Исходная база данных db.sqlite3 не найдена")
                self.stdout.write(
                    self.style.ERROR('❌ Исходная база данных db.sqlite3 не найдена')
                )
                return

            # Копируем базу данных
            shutil.copy2('db.sqlite3', backup_path)

            # Проверяем размер бэкапа
            backup_size = os.path.getsize(backup_path)
            backup_size_mb = backup_size / (1024 * 1024)

            logger.info(f"✅ Бэкап создан: {backup_filename}")
            logger.info(f"📊 Размер бэкапа: {backup_size_mb:.2f} MB")
            logger.info(f"📅 Бэкапы хранятся: {keep_days} дней")

            # Удаляем старые бэкапы
            deleted_count = self.clean_old_backups(backup_dir, keep_days)

            if deleted_count > 0:
                logger.info(f"🧹 Удалено старых бэкапов: {deleted_count}")

            # Статистика оставшихся бэкапов
            remaining_backups = len([f for f in os.listdir(backup_dir) if f.startswith('auto_backup_')])
            logger.info(f"📦 Всего бэкапов в папке: {remaining_backups}")

            logger.info("🎯 Создание бэкапа завершено успешно")

            self.stdout.write(
                self.style.SUCCESS(f'✅ Автобэкап создан: {backup_filename} ({backup_size_mb:.2f} MB)')
            )

        except Exception as e:
            logger.error(f"❌ Ошибка создания бэкапа: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка создания бэкапа: {str(e)}')
            )

    def clean_old_backups(self, backup_dir, keep_days):
        """Удаляет бэкапы старше указанного количества дней"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0

            for filename in os.listdir(backup_dir):
                if filename.startswith('auto_backup_') and filename.endswith('.sqlite3'):
                    filepath = os.path.join(backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))

                    if file_time < cutoff_date:
                        file_size = os.path.getsize(filepath)
                        file_size_mb = file_size / (1024 * 1024)

                        os.remove(filepath)
                        deleted_count += 1

                        logger.info(f"🗑️ Удален старый бэкап: {filename} ({file_size_mb:.2f} MB)")

                        self.stdout.write(f'🗑️ Удален старый бэкап: {filename}')

            return deleted_count

        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых бэкапов: {str(e)}")
            return 0