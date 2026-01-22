"""
🚀 ПРОФЕССИОНАЛЬНЫЙ ПУЛ ДРАЙВЕРОВ ДЛЯ НАСТОЯЩЕЙ ПАРАЛЛЕЛЬНОСТИ
Каждый процесс = отдельный драйвер = отдельный GIL = отдельное ядро CPU
"""

import multiprocessing
from multiprocessing import Process, Queue, Manager
from queue import Empty
import time
import logging
import json
import re
import random
from urllib.parse import quote
from datetime import datetime
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Selenium импорты
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger('parser.driver_pool')


class DriverConfig:
    """Конфигурация для каждого воркера"""

    def __init__(self, worker_id=0):
        self.worker_id = worker_id
        self.headless = False
        self.window_size = "1920,1080"
        self.timeout_page_load = 30
        self.timeout_element = 10
        self.disable_images = True
        self.city = "Москва"
        self.site = "avito"
        self.user_agent = self._get_smart_user_agent()

    def _get_smart_user_agent(self):
        """Получает умный User-Agent из твоего модуля или использует фоллбэк"""
        try:
            # Пробуем импортировать твой модуль User-Agent
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from apps.parsing.utils.custom_user_agents import get_random_user_agent, get_smart_user_agent

            # Попробуем умный агент
            user_agent = get_smart_user_agent(self.worker_id, None)
            if user_agent:
                return user_agent

            # Или случайный
            user_agent = get_random_user_agent()
            if user_agent:
                return user_agent

        except Exception as e:
            pass

        # Фоллбэк агенты если твой модуль недоступен
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(agents)


def create_driver(config):
    """Создает драйвер для воркера"""
    try:
        chrome_options = Options()

        # Основные настройки безопасности
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Стелс-режим для обхода обнаружения
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Оптимизация скорости
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")

        if config.disable_images:
            chrome_options.add_argument("--blink-settings=imagesEnabled=false")

        # Настройки окна
        chrome_options.add_argument(f"--window-size={config.window_size}")
        chrome_options.add_argument("--start-maximized")

        # User-Agent
        chrome_options.add_argument(f"--user-agent={config.user_agent}")

        # Создаем драйвер
        driver = webdriver.Chrome(options=chrome_options)

        # Настройки таймаутов
        driver.set_page_load_timeout(config.timeout_page_load)
        driver.implicitly_wait(config.timeout_element)
        driver.set_script_timeout(15)

        # Скрываем WebDriver признаки
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": config.user_agent,
            "platform": "Win32"
        })

        return driver

    except Exception as e:
        print(f"❌ [Процесс {config.worker_id}] Ошибка создания драйвера: {e}")
        return None


def driver_worker(worker_id, config_dict, task_queue, result_queue, status_dict):
    """
    🏭 ОСНОВНОЙ РАБОЧИЙ ПРОЦЕСС
    Каждый такой процесс = отдельное ядро CPU
    """
    # Настраиваем логирование для процесса
    logging.basicConfig(
        level=logging.INFO,
        format=f'[Процесс {worker_id}] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    worker_logger = logging.getLogger(f'worker_{worker_id}')

    worker_logger.info(f"🚀 Процесс {worker_id} запущен (PID: {os.getpid()})")

    driver = None
    parser = None

    try:
        # 🔥 ШАГ 1: СОЗДАЕМ ДРАЙВЕР
        worker_logger.info("🛠️ Создаю драйвер...")

        config = DriverConfig(worker_id)
        config.__dict__.update(config_dict)

        driver = create_driver(config)

        if not driver:
            worker_logger.error("❌ Не удалось создать драйвер")
            status_dict[f'worker_{worker_id}'] = 'ERROR'
            return

        # 🔥 ШАГ 2: ИМПОРТИРУЕМ И СОЗДАЕМ ПАРСЕР
        worker_logger.info("📦 Импортируем AvitoParser...")

        try:
            from apps.parsing.sites.avito_parser import AvitoParser
            parser = AvitoParser(driver, city=config.city)
            worker_logger.info(f"✅ AvitoParser создан для города: {config.city}")
        except ImportError as e:
            worker_logger.error(f"❌ Не удалось импортировать AvitoParser: {e}")
            status_dict[f'worker_{worker_id}'] = 'ERROR'
            return
        except Exception as e:
            worker_logger.error(f"❌ Ошибка создания парсера: {e}")
            status_dict[f'worker_{worker_id}'] = 'ERROR'
            return

        # 🔥 ШАГ 3: СТАРТУЕМ - ОТКРЫВАЕМ САЙТ
        worker_logger.info("🌐 Открываем Avito для теста...")

        try:
            driver.get("https://www.avito.ru")
            time.sleep(2)
            current_title = driver.title
            worker_logger.info(f"✅ Avito открыт: {current_title[:50]}")
        except Exception as e:
            worker_logger.warning(f"⚠️ Не удалось открыть Avito: {e}")

        status_dict[f'worker_{worker_id}'] = 'READY'
        worker_logger.info("✅ Готов к работе! Жду задачи...")

        # 🔥 ШАГ 4: ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ ЗАДАЧ
        while True:
            try:
                # Получаем задачу (блокируемся максимум 1 секунду)
                task = task_queue.get(timeout=1)

                if task is None:  # Команда остановки
                    worker_logger.info("🛑 Получена команда остановки")
                    break

                task_type = task.get('type', 'UNKNOWN')
                task_id = task.get('task_id', f'task_{worker_id}_{int(time.time())}')
                task_data = task.get('data', {})

                worker_logger.info(f"📥 Получена задача: {task_type} (ID: {task_id})")

                # ОБРАБОТКА ЗАДАЧ
                if task_type == 'SEARCH':
                    # Задача поиска товаров
                    query = task_data.get('query', '')
                    max_items = task_data.get('max_items', 20)
                    city = task_data.get('city', config.city)

                    worker_logger.info(f"🔍 Поиск: '{query}' (макс: {max_items} товаров)")

                    result = {
                        'task_id': task_id,
                        'type': task_type,
                        'success': False,
                        'worker_id': worker_id,
                        'process_pid': os.getpid(),
                        'data': {
                            'query': query,
                            'city': city,
                            'products': [],
                            'error': None
                        }
                    }

                    try:
                        # 🔥 ВАЖНО: РАБОТАЕМ ТОЛЬКО С ПАРСЕРОМ - никаких asyncio!
                        products = parser.search_items(query, max_items=max_items)

                        if products:
                            result['success'] = True
                            result['data']['products'] = products
                            result['data']['count'] = len(products)
                            worker_logger.info(f"✅ Нашёл {len(products)} товаров по запросу '{query}'")
                        else:
                            result['data']['error'] = 'Товары не найдены'
                            worker_logger.info(f"⚠️ Товары не найдены по запросу '{query}'")

                    except Exception as e:
                        worker_logger.error(f"❌ Ошибка поиска: {e}")
                        result['data']['error'] = str(e)

                    # Отправляем результат
                    result_queue.put(result)

                elif task_type == 'GET_DETAILS':
                    # Задача получения деталей товара
                    product_data = task_data.get('product', {})

                    result = {
                        'task_id': task_id,
                        'type': task_type,
                        'success': False,
                        'worker_id': worker_id,
                        'process_pid': os.getpid(),
                        'data': {
                            'product_details': None,
                            'error': None
                        }
                    }

                    try:
                        # Получаем детали
                        details = parser.get_product_details(product_data)

                        if details:
                            result['success'] = True
                            result['data']['product_details'] = details
                            worker_logger.info(f"✅ Детали товара получены")
                        else:
                            result['data']['error'] = 'Не удалось получить детали'
                            worker_logger.warning(f"⚠️ Не удалось получить детали товара")

                    except Exception as e:
                        worker_logger.error(f"❌ Ошибка получения деталей: {e}")
                        result['data']['error'] = str(e)

                    # Отправляем результат
                    result_queue.put(result)

                elif task_type == 'HEALTH_CHECK':
                    # Проверка здоровья
                    try:
                        # Простая проверка что драйвер жив
                        driver.current_url
                        health_status = 'HEALTHY'
                    except:
                        health_status = 'DEAD'

                    result_queue.put({
                        'task_id': task_id,
                        'type': task_type,
                        'success': health_status == 'HEALTHY',
                        'worker_id': worker_id,
                        'process_pid': os.getpid(),
                        'data': {'status': health_status}
                    })

                else:
                    worker_logger.warning(f"⚠️ Неизвестный тип задачи: {task_type}")

            except Empty:
                # Нет задач в очереди - продолжаем ждать
                continue
            except Exception as e:
                worker_logger.error(f"❌ Критическая ошибка в цикле обработки: {e}")
                time.sleep(1)  # Небольшая пауза при ошибке

    except Exception as e:
        worker_logger.error(f"💥 Критическая ошибка воркера: {e}")

    finally:
        # 🔥 ОЧИСТКА РЕСУРСОВ
        worker_logger.info("🧹 Очистка ресурсов...")

        if driver:
            try:
                driver.quit()
                worker_logger.info("✅ Драйвер закрыт")
            except:
                pass

        status_dict[f'worker_{worker_id}'] = 'STOPPED'
        worker_logger.info(f"🏁 Процесс {worker_id} завершен")


class DriverPool:
    """🚀 ПУЛ ДРАЙВЕРОВ ДЛЯ НАСТОЯЩЕЙ ПАРАЛЛЕЛЬНОСТИ"""

    def __init__(self, num_workers=3):
        self.num_workers = num_workers
        self.workers = []
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.manager = Manager()
        self.status = self.manager.dict()  # Общий статус через Manager

        self.stats = {
            'total_workers': num_workers,
            'active_workers': 0,
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'errors': 0
        }

        logger.info(f"🚀 Инициализация пула из {num_workers} процессов...")

    def start(self):
        """Запускает все процессы"""
        try:
            # 🔥 Сначала убиваем все старые процессы Chrome
            self._kill_stale_chrome_processes()

            for i in range(self.num_workers):
                # Конфигурация для каждого воркера
                config = {
                    'worker_id': i,
                    'headless': False,
                    'city': 'Москва',
                    'disable_images': True,
                    'window_size': '1920,1080'
                }

                # 🔥 СОЗДАЕМ ОТДЕЛЬНЫЙ ПРОЦЕСС!
                process = Process(
                    target=driver_worker,
                    args=(i, config, self.task_queue, self.result_queue, self.status),
                    name=f'DriverWorker_{i}',
                    daemon=False  # Важно: False чтобы процессы не умирали с родителем
                )

                process.start()
                self.workers.append(process)
                self.status[f'worker_{i}'] = 'STARTING'

                logger.info(f"👷 Процесс {i} запущен (PID: {process.pid})")
                time.sleep(2)  # Даем время на запуск

            # 🔥 ЖДЕМ ИНИЦИАЛИЗАЦИИ
            logger.info("⏳ Ожидаем инициализацию процессов...")
            time.sleep(5)

            # 🔥 ПРОВЕРЯЕМ СТАТУСЫ
            ready_workers = 0
            for i in range(self.num_workers):
                status = self.status.get(f'worker_{i}', 'UNKNOWN')
                if status == 'READY':
                    ready_workers += 1
                logger.info(f"  - Процесс {i}: {status}")

            self.stats['active_workers'] = ready_workers

            if ready_workers > 0:
                logger.info(f"✅ Пул запущен: {ready_workers}/{self.num_workers} процессов готовы")
                return True
            else:
                logger.error("❌ Не удалось запустить ни одного процесса")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка запуска пула: {e}")
            return False

    def _kill_stale_chrome_processes(self):
        """Убивает зависшие процессы Chrome"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        logger.info(f"🔄 Убиваем старый Chrome процесс: {proc.info['pid']}")
                        proc.terminate()
                except:
                    pass
            time.sleep(1)
        except ImportError:
            logger.warning("⚠️ psutil не установлен, пропускаем очистку процессов")

    def submit_search_task(self, query, city=None, max_items=20, user_id=None):
        """Добавляет задачу поиска"""
        try:
            task_id = f"search_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

            task = {
                'type': 'SEARCH',
                'task_id': task_id,
                'data': {
                    'query': query,
                    'city': city or 'Москва',
                    'max_items': max_items,
                    'user_id': user_id
                }
            }

            self.task_queue.put(task)
            self.stats['tasks_submitted'] += 1

            logger.info(f"📤 Задача добавлена: '{query}' (ID: {task_id})")
            return task_id

        except Exception as e:
            logger.error(f"❌ Ошибка добавления задачи: {e}")
            self.stats['errors'] += 1
            return None

    def get_results(self, timeout=30):
        """Получает результаты из очереди"""
        results = []
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                try:
                    # Неблокирующее получение из очереди
                    result = self.result_queue.get_nowait()
                    if result:
                        results.append(result)
                        self.stats['tasks_completed'] += 1
                except Empty:
                    # Если очередь пуста 2 секунды - выходим
                    if time.time() - start_time > 2 and not results:
                        break
                    time.sleep(0.5)  # Короткая пауза

        except Exception as e:
            logger.error(f"❌ Ошибка получения результатов: {e}")

        return results

    def get_worker_status(self):
        """Статус всех воркеров"""
        return dict(self.status)

    def health_check(self):
        """Проверка здоровья всех воркеров"""
        task_ids = []
        for i in range(self.num_workers):
            task_id = f"health_check_{i}_{int(time.time())}"
            task = {
                'type': 'HEALTH_CHECK',
                'task_id': task_id,
                'data': {}
            }
            self.task_queue.put(task)
            task_ids.append(task_id)

        # Ждем результаты
        time.sleep(2)
        results = self.get_results(timeout=3)

        healthy_count = sum(1 for r in results if r.get('success', False))
        return {
            'total_workers': self.num_workers,
            'healthy_workers': healthy_count,
            'results': results
        }

    def stop(self):
        """Останавливает все процессы"""
        logger.info("🛑 Остановка пула...")

        try:
            # 🔥 Отправляем команду STOP всем воркерам
            for i in range(self.num_workers):
                self.task_queue.put(None)  # None = команда остановки

            # 🔥 ЖДЕМ ЗАВЕРШЕНИЯ
            timeout = 10
            start_time = time.time()

            for i, process in enumerate(self.workers):
                if process.is_alive():
                    logger.info(f"⏳ Ожидаем завершение процесса {i} (PID: {process.pid})")
                    process.join(timeout=5)

                    if process.is_alive():
                        logger.warning(f"⚠️ Процесс {i} не отвечает, принудительно останавливаем...")
                        process.terminate()
                        process.join(timeout=2)

                        if process.is_alive():
                            logger.error(f"❌ Процесс {i} всё ещё жив, убиваем...")
                            process.kill()

            # 🔥 ОЧИЩАЕМ ОЧЕРЕДИ
            try:
                while True:
                    self.task_queue.get_nowait()
            except Empty:
                pass

            try:
                while True:
                    self.result_queue.get_nowait()
            except Empty:
                pass

            logger.info("✅ Пул остановлен")

        except Exception as e:
            logger.error(f"❌ Ошибка остановки пула: {e}")

    def get_stats(self):
        """Статистика пула"""
        stats = self.stats.copy()
        stats['status'] = dict(self.status)
        return stats


# ============================================
# УПРОЩЕННАЯ ИНТЕГРАЦИЯ
# ============================================

class SimpleParallelParser:
    """Упрощенный параллельный парсер"""

    def __init__(self, num_workers=3):
        self.num_workers = num_workers
        self.pool = None
        self.is_running = False

    def start(self):
        """Запуск парсера"""
        logger.info(f"🚀 Запуск упрощенного парсера с {self.num_workers} процессами")

        try:
            self.pool = DriverPool(num_workers=self.num_workers)

            if self.pool.start():
                self.is_running = True
                logger.info("✅ Парсер запущен")
                return True
            else:
                logger.error("❌ Не удалось запустить парсер")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка запуска парсера: {e}")
            return False

    def search(self, queries, city="Москва", max_items=10):
        """Поиск по нескольким запросам"""
        if not self.is_running or not self.pool:
            logger.error("❌ Парсер не запущен")
            return []

        task_ids = []
        for query in queries[:3]:  # Ограничим 3 запроса
            task_id = self.pool.submit_search_task(
                query=query,
                city=city,
                max_items=max_items
            )
            if task_id:
                task_ids.append(task_id)

        # Ждем результаты
        logger.info(f"⏳ Ожидаем результаты ({len(task_ids)} задач)...")
        time.sleep(10)

        results = self.pool.get_results(timeout=15)

        all_products = []
        for result in results:
            if result.get('success'):
                products = result['data'].get('products', [])
                all_products.extend(products)
                logger.info(f"✅ Найдено {len(products)} товаров")

        return all_products

    def stop(self):
        """Остановка парсера"""
        if self.pool:
            self.pool.stop()
        self.is_running = False
        logger.info("🛑 Парсер остановлен")


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%H:%M:%S'
    )

    print("🧪 Тестирование Driver Pool...")
    print("=" * 50)

    # Создаем и запускаем пул
    pool = DriverPool(num_workers=2)

    if pool.start():
        print("✅ Пул процессов запущен!")
        print(f"📊 Статусы: {pool.get_worker_status()}")

        # Проверяем здоровье
        health = pool.health_check()
        print(f"🏥 Здоровье: {health['healthy_workers']}/{health['total_workers']} процессов здоровы")

        # Тестовый поиск
        print("\n🔍 Тестовый поиск...")
        task_id = pool.submit_search_task("iPhone 13", max_items=5)

        if task_id:
            print(f"📤 Задача отправлена: {task_id}")

            # Ждем
            time.sleep(10)

            # Получаем результаты
            results = pool.get_results(timeout=10)
            print(f"📥 Получено результатов: {len(results)}")

            for result in results:
                if result['success']:
                    products = result['data']['products']
                    worker_id = result['worker_id']
                    print(f"✅ Процесс {worker_id} нашёл {len(products)} товаров")
                    if products:
                        print(f"   Пример: {products[0].get('name', 'No name')[:50]}...")
                else:
                    print(f"❌ Ошибка: {result['data'].get('error', 'Unknown')}")

        # Статистика
        print(f"\n📊 Статистика: {pool.get_stats()}")

        # Останавливаем
        pool.stop()
        print("✅ Тест завершен")
    else:
        print("❌ Не удалось запустить пул")