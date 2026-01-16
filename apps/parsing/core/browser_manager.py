import time
import logging
import requests
import zipfile
import subprocess
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ✅ Создаем логгер для менеджера браузера
logger = logging.getLogger('parser.browser')


class ProductionDriverManager:
    """🚀 УМНЫЙ МЕНЕДЖЕР ДРАЙВЕРОВ ДЛЯ ПРОДАКШЕНА"""

    def __init__(self):
        self.local_driver = "chromedriver.exe"
        self.current_version = None

    def get_service(self):
        """Основной метод - возвращает Service с правильным драйвером"""
        try:
            # 1. Пробуем WebDriverManager с явными параметрами
            try:
                driver_path = self._try_webdriver_manager()
                return Service(driver_path)
            except Exception as wdm_error:
                logger.warning(f"⚠️ WebDriverManager не сработал: {wdm_error}")

            # 2. Проверяем локальный драйвер
            if self._check_local_driver():
                logger.info(f"✅ Использую локальный драйвер: {self.local_driver}")
                return Service(self.local_driver)

            # 3. Скачиваем драйвер напрямую
            logger.info("🔄 Скачиваю драйвер напрямую...")
            driver_path = self._download_driver_directly()
            return Service(driver_path)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка менеджера драйверов: {e}")
            # Последняя попытка - самый простой вариант
            if os.path.exists(self.local_driver):
                return Service(self.local_driver)
            raise

    def _try_webdriver_manager(self):
        """Пробуем WebDriverManager с правильными настройками"""
        from webdriver_manager.core.os_manager import ChromeType

        # 🔥 ИСПРАВЛЕННЫЙ КОД: простой вызов без лишних параметров
        driver_path = ChromeDriverManager().install()

        logger.info(f"✅ WebDriverManager нашел драйвер: {driver_path}")
        self.current_version = "143.0.7499.146"

        # Копируем драйвер локально для резервной копии
        self._backup_driver(driver_path)

        return driver_path

    def _check_local_driver(self):
        """Проверяем локальный драйвер"""
        if not os.path.exists(self.local_driver):
            return False

        # Проверяем, не пустой ли файл
        if os.path.getsize(self.local_driver) < 1024 * 100:  # Меньше 100KB
            logger.warning(f"⚠️ Локальный драйвер слишком маленький, перекачаю")
            os.remove(self.local_driver)
            return False

        return True

    def _download_driver_directly(self):
        """Скачивает драйвер напрямую с Google"""
        try:
            # URL для Chrome 143.0.7499.146
            download_url = "https://storage.googleapis.com/chrome-for-testing-public/143.0.7499.146/win64/chromedriver-win64.zip"

            logger.info(f"📥 Скачиваю драйвер с: {download_url}")

            # Скачиваем
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()

            # Сохраняем временный архив
            temp_zip = "chromedriver_temp.zip"
            with open(temp_zip, "wb") as f:
                f.write(response.content)

            # Распаковываем
            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                zip_ref.extractall(".")

            # Находим и переименовываем драйвер
            extracted_dir = "chromedriver-win64"
            if os.path.exists(os.path.join(extracted_dir, "chromedriver.exe")):
                os.rename(
                    os.path.join(extracted_dir, "chromedriver.exe"),
                    self.local_driver
                )
            elif os.path.exists("chromedriver.exe"):
                os.rename("chromedriver.exe", self.local_driver)

            # Очистка
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            if os.path.exists(extracted_dir):
                import shutil
                shutil.rmtree(extracted_dir)

            logger.info(f"✅ Драйвер скачан: {self.local_driver}")
            self.current_version = "143.0.7499.146"

            return self.local_driver

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки драйвера: {e}")
            raise

    def _backup_driver(self, source_path):
        """Создает резервную копию драйвера"""
        try:
            if os.path.exists(source_path):
                import shutil
                shutil.copy2(source_path, self.local_driver)
                logger.info(f"📁 Создана резервная копия драйвера")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать резервную копию: {e}")

    def clear_cache(self):
        """Очищает кеш WebDriverManager"""
        try:
            wdm_cache = os.path.expanduser("~/.wdm")
            if os.path.exists(wdm_cache):
                import shutil
                shutil.rmtree(wdm_cache)
                logger.info("🧹 Кеш WebDriverManager очищен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось очистить кеш: {e}")


# 🔧 Инициализируем менеджер драйверов один раз
_driver_manager = ProductionDriverManager()


class BrowserManager:
    def __init__(self):
        self.drivers = []
        self.browser_windows = 1

    def set_browser_windows(self, count):
        self.browser_windows = max(1, min(5, count))
        logger.info(f"🔄 Установлено окон: {self.browser_windows}")

    def create_driver(self, window_index=0):
        """СОЗДАНИЕ ДРАЙВЕРА С USER-AGENT"""
        try:
            chrome_options = Options()

            # ОСНОВНЫЕ ПАРАМЕТРЫ
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')

            # 🔥 ПРОСТОЙ И НАДЕЖНЫЙ ВАРИАНТ - используем локальный драйвер
            # Проверяем, есть ли chromedriver.exe в папке
            if not os.path.exists("chromedriver.exe"):
                logger.warning("⚠️ chromedriver.exe не найден, скачиваю...")
                _driver_manager._download_driver_directly()

            service = Service("chromedriver.exe")

            try:
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logger.error(f"❌ Ошибка создания драйвера с options: {e}")
                # Пробуем без options
                driver = webdriver.Chrome(service=service)

            # 🔥 ДОБАВИТЬ: Сразу применяем User-Agent после создания драйвера
            try:
                from apps.parsing.utils.custom_user_agents import apply_user_agent_to_driver
                user_agent = apply_user_agent_to_driver(driver, window_index + 1)
                if user_agent:
                    logger.info(f"✅ Окно {window_index + 1} | User-Agent установлен при создании")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось установить User-Agent при создании драйвера: {e}")

            logger.info(f"✅ Окно {window_index + 1} создано")
            return driver

        except Exception as e:
            logger.error(f"❌ Ошибка создания драйвера: {e}")
            return None

    def test_driver(self):
        """Тестирует подключение драйвера"""
        try:
            logger.info("🧪 Тестирую драйвер...")
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')

            if not os.path.exists("chromedriver.exe"):
                logger.warning("⚠️ chromedriver.exe не найден, скачиваю...")
                _driver_manager._download_driver_directly()

            service = Service("chromedriver.exe")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://www.google.com")
            title = driver.title
            driver.quit()

            logger.info(f"✅ Тест пройден! Страница: {title}")
            return True
        except Exception as e:
            logger.error(f"❌ Тест не пройден: {e}")
            return False

    def setup_drivers(self):
        try:
            self.close_drivers()
            logger.info("🚀 Запуск браузера...")

            driver = self.create_driver()
            if driver:
                self.drivers.append(driver)
                logger.info("✅ Браузер запущен успешно!")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            return False

    def get_driver(self, index=0):
        if self.drivers and 0 <= index < len(self.drivers):
            return self.drivers[index]
        return None

    def close_drivers(self):
        """🧹 НОРМАЛЬНОЕ ЗАКРЫТИЕ ДРАЙВЕРОВ"""
        for driver in self.drivers:
            try:
                driver.quit()
            except:
                pass
        self.drivers = []
        logger.info("✅ Все окна закрыты")

    def close_drivers_force(self):
        """💀 ПРИНУДИТЕЛЬНОЕ ЗАКРЫТИЕ ДРАЙВЕРОВ С УБИЙСТВОМ ПРОЦЕССОВ"""
        try:
            logger.info("💀 Принудительное закрытие драйверов...")

            # 1. Пытаемся закрыть нормально
            self.close_drivers()

            # 2. Убиваем процессы браузера
            self._kill_browser_processes()

            # 3. Дополнительная очистка
            self.drivers = []

            logger.info("✅ Драйверы принудительно закрыты")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка принудительного закрытия: {e}")
            return False

    def _kill_browser_processes(self):
        """💀 УБИЙСТВО ПРОЦЕССОВ БРАУЗЕРА И ХРОМДРАЙВЕРА"""
        try:
            if os.name == 'nt':  # Windows
                # Убиваем Chrome процессы
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
                               capture_output=True, timeout=10)
                # Убиваем ChromeDriver процессы
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'],
                               capture_output=True, timeout=10)
                # Убиваем по портам (дополнительно)
                subprocess.run(['netstat', '-ano'], capture_output=True)

            else:  # Linux/Mac
                subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                subprocess.run(['pkill', '-f', 'chromedriver'], capture_output=True)

            logger.info("💀 Процессы браузера принудительно завершены")

        except Exception as e:
            logger.error(f"❌ Ошибка завершения процессов: {e}")

    def close_driver_force(self, index=0):
        """💀 ПРИНУДИТЕЛЬНОЕ ЗАКРЫТИЕ КОНКРЕТНОГО ДРАЙВЕРА"""
        try:
            if 0 <= index < len(self.drivers):
                driver = self.drivers[index]
                try:
                    driver.quit()
                except:
                    try:
                        driver.close()
                    except:
                        pass

                # Удаляем из списка
                self.drivers.pop(index)
                logger.info(f"💀 Драйвер {index + 1} принудительно закрыт")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Ошибка принудительного закрытия драйвера {index + 1}: {e}")
            return False

    def is_any_driver_alive(self):
        """🔍 ПРОВЕРКА, ЕСТЬ ЛИ ЖИВЫЕ ДРАЙВЕРЫ"""
        try:
            for i, driver in enumerate(self.drivers):
                try:
                    # Простая проверка - пытаемся получить заголовок
                    driver.title
                    return True
                except:
                    logger.warning(f"⚠️ Драйвер {i + 1} не отвечает")
            return False
        except:
            return False

    def emergency_cleanup(self):
        """🚨 АВАРИЙНАЯ ОЧИСТКА ВСЕХ РЕСУРСОВ"""
        try:
            logger.warning("🚨 ЗАПУСК АВАРИЙНОЙ ОЧИСТКИ!")

            # 1. Быстро закрываем драйверы без исключений
            for driver in self.drivers:
                try:
                    driver.quit()
                except:
                    try:
                        driver.close()
                    except:
                        pass

            # 2. Немедленно убиваем процессы
            self._kill_browser_processes()

            # 3. Полная очистка списка
            self.drivers.clear()

            # 4. Дополнительная пауза для гарантии
            time.sleep(2)

            # 5. Повторное убийство процессов на всякий случай
            self._kill_browser_processes()

            logger.warning("🚨 АВАРИЙНАЯ ОЧИСТКА ЗАВЕРШЕНА")
            return True

        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ АВАРИЙНОЙ ОЧИСТКЕ: {e}")
            return False

    @property
    def driver(self):
        return self.get_driver(0)

    def restart_driver(self, index=0):
        """Перезапускает драйвер по индексу"""
        try:
            if 0 <= index < len(self.drivers):
                try:
                    self.drivers[index].quit()
                except:
                    pass

                new_driver = self.create_driver(index)
                if new_driver:
                    self.drivers[index] = new_driver
                    logger.info(f"🔄 Драйвер {index + 1} перезапущен")
                    return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка перезапуска драйвера {index + 1}: {e}")
            return False

    def get_drivers_count(self):
        """Возвращает количество активных драйверов"""
        return len(self.drivers)

    def is_driver_healthy(self, index=0):
        """Проверяет здоровье драйвера"""
        try:
            driver = self.get_driver(index)
            if driver:
                # Простая проверка - пытаемся получить текущий URL
                driver.current_url
                return True
            return False
        except:
            logger.warning(f"⚠️ Драйвер {index + 1} не отвечает")
            return False

    def setup_multiple_drivers(self):
        """Настраивает несколько драйверов для параллельной работы"""
        try:
            self.close_drivers()
            logger.info(f"🚀 Запуск {self.browser_windows} окон браузера...")

            success_count = 0
            for i in range(self.browser_windows):
                driver = self.create_driver(i)
                if driver:
                    self.drivers.append(driver)
                    success_count += 1
                    # Небольшая пауза между созданием драйверов
                    time.sleep(1)

            if success_count > 0:
                logger.info(f"✅ Успешно запущено {success_count}/{self.browser_windows} окон браузера")
                return True
            else:
                logger.error("❌ Не удалось запустить ни одного драйвера")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка настройки нескольких драйверов: {e}")
            return False


def force_update_chromedriver():
    """Принудительное обновление chromedriver"""
    print("🔄 Принудительное обновление chromedriver...")

    # Очищаем кеш
    _driver_manager.clear_cache()

    # Удаляем старый драйвер если есть
    if os.path.exists("chromedriver.exe"):
        os.remove("chromedriver.exe")
        print("🧹 Старый драйвер удален")

    # Скачиваем новый
    try:
        driver_path = _driver_manager._download_driver_directly()
        print(f"✅ Новый драйвер скачан: {driver_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def quick_test():
    """Быстрый тест драйвера"""
    print("🧪 Быстрый тест драйвера...")

    # Убедимся что драйвер есть
    if not os.path.exists("chromedriver.exe"):
        print("⚠️ chromedriver.exe не найден, скачиваю...")
        force_update_chromedriver()

    if os.path.exists("chromedriver.exe"):
        print(f"✅ Драйвер найден, размер: {os.path.getsize('chromedriver.exe') // 1024} KB")

        # Простой тест
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')

            service = Service("chromedriver.exe")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://www.google.com")
            print(f"✅ Тест пройден! Заголовок: {driver.title}")
            driver.quit()
            return True
        except Exception as e:
            print(f"❌ Ошибка теста: {e}")
            return False
    else:
        print("❌ Драйвер не найден после загрузки")
        return False


# Автопроверка при импорте
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if quick_test():
        print("🎉 ВСЁ РАБОТАЕТ! Парсер готов к запуску.")
        print("\n📋 Инструкция:")
        print("1. Этот файл уже содержит исправленный код")
        print("2. Драйвер chromedriver.exe будет автоматически скачан")
        print("3. Запустите ваш парсер как обычно")
    else:
        print("❌ Что-то пошло не так, проверьте ошибку выше")