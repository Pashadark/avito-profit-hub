import os
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class DatabaseSecurity:
    def __init__(self, db_path='db.sqlite3'):
        self.db_path = db_path
        self.key = self._generate_key()

    def _generate_key(self):
        """Генерирует ключ шифрования на основе секретного ключа Django"""
        try:
            from django.conf import settings
            secret_key = settings.SECRET_KEY.encode()
        except:
            # Если не можем получить SECRET_KEY, используем фиксированный ключ для демо
            secret_key = b'default_secret_key_for_demo_purposes_only'

        salt = b'database_security_salt_12345'

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        return key

    def encrypt_database(self):
        """Шифрует файл базы данных"""
        try:
            if not os.path.exists(self.db_path):
                return False

            # Создаем резервную копию перед шифрованием
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f'database_backups/pre_encryption_backup_{backup_time}.sqlite3'
            shutil.copy2(self.db_path, backup_path)

            with open(self.db_path, 'rb') as file:
                data = file.read()

            fernet = Fernet(self.key)
            encrypted_data = fernet.encrypt(data)

            # Сохраняем зашифрованную версию
            encrypted_path = self.db_path + '.encrypted'
            with open(encrypted_path, 'wb') as file:
                file.write(encrypted_data)

            add_to_console(f"✅ База данных зашифрована: {encrypted_path}")
            return True
        except Exception as e:
            add_to_console(f"❌ Ошибка шифрования: {e}")
            return False

    def decrypt_database(self):
        """Расшифровывает файл базы данных"""
        try:
            encrypted_path = self.db_path + '.encrypted'

            if not os.path.exists(encrypted_path):
                print("❌ Зашифрованный файл не найден")
                return False

            with open(encrypted_path, 'rb') as file:
                encrypted_data = file.read()

            fernet = Fernet(self.key)
            decrypted_data = fernet.decrypt(encrypted_data)

            # Создаем резервную копию зашифрованного файла
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f'database_backups/encrypted_backup_{backup_time}.sqlite3.encrypted'
            shutil.copy2(encrypted_path, backup_path)

            # Восстанавливаем оригинальную базу
            with open(self.db_path, 'wb') as file:
                file.write(decrypted_data)

            add_to_console(f"✅ База данных расшифрована: {self.db_path}")
            return True
        except Exception as e:
            add_to_console(f"❌ Ошибка дешифрования: {e}")
            return False

    def create_emergency_backup(self):
        """Создает экстренную резервную копию с шифрованием"""
        try:
            if not os.path.exists(self.db_path):
                return False

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            emergency_backup = f'database_backups/emergency_backup_{timestamp}.sqlite3'

            # Создаем папку для бэкапов если ее нет
            if not os.path.exists('database_backups'):
                os.makedirs('database_backups')

            # Создаем резервную копию
            shutil.copy2(self.db_path, emergency_backup)

            # Шифруем бэкап
            return self.encrypt_file(emergency_backup)
        except Exception as e:
            add_to_console(f"❌ Ошибка создания экстренного бэкапа: {e}")
            return False

    def encrypt_file(self, file_path):
        """Шифрует указанный файл"""
        try:
            if not os.path.exists(file_path):
                return False

            with open(file_path, 'rb') as file:
                data = file.read()

            fernet = Fernet(self.key)
            encrypted_data = fernet.encrypt(data)

            encrypted_path = file_path + '.encrypted'
            with open(encrypted_path, 'wb') as file:
                file.write(encrypted_data)

            # Удаляем оригинальный незашифрованный файл
            os.remove(file_path)
            add_to_console(f"✅ Файл зашифрован: {encrypted_path}")
            return True
        except Exception as e:
            add_to_console(f"❌ Ошибка шифрования файла: {e}")
            return False

    def decrypt_file(self, encrypted_file_path):
        """Расшифровывает указанный файл"""
        try:
            if not os.path.exists(encrypted_file_path):
                return False

            with open(encrypted_file_path, 'rb') as file:
                encrypted_data = file.read()

            fernet = Fernet(self.key)
            decrypted_data = fernet.decrypt(encrypted_data)

            # Восстанавливаем оригинальный файл (убираем .encrypted расширение)
            original_path = encrypted_file_path.replace('.encrypted', '')
            with open(original_path, 'wb') as file:
                file.write(decrypted_data)

            add_to_console(f"✅ Файл расшифрован: {original_path}")
            return True
        except Exception as e:
            add_to_console(f"❌ Ошибка дешифрования файла: {e}")
            return False