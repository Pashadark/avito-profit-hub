# apps/core/utils/backup_manager.py
import os
import sys
import subprocess
import shutil
import gzip
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
import logging
from typing import Optional, Dict, List
import tempfile
import time
from django.contrib.auth.models import User

logger = logging.getLogger('system.backup')


class ProgressTracker:
    """📊 Класс для отслеживания прогресса отправки файлов с корректным форматированием"""

    def __init__(self, total_size=0, description=""):
        self.total_size = total_size
        self.current_size = 0
        self.start_time = time.time()
        self.description = description
        self.last_update = 0
        self.speed_history = []

    def update(self, chunk_size):
        """Обновить прогресс"""
        self.current_size += chunk_size
        current_time = time.time()

        # Обновляем раз в 1 секунду
        if current_time - self.last_update > 1.0:
            self.last_update = current_time
            self._print_progress()

    def _print_progress(self):
        """Вывести прогресс бар через logger"""
        if self.total_size > 0:
            percent = (self.current_size / self.total_size) * 100
            elapsed = time.time() - self.start_time
            speed = self.current_size / elapsed if elapsed > 0 else 0

            # Добавляем в историю скорости
            self.speed_history.append(speed)
            if len(self.speed_history) > 10:
                self.speed_history.pop(0)

            avg_speed = sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0

            # Оставшееся время
            if avg_speed > 0:
                remaining = (self.total_size - self.current_size) / avg_speed
                eta_str = f"ETA: {remaining:.0f}s"
            else:
                eta_str = "ETA: --"

            # Прогресс бар (20 символов)
            bar_length = 20
            filled_length = int(bar_length * self.current_size // self.total_size)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            # Форматирование размеров
            def format_size(bytes_size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if bytes_size < 1024.0:
                        return f"{bytes_size:.1f} {unit}"
                    bytes_size /= 1024.0
                return f"{bytes_size:.1f} TB"

            progress_str = f"{self.description}: |{bar}| {percent:6.1f}% "
            progress_str += f"[{format_size(self.current_size)}/{format_size(self.total_size)}] "
            progress_str += f"Speed: {format_size(avg_speed)}/s {eta_str}"

            logger.info(progress_str)

    def finish(self):
        """Завершить прогресс бар"""
        if self.total_size > 0:
            elapsed = time.time() - self.start_time
            avg_speed = self.total_size / elapsed if elapsed > 0 else 0

            def format_size(bytes_size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if bytes_size < 1024.0:
                        return f"{bytes_size:.1f} {unit}"
                    bytes_size /= 1024.0
                return f"{bytes_size:.1f} TB"

            finish_str = f"{self.description}: ✅ Завершено за {elapsed:.1f}s "
            finish_str += f"({format_size(avg_speed)}/s)"

            logger.info(finish_str)


class TelegramBackupSender:
    """📤 Отправка бэкапов через Telegram бота ЛИЧНО АДМИНУ"""

    def __init__(self):
        self.token = self._get_telegram_token()
        self.admin_user_id = self._get_admin_telegram_id()

    def _get_telegram_token(self) -> Optional[str]:
        """Получаем токен Telegram бота"""
        try:
            token = settings.TELEGRAM_BOT_TOKEN
            if token:
                logger.info("✅ Токен Telegram бота загружен из настроек")
                return token
        except:
            pass

        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if token:
            logger.info("✅ Токен Telegram бота загружен из переменных окружения")
            return token

        logger.warning("⚠️ Токен Telegram бота не найден. Отправка в Telegram отключена.")
        return None

    def _get_admin_telegram_id(self) -> Optional[str]:
        """Получаем Telegram ID админа из настроек"""
        try:
            # Пробуем из настроек Django
            telegram_id = getattr(settings, 'ADMIN_TELEGRAM_ID', None)
            if telegram_id:
                logger.info(f"✅ Telegram ID админа из настроек: {telegram_id}")
                return str(telegram_id)

            # Пробуем из переменной окружения
            telegram_id = os.environ.get('ADMIN_TELEGRAM_ID')
            if telegram_id:
                logger.info(f"✅ Telegram ID админа из переменных окружения: {telegram_id}")
                return str(telegram_id)

            logger.warning("⚠️ Telegram ID админа не найден в настройках")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения Telegram ID админа: {e}")
            return None

    def send_file(self, file_path: str, caption: str = "") -> bool:
        """Отправляет файл в Telegram лично админу"""
        if not self.token or not self.admin_user_id:
            logger.warning("⚠️ Не настроен Telegram бот или не указан ID админа для отправки файлов")
            return False

        try:
            if not os.path.exists(file_path):
                logger.error(f"❌ Файл для отправки не найден: {file_path}")
                return False

            file_size = os.path.getsize(file_path)
            filename = Path(file_path).name

            # Адаптивные таймауты
            if file_size < 5 * 1024 * 1024:  # До 5MB
                timeout = (15, 60)  # 1 минута
            elif file_size < 20 * 1024 * 1024:  # До 20MB
                timeout = (30, 180)  # 3 минуты
            elif file_size < 50 * 1024 * 1024:  # До 50MB
                timeout = (30, 300)  # 5 минут
            else:  # Для премиума
                timeout = (30, 600)  # 10 минут

            logger.info(f"📤 Отправка файла админу в Telegram: {filename} ({file_size / 1024 / 1024:.1f}MB)")
            logger.info(f"⏱️  Таймаут: {timeout[1]} секунд")

            # Создаем прогресс трекер
            progress = ProgressTracker(file_size, f"📤 Отправка {filename}")

            # Отправляем файл
            success = self._upload_with_progress(file_path, filename, caption, progress, timeout)

            progress.finish()
            return success

        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False

    def _upload_with_progress(self, file_path: str, filename: str, caption: str, progress: ProgressTracker,
                              timeout=(30, 300)) -> bool:
        """Загрузка файла с отслеживанием прогресса"""
        try:
            import io

            class ProgressFile(io.BufferedReader):
                """Файл с отслеживанием прогресса чтения"""

                def __init__(self, file_obj, progress_tracker):
                    super().__init__(file_obj)
                    self.progress_tracker = progress_tracker

                def read(self, size=-1):
                    chunk = super().read(size)
                    if chunk:
                        self.progress_tracker.update(len(chunk))
                    return chunk

            with open(file_path, 'rb') as f:
                # Обернем файл в прогресс-трекер
                progress_file = ProgressFile(f, progress)

                url = f"https://api.telegram.org/bot{self.token}/sendDocument"
                files = {'document': (filename, progress_file)}
                data = {
                    'chat_id': self.admin_user_id,
                    'caption': caption,
                    'disable_notification': True,
                    'parse_mode': 'HTML'
                }

                response = requests.post(url, files=files, data=data, timeout=timeout)

                if response.status_code == 200:
                    logger.info(f"✅ Файл отправлен админу в Telegram: {filename}")
                    return True
                else:
                    logger.error(f"❌ Ошибка отправки файла: {response.status_code} - {response.text}")
                    return False

        except requests.exceptions.Timeout:
            logger.error(f"❌ Таймаут {timeout[1]}s при отправке файла: {filename}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False

    def send_compressed_folder(self, folder_path: str, caption: str = "") -> bool:
        """Сжимает папку и отправляет архив в Telegram админу"""
        if not self.token or not self.admin_user_id:
            logger.warning("⚠️ Не настроен Telegram бот для отправки папок")
            return False

        try:
            folder = Path(folder_path)
            if not folder.exists():
                logger.error(f"❌ Папка не найдена: {folder_path}")
                return False

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{folder.name}_backup_{timestamp}.tar.gz"

            logger.info(f"📦 Создание архива папки для админа: {folder.name}")

            # Считаем общий размер для прогресс бара
            total_size = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    filepath = os.path.join(root, file)
                    total_size += os.path.getsize(filepath)

            archive_progress = ProgressTracker(total_size, "📦 Создание архива")

            # Создаем архив
            with tempfile.TemporaryDirectory() as tmpdir:
                archive_path = Path(tmpdir) / archive_name

                import tarfile

                class ProgressTarFile(tarfile.TarFile):
                    """TarFile с отслеживанием прогресса"""

                    def add(self, name, arcname=None, recursive=True, *, filter=None):
                        if os.path.isfile(name):
                            file_size = os.path.getsize(name)
                            archive_progress.update(file_size)
                        super().add(name, arcname, recursive, filter=filter)

                with ProgressTarFile.open(archive_path, 'w:gz') as tar:
                    tar.add(folder, arcname=folder.name)

                archive_progress.finish()

                archive_size = archive_path.stat().st_size
                logger.info(f"✅ Архив создан: {archive_name} ({archive_size / 1024 / 1024:.1f}MB)")

                # Отправляем архив
                success = self.send_file(str(archive_path), caption)

                if success:
                    logger.info(f"✅ Папка отправлена админу в Telegram: {folder.name}")

                return success

        except Exception as e:
            logger.error(f"❌ Ошибка отправки папки: {e}")
            return False

    def send_backup_summary(self, backup_info: Dict, files_sent: List[str]) -> bool:
        """Отправляет сводку о бэкапе админу в ОДНОМ КРАСИВОМ СООБЩЕНИИ"""
        if not self.token or not self.admin_user_id:
            return False

        try:
            # Форматируем красивое сообщение
            message = self._format_backup_message(backup_info, files_sent)

            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': self.admin_user_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }

            response = requests.post(url, json=data, timeout=30)

            if response.status_code == 200:
                logger.info("✅ Красивая сводка отправлена админу в Telegram")
                return True
            else:
                logger.error(f"❌ Ошибка отправки сводки: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки сводки: {e}")
            return False

    def _format_backup_message(self, backup_info: Dict, files_sent: List[str]) -> str:
        """Форматирует красивое сообщение о бэкапе"""
        success_count = sum(1 for k, v in backup_info.items()
                            if v and k not in ['timestamp', 'complete_archive', 'telegram_sent',
                                               'complete_folder_sent'])

        # Статистика по типам
        status_info = {
            'database': {'icon': '🗄️', 'name': 'База данных'},
            'media': {'icon': '🖼️', 'name': 'Медиа файлы'},
            'logs': {'icon': '📝', 'name': 'Логи системы'},
            'ml_models': {'icon': '🧠', 'name': 'ML модели'}
        }

        # Собираем информацию о файлах
        file_details = []
        total_size = 0

        for file_path in files_sent:
            if os.path.exists(file_path):
                filename = Path(file_path).name
                file_size = os.path.getsize(file_path)
                total_size += file_size

                # Определяем тип файла
                file_type = '💾 Другой файл'
                file_icon = '📁'

                if 'postgres_backup' in filename:
                    file_type = '🗄️ База данных'
                    file_icon = '🗄️'
                elif 'media_backup' in filename:
                    file_type = '🖼️ Медиа файлы'
                    file_icon = '🖼️'
                elif 'logs_backup' in filename:
                    file_type = '📝 Логи системы'
                    file_icon = '📝'
                elif 'ml_models_backup' in filename:
                    file_type = '🧠 ML модели'
                    file_icon = '🧠'
                elif 'full_backup' in filename:
                    file_type = '📁 Полный архив'
                    file_icon = '📦'

                # Форматируем размер
                size_mb = file_size / 1024 / 1024
                if size_mb < 1:
                    size_str = f"{file_size / 1024:.1f}KB"
                else:
                    size_str = f"{size_mb:.1f}MB"

                file_details.append({
                    'icon': file_icon,
                    'type': file_type,
                    'name': filename,
                    'size': size_str,
                    'size_bytes': file_size
                })

        # Сортируем файлы по типу для красоты
        type_order = {'🗄️ База данных': 0, '🖼️ Медиа файлы': 1, '📝 Логи системы': 2,
                      '🧠 ML модели': 3, '📁 Полный архив': 4, '💾 Другой файл': 5}
        file_details.sort(key=lambda x: type_order.get(x['type'], 999))

        # Форматируем общий размер
        total_mb = total_size / 1024 / 1024
        if total_mb < 1:
            total_size_str = f"{total_size / 1024:.1f}KB"
        elif total_mb < 1024:
            total_size_str = f"{total_mb:.1f}MB"
        else:
            total_size_str = f"{total_mb / 1024:.1f}GB"

        # Строим сообщение
        message_lines = []

        # Заголовок
        message_lines.append("🚀 <b>СИСТЕМНЫЙ БЭКАП ЗАВЕРШЕН</b>")
        message_lines.append("=" * 30)

        # Время
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_lines.append(f"⏰ <b>Время:</b> {current_time}")
        message_lines.append("")

        # Статус выполнения
        message_lines.append(f"📊 <b>СТАТУС ВЫПОЛНЕНИЯ:</b> {success_count}/4")
        message_lines.append("")

        # Детали по каждому типу
        message_lines.append("🎯 <b>РЕЗУЛЬТАТЫ БЭКАПА:</b>")
        for key, info in status_info.items():
            icon = info['icon']
            name = info['name']
            status = "✅ УСПЕХ" if backup_info.get(key) else "❌ ОШИБКА"
            message_lines.append(f"  {icon} <b>{name}:</b> {status}")

        message_lines.append("")

        # Отправленные файлы
        if file_details:
            message_lines.append(f"📦 <b>ОТПРАВЛЕННЫЕ ФАЙЛЫ ({len(file_details)}):</b>")

            # Группируем по типам
            grouped_files = {}
            for file in file_details:
                file_type = file['type']
                if file_type not in grouped_files:
                    grouped_files[file_type] = []
                grouped_files[file_type].append(file)

            # Выводим файлы по группам
            for file_type, files in grouped_files.items():
                type_icon = files[0]['icon'] if files else '📁'
                # Убираем иконку из названия типа
                type_name = file_type.split(' ', 1)[1] if ' ' in file_type else file_type
                message_lines.append(f"  {type_icon} <b>{type_name}:</b>")

                for file in files:
                    message_lines.append(f"    📄 {file['name']} ({file['size']})")

            message_lines.append("")

        # Итоговая статистика
        message_lines.append("📈 <b>ИТОГОВАЯ СТАТИСТИКА:</b>")
        message_lines.append(f"  📦 <b>Всего файлов:</b> {len(files_sent)}")
        message_lines.append(f"  📊 <b>Общий размер:</b> {total_size_str}")

        # Статус отправки в Telegram
        if backup_info.get('complete_folder_sent'):
            telegram_status = "✅ Бэкапы отправлены"
        elif backup_info.get('telegram_sent'):
            telegram_status = "✅ Сводка отправлена"
        else:
            telegram_status = "⚠️ Ошибка отправки"

        message_lines.append(f"  📤 <b>Telegram:</b> {telegram_status}")

        message_lines.append("")

        # Заключение
        if success_count == 4:
            message_lines.append("🎉 <b>БЭКАП УСПЕШНО ЗАВЕРШЕН!</b>")
        else:
            message_lines.append(f"⚠️ <b>Бэкап завершен с ошибками: {success_count}/4</b>")

        # Разделитель
        message_lines.append("=" * 30)
        message_lines.append("⚡️ <i>Система Avito Profit Hub</i>")

        return "\n".join(message_lines)


class BackupManager:
    """🗄️ ПРОФЕССИОНАЛЬНЫЙ МЕНЕДЖЕР БЭКАПОВ ДЛЯ AVITO PROFIT HUB С ОТПРАВКОЙ АДМИНУ В TELEGRAM"""

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.backup_dir = self.base_dir / 'database_backups'
        self.media_backup_dir = self.backup_dir / 'media'
        self.logs_backup_dir = self.backup_dir / 'logs'

        # Инициализация Telegram отправителя
        self.telegram_sender = TelegramBackupSender()
        self.send_to_telegram = self.telegram_sender.token is not None and self.telegram_sender.admin_user_id is not None

        # Создаем директории
        self.backup_dir.mkdir(exist_ok=True)
        self.media_backup_dir.mkdir(exist_ok=True)
        self.logs_backup_dir.mkdir(exist_ok=True)

        # Настройки из Django
        self.db_settings = settings.DATABASES['default']

        logger.info(f"✅ Менеджер бэкапов инициализирован: {self.backup_dir}")
        if self.send_to_telegram:
            logger.info(f"✅ Отправка админу в Telegram активирована (ID: {self.telegram_sender.admin_user_id})")
        else:
            logger.info("ℹ️ Отправка в Telegram отключена")

    def _send_to_telegram(self, file_path: str, file_type: str) -> bool:
        """Отправляет файл бэкапа в Telegram админу"""
        if not self.send_to_telegram:
            return False

        try:
            if not os.path.exists(file_path):
                logger.error(f"❌ Файл для отправки не найден: {file_path}")
                return False

            filename = Path(file_path).name
            file_size = os.path.getsize(file_path)

            # Иконки для разных типов файлов
            icons = {
                'database': '🗄️',
                'media': '🖼️',
                'logs': '📝',
                'ml_models': '🧠',
                'База данных': '🗄️',
                'Медиа файлы': '🖼️',
                'Логи системы': '📝',
                'ML модели': '🧠'
            }

            icon = icons.get(file_type, '💾')

            caption = f"{icon} <b>БЭКАП {file_type.upper()}</b>\n"
            caption += f"📄 Файл: {filename}\n"
            caption += f"📊 Размер: {file_size / 1024:.1f}KB\n"
            caption += f"⏰ Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            success = self.telegram_sender.send_file(file_path, caption)

            if success:
                logger.info(f"📤 Файл отправлен админу в Telegram: {filename}")
            else:
                logger.warning(f"⚠️ Не удалось отправить файл админу: {filename}")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False

    def _send_complete_folder_to_telegram(self) -> bool:
        """Отправляет полную папку с бэкапами в Telegram админу - ТОЛЬКО ВАЖНОЕ"""
        if not self.send_to_telegram:
            return False

        try:
            logger.info("🎯 Отправляем только самые важные бэкапы:")

            # 1. Самый свежий бэкап БД
            db_files = sorted(self.backup_dir.glob("postgres_backup_*.sql.gz"),
                              key=lambda x: x.stat().st_mtime, reverse=True)
            latest_db = db_files[0] if db_files else None

            # 2. Самые свежие логи (сегодняшние)
            today = datetime.now().strftime("%Y%m%d")
            log_files = list(self.logs_backup_dir.glob(f"*backup_{today}*"))
            if not log_files:
                log_files = sorted(self.logs_backup_dir.glob("*backup_*"),
                                   key=lambda x: x.stat().st_mtime, reverse=True)[:1]

            # 3. Самые свежие ML модели
            ml_files = sorted(self.backup_dir.glob("ml_models_backup_*.tar.gz"),
                              key=lambda x: x.stat().st_mtime, reverse=True)[:1]

            # Собираем ТОЛЬКО 3 самых важных файла
            files_to_send = []
            if latest_db:
                files_to_send.append(latest_db)
            if log_files:
                files_to_send.append(log_files[0])
            if ml_files:
                files_to_send.append(ml_files[0])

            if not files_to_send:
                logger.warning("⚠️ Нет файлов для отправки")
                return False

            # Показываем что отправляем
            total_size = 0
            logger.info(f"📦 Отправляем {len(files_to_send)} файлов:")
            for file in files_to_send:
                size_mb = file.stat().st_size / 1024 / 1024
                total_size += file.stat().st_size
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                logger.info(f"   📄 {file.name} ({size_mb:.1f}MB) - {file_time.strftime('%H:%M:%S')}")

            logger.info(f"📊 Общий размер: {total_size / 1024 / 1024:.1f}MB")

            # Если меньше 15MB - отправляем архивом, иначе - по отдельности
            if total_size < 15 * 1024 * 1024:
                logger.info("📦 Объединяем файлы в один архив...")
                return self._send_folder_as_archive(files_to_send)
            else:
                logger.info("📦 Отправляем файлы по отдельности...")
                return self._send_files_separately(files_to_send)

        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
            return False

    def _send_folder_as_archive(self, files):
        """Отправляет файлы как единый архив"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_backup_dir = Path(tmpdir) / "backups"
                temp_backup_dir.mkdir()

                # Копируем файлы
                copy_progress = ProgressTracker(len(files), "📋 Копирование файлов")
                for i, file in enumerate(files):
                    if file.exists():
                        shutil.copy2(file, temp_backup_dir / file.name)
                        copy_progress.update(1)
                copy_progress.finish()

                # Создаем архив
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = f"full_backup_{timestamp}.tar.gz"
                archive_path = Path(tmpdir) / archive_name

                # Считаем общий размер
                total_size = sum(f.stat().st_size for f in files)
                archive_progress = ProgressTracker(total_size, "🗜️  Создание архива")

                import tarfile

                class ProgressTarFile(tarfile.TarFile):
                    """TarFile с отслеживанием прогресса"""

                    def add(self, name, arcname=None, recursive=True, *, filter=None):
                        if os.path.isfile(name):
                            file_size = os.path.getsize(name)
                            archive_progress.update(file_size)
                        super().add(name, arcname, recursive, filter=filter)

                with ProgressTarFile.open(archive_path, 'w:gz', compresslevel=6) as tar:
                    tar.add(temp_backup_dir, arcname="backups")

                archive_progress.finish()

                archive_size = archive_path.stat().st_size
                logger.info(f"📦 Архив создан: {archive_name} ({archive_size / 1024 / 1024:.1f}MB)")

                # Отправляем архив
                caption = f"📁 <b>ПОЛНЫЙ АРХИВ БЭКАПОВ</b>\n"
                caption += f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                caption += f"📊 Размер: {archive_size / 1024 / 1024:.1f}MB\n"
                caption += f"📦 Файлов: {len(files)}\n"
                caption += f"💾 Включает: БД, медиа, логи"

                return self.telegram_sender.send_file(str(archive_path), caption)

        except Exception as e:
            logger.error(f"❌ Ошибка создания архива: {e}")
            return False

    def _send_files_separately(self, files):
        """Отправляет файлы по отдельности"""
        try:
            success_count = 0
            file_types = {
                'postgres_backup': '🗄️ База данных',
                'media_backup': '🖼️ Медиа файлы',
                'logs_backup': '📝 Логи системы',
                'ml_models_backup': '🧠 ML модели'
            }

            # Общий прогресс бар
            total_progress = ProgressTracker(len(files), "📤 Отправка всех файлов")

            for i, file in enumerate(files, 1):
                filename = file.name

                # Определяем тип файла
                file_type = '💾 Другой файл'
                for key, value in file_types.items():
                    if key in filename:
                        file_type = value
                        break

                # Отправляем файл
                caption = f"{file_type}\n📄 {filename}\n📦 Файл {i}/{len(files)}"

                logger.info(f"📤 Отправка файла {i}/{len(files)}: {filename}")

                if self.telegram_sender.send_file(str(file), caption):
                    success_count += 1
                    logger.info(f"✅ Отправлен: {filename}")
                else:
                    logger.warning(f"⚠️ Не удалось отправить: {filename}")

                total_progress.update(1)

            total_progress.finish()

            logger.info(f"📊 Отправлено файлов: {success_count}/{len(files)}")
            return success_count > 0

        except Exception as e:
            logger.error(f"❌ Ошибка отправки файлов: {e}")
            return False

    def create_postgres_backup(self, compress=True, max_backups=10, send_to_telegram=True):
        """Создает бэкап PostgreSQL базы данных"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"postgres_backup_{timestamp}"
            sql_file = self.backup_dir / f"{backup_name}.sql"
            final_file = self.backup_dir / f"{backup_name}.sql.gz" if compress else sql_file

            logger.info(f"🔄 Создание бэкапа PostgreSQL: {backup_name}")

            # ПУТЬ К PG_DUMP (версия 17)
            pg_dump_path = r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe'

            # Команда
            cmd = [
                pg_dump_path,
                '-h', self.db_settings['HOST'],
                '-p', str(self.db_settings['PORT']),
                '-U', self.db_settings['USER'],
                '-d', self.db_settings['NAME'],
                '-f', str(sql_file),
                '-F', 'p',
                '--clean',
                '--if-exists',
                '--no-owner',
                '--no-privileges',
                '--inserts'
            ]

            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_settings['PASSWORD']

            logger.debug(f"Выполняем команду: {' '.join(cmd)}")

            # Запускаем pg_dump
            start_time = time.time()
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                shell=False
            )

            dump_time = time.time() - start_time

            if result.returncode != 0:
                logger.error(f"❌ Ошибка pg_dump: {result.stderr}")
                logger.info("🔄 Использую резервный метод psycopg2...")
                return self._create_backup_with_psycopg2(sql_file, final_file, compress, send_to_telegram)

            # Проверяем создался ли файл
            if not os.path.exists(sql_file):
                logger.error("❌ Файл бэкапа не создан!")
                return False

            dump_size = os.path.getsize(sql_file)
            logger.info(f"🗄️  Дамп БД создан за {dump_time:.1f}s ({dump_size / 1024 / 1024:.1f} MB)")

            # Сжатие с реальным прогрессом
            if compress:
                try:
                    compress_progress = ProgressTracker(dump_size, "🗜️  Сжатие дампа")

                    with open(sql_file, 'rb') as f_in:
                        with gzip.open(final_file, 'wb') as f_out:
                            chunk_size = 1024 * 1024
                            while True:
                                chunk = f_in.read(chunk_size)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                                compress_progress.update(len(chunk))

                    compress_progress.finish()

                    # Удаляем несжатый файл
                    os.remove(sql_file)
                    file_size = os.path.getsize(final_file)
                    backup_file_name = final_file.name
                    final_path = str(final_file)
                except Exception as e:
                    logger.error(f"❌ Ошибка сжатия: {e}")
                    file_size = os.path.getsize(sql_file)
                    backup_file_name = sql_file.name
                    final_path = str(sql_file)
            else:
                file_size = os.path.getsize(sql_file)
                backup_file_name = sql_file.name
                final_path = str(sql_file)

            # Отправка в Telegram
            if send_to_telegram and self.send_to_telegram:
                self._send_to_telegram(final_path, "База данных")

            # Очистка старых бэкапов
            self._cleanup_old_backups('postgres', max_backups)

            logger.info(f"✅ Бэкап PostgreSQL создан: {backup_file_name} ({file_size / 1024 / 1024:.1f} MB)")
            return final_path

        except Exception as e:
            logger.error(f"❌ Ошибка создания бэкапа PostgreSQL: {e}", exc_info=True)
            return False

    def _create_backup_with_psycopg2(self, sql_file, final_file, compress, send_to_telegram=True):
        """Резервный метод через psycopg2"""
        try:
            import psycopg2
            from psycopg2 import sql

            logger.info("🔄 Использую резервный метод бэкапа через psycopg2...")

            # Подключаемся к БД
            conn = psycopg2.connect(
                host=self.db_settings['HOST'],
                port=self.db_settings['PORT'],
                database=self.db_settings['NAME'],
                user=self.db_settings['USER'],
                password=self.db_settings['PASSWORD']
            )

            # Создаем дамп
            start_time = time.time()
            with open(sql_file, 'w', encoding='utf-8') as f:
                self._create_sql_dump(conn, f)

            dump_time = time.time() - start_time

            conn.close()

            dump_size = os.path.getsize(sql_file)
            logger.info(f"🗄️  Дамп через psycopg2 создан за {dump_time:.1f}s ({dump_size / 1024 / 1024:.1f} MB)")

            # Сжатие с реальным прогрессом
            if compress:
                compress_progress = ProgressTracker(dump_size, "🗜️  Сжатие дампа")

                with open(sql_file, 'rb') as f_in:
                    with gzip.open(final_file, 'wb') as f_out:
                        chunk_size = 1024 * 1024
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            compress_progress.update(len(chunk))

                compress_progress.finish()

                os.remove(sql_file)
                final_path = str(final_file)
            else:
                final_path = str(sql_file)

            # Отправка в Telegram
            if send_to_telegram and self.send_to_telegram:
                self._send_to_telegram(final_path, "База данных")

            return final_path

        except Exception as e:
            logger.error(f"❌ Ошибка psycopg2 бэкапа: {e}", exc_info=True)
            return False

    def _create_sql_dump(self, conn, file_obj):
        """Создает SQL дамп всей базы"""
        from psycopg2 import sql

        file_obj.write(f"-- PostgreSQL Backup created at {datetime.now()}\n")
        file_obj.write(f"-- Database: {self.db_settings['NAME']}\n\n")
        file_obj.write("BEGIN;\n\n")

        # Получаем все таблицы
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]

        total_tables = len(tables)
        logger.info(f"🗄️  Найдено таблиц для дампа: {total_tables}")

        # Дамп каждой таблицы
        for idx, table in enumerate(tables, 1):
            self._dump_table(conn, file_obj, table)

            # Логируем прогресс каждые 10 таблиц
            if idx % 10 == 0 or idx == total_tables:
                logger.info(f"🗄️  Обработано таблиц: {idx}/{total_tables}")

        file_obj.write("\nCOMMIT;\n")

    def _dump_table(self, conn, file_obj, table_name):
        """Дамп отдельной таблицы"""
        from psycopg2 import sql

        file_obj.write(f"\n-- Table: {table_name}\n")

        with conn.cursor() as cur:
            # Создаем таблицу
            cur.execute(sql.SQL("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """), [table_name])

            columns = cur.fetchall()

            file_obj.write(f"DROP TABLE IF EXISTS {table_name} CASCADE;\n")
            file_obj.write(f"CREATE TABLE {table_name} (\n")

            col_defs = []
            for col in columns:
                col_name, data_type, is_nullable, col_default = col
                col_def = f"    {col_name} {data_type}"
                if is_nullable == 'NO':
                    col_def += " NOT NULL"
                if col_default:
                    col_def += f" DEFAULT {col_default}"
                col_defs.append(col_def)

            file_obj.write(",\n".join(col_defs))
            file_obj.write("\n);\n\n")

            # Данные таблицы
            cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name)))
            rows = cur.fetchall()

            if rows:
                file_obj.write(f"-- Data: {len(rows)} rows\n")
                for row in rows:
                    values = []
                    for val in row:
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, str):
                            values.append("'" + val.replace("'", "''") + "'")
                        elif isinstance(val, datetime):
                            values.append("'" + val.strftime("%Y-%m-%d %H:%M:%S") + "'")
                        elif isinstance(val, bool):
                            values.append("TRUE" if val else "FALSE")
                        else:
                            values.append(str(val))

                    file_obj.write(f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n")

                file_obj.write("\n")

    def backup_media_files(self, send_to_telegram=True):
        """Бэкап медиа файлов"""
        try:
            media_dir = self.base_dir / 'media'
            if not media_dir.exists():
                logger.info("ℹ️ Папка media не найдена, пропускаем")
                return True

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            media_backup = self.media_backup_dir / f"media_backup_{timestamp}.tar.gz"

            logger.info(f"🖼️ Создание бэкапа медиа файлов: {media_backup.name}")

            # Считаем общий размер
            total_size = 0
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    total_size += os.path.getsize(filepath)

            # Создаем архив
            import tarfile

            archive_progress = ProgressTracker(total_size, "🖼️  Архивирование медиа")

            class ProgressTarFile(tarfile.TarFile):
                """TarFile с отслеживанием прогресса"""

                def add(self, name, arcname=None, recursive=True, *, filter=None):
                    if os.path.isfile(name):
                        file_size = os.path.getsize(name)
                        archive_progress.update(file_size)
                    super().add(name, arcname, recursive, filter=filter)

            with ProgressTarFile.open(media_backup, 'w:gz') as tar:
                tar.add(media_dir, arcname='media')

            archive_progress.finish()

            file_size = media_backup.stat().st_size

            # Отправка в Telegram
            if send_to_telegram and self.send_to_telegram:
                self._send_to_telegram(str(media_backup), "Медиа файлы")

            # Очистка старых бэкапов
            self._cleanup_old_backups('media', 7)

            logger.info(f"✅ Бэкап медиа создан: {media_backup.name} ({file_size / 1024 / 1024:.1f} MB)")
            return str(media_backup)

        except Exception as e:
            logger.error(f"❌ Ошибка бэкапа медиа файлов: {e}")
            return False

    def backup_logs(self, send_to_telegram=True):
        """Бэкап логов"""
        try:
            logs_dir = self.base_dir / 'logs'
            if not logs_dir.exists():
                logger.info("ℹ️ Папка logs не найдена, пропускаем")
                return True

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            logs_backup = self.logs_backup_dir / f"logs_backup_{timestamp}.tar.gz"

            logger.info(f"📝 Создание бэкапа логов: {logs_backup.name}")

            # Считаем общий размер
            total_size = 0
            for root, dirs, files in os.walk(logs_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    total_size += os.path.getsize(filepath)

            import tarfile

            archive_progress = ProgressTracker(total_size, "📝 Архивирование логов")

            class ProgressTarFile(tarfile.TarFile):
                def add(self, name, arcname=None, recursive=True, *, filter=None):
                    if os.path.isfile(name):
                        file_size = os.path.getsize(name)
                        archive_progress.update(file_size)
                    super().add(name, arcname, recursive, filter=filter)

            with ProgressTarFile.open(logs_backup, 'w:gz') as tar:
                tar.add(logs_dir, arcname='logs')

            archive_progress.finish()

            file_size = logs_backup.stat().st_size

            # Отправка в Telegram
            if send_to_telegram and self.send_to_telegram:
                self._send_to_telegram(str(logs_backup), "Логи системы")

            # Очистка старых бэкапов
            self._cleanup_old_backups('logs', 7)

            logger.info(f"✅ Бэкап логов создан: {logs_backup.name} ({file_size / 1024 / 1024:.1f} MB)")
            return str(logs_backup)

        except Exception as e:
            logger.error(f"❌ Ошибка бэкапа логов: {e}")
            return False

    def backup_ml_models(self, send_to_telegram=True):
        """Бэкап ML моделей"""
        try:
            ml_dir = self.base_dir / 'ml_models'
            if not ml_dir.exists():
                logger.info("ℹ️ Папка ml_models не найдена, пропускаем")
                return True

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ml_backup = self.backup_dir / f"ml_models_backup_{timestamp}.tar.gz"

            logger.info(f"🧠 Создание бэкапа ML моделей: {ml_backup.name}")

            # Считаем общий размер
            total_size = 0
            for root, dirs, files in os.walk(ml_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    total_size += os.path.getsize(filepath)

            import tarfile

            archive_progress = ProgressTracker(total_size, "🧠 Архивирование ML моделей")

            class ProgressTarFile(tarfile.TarFile):
                def add(self, name, arcname=None, recursive=True, *, filter=None):
                    if os.path.isfile(name):
                        file_size = os.path.getsize(name)
                        archive_progress.update(file_size)
                    super().add(name, arcname, recursive, filter=filter)

            with ProgressTarFile.open(ml_backup, 'w:gz') as tar:
                tar.add(ml_dir, arcname='ml_models')

            archive_progress.finish()

            file_size = ml_backup.stat().st_size

            # Отправка в Telegram
            if send_to_telegram and self.send_to_telegram:
                self._send_to_telegram(str(ml_backup), "ML модели")

            logger.info(f"✅ Бэкап ML моделей создан: {ml_backup.name} ({file_size / 1024 / 1024:.1f} MB)")
            return str(ml_backup)

        except Exception as e:
            logger.error(f"❌ Ошибка бэкапа ML моделей: {e}")
            return False

    def create_full_backup(self, send_to_telegram=True):
        """Создает полный бэкап всей системы с отправкой админу в Telegram"""
        logger.info("🚀 ЗАПУСК ПОЛНОГО БЭКАПА СИСТЕМЫ")

        if send_to_telegram and self.send_to_telegram:
            logger.info("📤 Бэкап будет отправлен админу в Telegram")

        results = {
            'database': False,
            'media': False,
            'logs': False,
            'ml_models': False,
            'telegram_sent': False,
            'complete_folder_sent': False,
            'timestamp': datetime.now().isoformat()
        }

        sent_files = []

        try:
            # Общий прогресс бар
            total_progress = ProgressTracker(4, "🚀 Полный бэкап системы")

            # 1. Бэкап базы данных
            logger.info("🗄️  ЭТАП 1: Бэкап базы данных")
            db_backup = self.create_postgres_backup(send_to_telegram=send_to_telegram)
            results['database'] = db_backup if db_backup else False
            if db_backup:
                sent_files.append(db_backup)
            total_progress.update(1)

            # 2. Бэкап медиа файлов
            logger.info("🖼️  ЭТАП 2: Бэкап медиа файлов")
            media_backup = self.backup_media_files(send_to_telegram=send_to_telegram)
            results['media'] = media_backup if media_backup else False
            if media_backup:
                sent_files.append(media_backup)
            total_progress.update(1)

            # 3. Бэкап логов
            logger.info("📝 ЭТАП 3: Бэкап логов системы")
            logs_backup = self.backup_logs(send_to_telegram=send_to_telegram)
            results['logs'] = logs_backup if logs_backup else False
            if logs_backup:
                sent_files.append(logs_backup)
            total_progress.update(1)

            # 4. Бэкап ML моделей
            logger.info("🧠 ЭТАП 4: Бэкап ML моделей")
            ml_backup = self.backup_ml_models(send_to_telegram=send_to_telegram)
            results['ml_models'] = ml_backup if ml_backup else False
            if ml_backup:
                sent_files.append(ml_backup)
            total_progress.update(1)

            total_progress.finish()

            # 5. Отправляем бэкапы админу
            if send_to_telegram and self.send_to_telegram and sent_files:
                logger.info("📤 ЭТАП 5: Отправка бэкапов админу в Telegram")

                folder_sent = self._send_complete_folder_to_telegram()
                results['complete_folder_sent'] = folder_sent

                # Отправляем КРАСИВУЮ сводку админу
                if folder_sent or sent_files:
                    logger.info("🎨 Формирование красивой сводки...")
                    self.telegram_sender.send_backup_summary(results, sent_files)
                    results['telegram_sent'] = True

            # Сохраняем информацию о бэкапе
            backup_info = self.backup_dir / f"backup_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_info, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)

            # Статистика
            success_count = sum(1 for k, v in results.items()
                                if v and k not in ['timestamp', 'telegram_sent', 'complete_folder_sent'])

            logger.info("📊 ИТОГИ БЭКАПА")
            logger.info(f"✅ Успешно: {success_count}/4")

            # Детальная статистика
            for key, label in [('database', '🗄️  База данных'),
                               ('media', '🖼️  Медиа файлы'),
                               ('logs', '📝 Логи системы'),
                               ('ml_models', '🧠 ML модели')]:
                if results.get(key):
                    logger.info(f"  {label}: ✅ УСПЕХ")
                else:
                    logger.info(f"  {label}: ❌ ОШИБКА")

            if send_to_telegram and self.send_to_telegram:
                if results.get('complete_folder_sent'):
                    logger.info("✅ Бэкапы отправлены админу")
                else:
                    logger.warning("⚠️ Не удалось отправить бэкапы админу")

            if success_count == 4:
                logger.info("🎉 ПОЛНЫЙ БЭКАП УСПЕШНО ЗАВЕРШЕН!")
            else:
                logger.warning(f"⚠️ Бэкап завершен с ошибками: {success_count}/4")

            return results

        except Exception as e:
            logger.error(f"❌ Критическая ошибка полного бэкапа: {e}", exc_info=True)
            return results

    def _cleanup_old_backups(self, backup_type, keep_count):
        """Очистка старых бэкапов"""
        try:
            if backup_type == 'postgres':
                pattern = "postgres_backup_*.sql.gz"
                target_dir = self.backup_dir
            elif backup_type == 'media':
                pattern = "media_backup_*.tar.gz"
                target_dir = self.media_backup_dir
            elif backup_type == 'logs':
                pattern = "logs_backup_*.tar.gz"
                target_dir = self.logs_backup_dir
            else:
                return

            backups = list(target_dir.glob(pattern))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            if len(backups) > keep_count:
                cleanup_progress = ProgressTracker(len(backups) - keep_count, "🧹 Очистка старых бэкапов")

                for backup in backups[keep_count:]:
                    try:
                        backup.unlink()
                        logger.debug(f"🧹 Удален старый бэкап: {backup.name}")
                        cleanup_progress.update(1)
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось удалить {backup.name}: {e}")

                cleanup_progress.finish()

        except Exception as e:
            logger.error(f"❌ Ошибка очистки бэкапов: {e}")

    def list_backups(self):
        """Список всех бэкапов"""
        backups = {
            'database': [],
            'media': [],
            'logs': [],
            'ml_models': []
        }

        # Бэкапы БД
        for file in self.backup_dir.glob("postgres_backup_*.sql.gz"):
            stat = file.stat()
            backups['database'].append({
                'name': file.name,
                'size': stat.st_size,
                'size_mb': stat.st_size / 1024 / 1024,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'path': str(file)
            })

        # Бэкапы медиа
        for file in self.media_backup_dir.glob("media_backup_*.tar.gz"):
            stat = file.stat()
            backups['media'].append({
                'name': file.name,
                'size': stat.st_size,
                'size_mb': stat.st_size / 1024 / 1024,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'path': str(file)
            })

        # Сортируем по дате
        for key in backups:
            backups[key].sort(key=lambda x: x['modified'], reverse=True)

        return backups

    def restore_database(self, backup_file):
        """Восстановление базы данных из бэкапа"""
        try:
            if not os.path.exists(backup_file):
                logger.error(f"❌ Файл бэкапа не найден: {backup_file}")
                return False

            logger.info(f"🔄 Восстановление БД из: {backup_file}")

            # Распаковываем если сжатый
            if backup_file.endswith('.gz'):
                import tempfile
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sql') as tmp:
                    with gzip.open(backup_file, 'rb') as f_in:
                        chunk_size = 1024 * 1024
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            tmp.write(chunk)

                    sql_file = tmp.name
            else:
                sql_file = backup_file

            # Восстанавливаем через psql
            cmd = [
                'psql',
                '-h', self.db_settings['HOST'],
                '-p', str(self.db_settings['PORT']),
                '-U', self.db_settings['USER'],
                '-d', self.db_settings['NAME'],
                '-f', sql_file
            ]

            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_settings['PASSWORD']

            start_time = time.time()
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                shell=True
            )
            restore_time = time.time() - start_time

            if backup_file.endswith('.gz'):
                os.unlink(sql_file)

            if result.returncode == 0:
                logger.info(f"✅ База данных успешно восстановлена за {restore_time:.1f}s!")
                return True
            else:
                logger.error(f"❌ Ошибка восстановления: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка восстановления БД: {e}", exc_info=True)
            return False


# Синглтон экземпляр для удобного использования
backup_manager = BackupManager()


# Утилитарные функции для обратной совместимости
def create_backup(send_to_telegram=True):
    """Создание резервной копии базы данных"""
    return backup_manager.create_postgres_backup(send_to_telegram=send_to_telegram)


def create_full_backup(send_to_telegram=True):
    """Создание полного бэкапа системы"""
    return backup_manager.create_full_backup(send_to_telegram=send_to_telegram)


def list_backups():
    """Список всех бэкапов"""
    return backup_manager.list_backups()