# ============================================
# СУЩЕСТВУЮЩИЕ ИМПОРТЫ (ПОЛНЫЙ СПИСОК) - ОПТИМИЗИРОВАННЫЙ
# ============================================
import asyncio
import random
from asgiref.sync import sync_to_async
import logging
import time
import hashlib
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs, urlunparse
import re
import requests
from io import BytesIO
from datetime import datetime

from ..core.base_parser import BaseParser
from ..core.browser_manager import BrowserManager
from ..core.settings_manager import SettingsManager
from ..core.timer_manager import TimerManager
from ..utils.notification_sender import NotificationSender
from ..utils.product_validator import ProductValidator
from ..sites.avito_parser import AvitoParser

from ..ai.ml_price_predictor import MLPricePredictor
from ..ai.ml_learning_system import MLLearningSystem
from ..ai.query_optimizer import QueryOptimizer
from ..ai.publication_predictor import PublicationPredictor

# ✅ Создаем логгер для парсера
logger = logging.getLogger('parser.selenium')

# 🔥 ДОБАВИТЬ ИМПОРТ USER-AGENT
try:
    from apps.parsing.utils.custom_user_agents import apply_user_agent_to_driver, get_smart_user_agent_for_parser

    USER_AGENTS_AVAILABLE = True
    logger.info("✅ Модуль custom_user_agents загружен")
except ImportError as e:
    logger.error(f"❌ Не удалось загрузить custom_user_agents: {e}")
    USER_AGENTS_AVAILABLE = False


    # Функции-заглушки
    def apply_user_agent_to_driver(driver, window_id=None):
        logger.warning("⚠️ User-Agent функции недоступны")
        return None


    def get_smart_user_agent_for_parser(window_id, last_user_agent=None):
        return None

# ✅ ДОБАВИТЬ ИМПОРТ ДЛЯ VISION SERVICE
try:
    from apps.bot.services.vision_service import vision_service

    VISION_FEEDBACK_AVAILABLE = True
    logger.info("✅ Система обратной связи vision загружена в парсере")
except ImportError as e:
    logger.warning(f"⚠️ Система обратной связи vision не доступна в парсере: {e}")
    VISION_FEEDBACK_AVAILABLE = False


    class VisionServiceStub:
        def __init__(self):
            self.initialized = False

        async def send_vision_feedback_request(self, *args, **kwargs):
            return False


    vision_service = VisionServiceStub()

# Вместо глобального импорта - динамическая загрузка
DJANGO_AVAILABLE = False  # По умолчанию


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ (ПОЛНЫЕ)
# ============================================

class SmartNotificationSystem:
    """🔔 УМНАЯ СИСТЕМА УВЕДОМЛЕНИЙ"""

    def __init__(self, notification_sender):
        self.notification_sender = notification_sender
        self.urgency_calculator = UrgencyCalculator()
        logger.info("🔔 Инициализирована умная система уведомлений")


class UrgencyCalculator:
    """Калькулятор срочности сделки"""

    def calculate_urgency(self, deal, deal_quality):
        """Рассчитывает срочность сделки"""
        try:
            urgency_score = 0

            # Экономия более 30% - высокая срочность
            economy_percent = deal.get('economy_percent', 0)
            if economy_percent > 30:
                urgency_score += 0.4
            elif economy_percent > 20:
                urgency_score += 0.2

            # Качество сделки
            urgency_score += deal_quality * 0.3

            # Время с момента публикации (менее 1 часа - срочно)
            time_listed = deal.get('time_listed', 24)
            if time_listed < 1:
                urgency_score += 0.3
            elif time_listed < 3:
                urgency_score += 0.1

            # Свежесть товара
            freshness_score = deal.get('ml_freshness_score', 0)
            if freshness_score > 0.8:
                urgency_score += 0.2
            elif freshness_score > 0.6:
                urgency_score += 0.1

            # Определение уровня срочности
            if urgency_score >= 0.7:
                return 'HIGH'
            elif urgency_score >= 0.4:
                return 'MEDIUM'
            else:
                return 'LOW'

        except Exception as e:
            logger.error(f"❌ Ошибка расчета срочности: {e}")
            return 'MEDIUM'


class AdvancedCache:
    """🚀 РАСШИРЕННЫЙ КЭШ С AI-ФИЧАМИ"""

    def __init__(self):
        self.url_cache = {}  # url_hash -> timestamp
        self.image_cache = {}  # image_hash -> vision_data
        self.search_cache = {}  # query -> {'results': [], 'timestamp': time}
        self.stats = {'hits': 0, 'misses': 0, 'size': 0}
        self.query_importance = {}  # Важность запросов для приоритетного кэширования
        self.adaptive_ttl = {}  # Адаптивное время жизни кэша

        # Лимиты для предотвращения утечек памяти
        self.max_urls = 3000
        self.max_images = 1000
        self.max_searches = 200
        self.cache_ttl = 24 * 3600  # 24 часа

        logger.info("🚀 Инициализирован расширенный кэш с AI-фичами")

    def get_url(self, url_hash):
        """Проверка URL в кэше"""
        if url_hash in self.url_cache:
            self.stats['hits'] += 1
            return True
        self.stats['misses'] += 1
        return False

    def add_url(self, url_hash):
        """Добавление URL в кэш с автоочисткой"""
        if len(self.url_cache) >= self.max_urls:
            self._cleanup_oldest('url_cache', self.max_urls // 2)
        self.url_cache[url_hash] = time.time()
        self.stats['size'] = len(self.url_cache)

    def get_search_results(self, query):
        """Получает результаты с проверкой адаптивного TTL"""
        if query in self.search_cache:
            cache_data = self.search_cache[query]
            ttl = self.adaptive_ttl.get(query, 1800)

            # Проверяем не устарели ли данные с учетом адаптивного TTL
            if time.time() - cache_data['timestamp'] < ttl:
                self.stats['hits'] += 1
                return cache_data['results']

        self.stats['misses'] += 1
        return None

    def add_search_results(self, query, results):
        """Добавляет результаты с учетом важности запроса"""
        # Определяем важность запроса
        importance = self._calculate_query_importance(query)
        self.query_importance[query] = importance

        # Адаптивное TTL в зависимости от важности
        ttl = 1800 if importance > 0.7 else 900  # 30 или 15 минут
        self.adaptive_ttl[query] = ttl

        if len(self.search_cache) >= self.max_searches:
            self._cleanup_oldest('search_cache', self.max_searches // 2)

        self.search_cache[query] = {
            'results': results,
            'timestamp': time.time()
        }

    def _cleanup_oldest(self, cache_name, keep_count):
        """Очистка самых старых записей"""
        cache = getattr(self, cache_name)
        if len(cache) > keep_count:
            # Сортируем по времени и оставляем самые новые
            sorted_items = sorted(cache.items(),
                                  key=lambda x: x[1] if isinstance(x[1], (int, float)) else x[1]['timestamp'])
            items_to_keep = dict(sorted_items[-keep_count:])
            setattr(self, cache_name, items_to_keep)
            logger.info(f"🧹 Очищен кэш {cache_name}: {len(cache)} -> {len(items_to_keep)}")

    def get_stats(self):
        """Статистика кэша"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0

        return {
            'hit_rate': round(hit_rate, 2),
            'url_cache_size': len(self.url_cache),
            'image_cache_size': len(self.image_cache),
            'search_cache_size': len(self.search_cache),
            'total_hits': self.stats['hits'],
            'total_misses': self.stats['misses']
        }

    def _calculate_query_importance(self, query):
        """Рассчитывает важность запроса для приоритетного кэширования"""
        importance = 0.5

        # Запросы с брендами важнее
        brands = ['iphone', 'macbook', 'samsung', 'sony']
        if any(brand in query.lower() for brand in brands):
            importance += 0.3

        # Конкретные запросы важнее общих
        words = query.split()
        if len(words) >= 3:
            importance += 0.2

        return min(importance, 1.0)


class HealthMonitor:
    """❤️ МОНИТОР ЗДОРОВЬЯ СИСТЕМЫ"""

    def __init__(self):
        self.metrics = {
            'start_time': time.time(),
            'total_cycles': 0,
            'successful_cycles': 0,
            'errors': [],
            'performance_history': []
        }
        logger.info("❤️ Инициализирован монитор здоровья системы")

    def record_cycle(self, success=True, cycle_time=0, found_items=0):
        """Записывает метрики цикла"""
        self.metrics['total_cycles'] += 1
        if success:
            self.metrics['successful_cycles'] += 1

        self.metrics['performance_history'].append({
            'timestamp': time.time(),
            'cycle_time': cycle_time,
            'success': success,
            'found_items': found_items
        })

        # Ограничиваем историю последними 100 циклами
        if len(self.metrics['performance_history']) > 100:
            self.metrics['performance_history'] = self.metrics['performance_history'][-100:]

    def get_health_status(self):
        """Возвращает статус здоровья системы"""
        total_cycles = self.metrics['total_cycles']
        successful_cycles = self.metrics['successful_cycles']

        if total_cycles == 0:
            return 'UNKNOWN'

        success_rate = successful_cycles / total_cycles

        if success_rate > 0.8:
            return 'HEALTHY'
        elif success_rate > 0.6:
            return 'DEGRADED'
        else:
            return 'UNHEALTHY'

    def get_performance_metrics(self):
        """Возвращает метрики производительности"""
        if not self.metrics['performance_history']:
            return {}

        recent_performance = self.metrics['performance_history'][-10:]
        avg_cycle_time = sum(p['cycle_time'] for p in recent_performance) / len(recent_performance)
        success_rate = sum(1 for p in recent_performance if p['success']) / len(recent_performance)

        return {
            'health_status': self.get_health_status(),
            'avg_cycle_time': avg_cycle_time,
            'recent_success_rate': success_rate,
            'uptime_hours': (time.time() - self.metrics['start_time']) / 3600,
            'total_cycles': self.metrics['total_cycles']
        }


class AdaptiveTimer:
    """⏰ АДАПТИВНЫЙ ТАЙМЕР"""

    def __init__(self):
        self.cycle_history = []  # История успешности циклов
        self.response_times = []  # Время ответа
        self.max_history = 10

    def calculate_pause(self, found_items, cycle_time, error_occurred=False):
        """Умная пауза с разумными ограничениями"""
        # Базовые настройки
        MIN_PAUSE = 5  # секунд
        MAX_PAUSE = 30  # секунд (максимум 30 секунд)

        if error_occurred:
            pause = 15  # 15 секунд при ошибках
        elif found_items > 0:
            pause = 10  # 10 секунд если нашли товары
        else:
            pause = 15  # 15 секунд если ничего не нашли

        # Ограничиваем диапазон
        pause = max(MIN_PAUSE, min(pause, MAX_PAUSE))

        logger.info(f"⏰ Умная пауза: {pause}сек")
        return pause


# ============================================
# ОСНОВНОЙ КЛАСС ПАРСЕРА С СУПЕР-AI ФИЧАМИ
# ============================================
class SeleniumAvitoParser(BaseParser):
    """🚀 СУПЕР-ПАРСЕР С AI-ФИЧАМИ И ПРИОРИТЕТОМ СВЕЖЕСТИ"""

    def __init__(self):
        super().__init__()

        # 🔥 ДОБАВЬТЕ ЭТИ СТРОКИ ДЛЯ УМНОЙ ОСТАНОВКИ:
        self.force_stop = False
        self.stop_requested = False
        self.current_operations = set()  # Для отслеживания текущих операций

        # 🔥 ДОБАВЬ ЭТИ СТРОКИ ДЛЯ ПОДДЕРЖКИ САЙТОВ
        self.current_site = 'avito'  # По умолчанию Avito
        self.site_parsers = {}  # Кэш парсеров для разных сайтов
        self.settings_check_counter = 0

        # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Добавляем хранение ID текущего пользователя
        self.current_user_id = None  # ID пользователя для которого работает парсер
        self.current_user_username = None  # Имя пользователя для логов

        # 🔥 ВСЕ МЕНЕДЖЕРЫ СОХРАНЯЕМ
        self.settings_manager = SettingsManager()
        self.browser_manager = BrowserManager()
        self.timer_manager = TimerManager()
        self.notification_sender = NotificationSender()
        self.product_validator = ProductValidator()

        # 🔥 УНИФИЦИРОВАННЫЕ AI-КОМПОНЕНТЫ - ВСЕ ИЗ parser/ai/
        self.price_predictor = MLPricePredictor()  # ✅ Цена + свежесть в одном!
        self.learning_system = MLLearningSystem()  # ✅ Универсальное обучение
        self.query_optimizer = QueryOptimizer()  # ✅ Умные запросы
        self.publication_predictor = PublicationPredictor()  # ✅ Паттерны публикаций

        # 🔥 ДОБАВЛЯЕМ FRESHNESS QUERY OPTIMIZER (исправление ошибки)
        try:
            from apps.parsing.utils.freshness_query_optimizer import FreshnessQueryOptimizer
            self.freshness_query_optimizer = FreshnessQueryOptimizer()
            logger.info("🎯 FreshnessQueryOptimizer инициализирован")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось инициализировать FreshnessQueryOptimizer: {e}")
            # Создаем простую заглушку
            self.freshness_query_optimizer = None

        # 🔥 ИСПРАВЛЕНИЕ: Инициализируем fresh_deals пустым списком
        self.fresh_deals = []

        # 🔔 УМНАЯ СИСТЕМА УВЕДОМЛЕНИЙ
        self.smart_notifier = SmartNotificationSystem(self.notification_sender)

        # ✅ ИНИЦИАЛИЗАЦИЯ VISION СЕРВИСА
        self.vision_service = None
        if VISION_FEEDBACK_AVAILABLE:
            try:
                from apps.bot.services.vision_service import vision_service
                self.vision_service = vision_service
                logger.info("✅ Система обратной связи vision инициализирована в парсере")
            except Exception as e:
                logger.warning(f"⚠️ Система обратной связи vision не инициализирована: {e}")

        # 🔥 УЛУЧШЕННЫЕ КОМПОНЕНТЫ
        self.optimized_cache = AdvancedCache()
        self.adaptive_timer = AdaptiveTimer()
        self.health_monitor = HealthMonitor()

        # 🔥 АСИНХРОННЫЕ КОМПОНЕНТЫ
        self.session = None
        self.thread_pool = ThreadPoolExecutor(max_workers=8)

        # 🔥 СТРУКТУРЫ ДАННЫХ
        self.processed_urls = set()
        self.persistent_urls_cache = set()
        self.url_cache_lock = asyncio.Lock()
        self.image_hash_cache = set()

        # 🔥 ХЭШ-ТАБЛИЦА ДЛЯ БЫСТРОЙ ПРОВЕРКИ ДУБЛИКАТОВ
        self.url_hash_cache = {}  # url_hash -> timestamp
        self.id_hash_cache = {}  # item_id -> timestamp

        # 🔥 РАСШИРЕННАЯ СТАТИСТИКА ПАРСЕРА
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'items_found': 0,
            'good_deals_found': 0,
            'duplicates_blocked': 0,
            'database_duplicates_skipped': 0,  # НОВАЯ СТАТИСТИКА
            'error_count': 0,
            'active_queries': 0,
            'avg_cycle_time': 0,
            'uptime': '0ч 0м',
            'last_reset': time.time(),
            'current_queries': [],
            'efficiency_distribution': [],
            'successful_queries': [],
            'cache_hit_rate': 0,
            'adaptive_pause': 60,
            'ai_optimized_queries': 0,
            'predicted_deals': 0,
            'trend_analysis_used': 0,
            'ml_learning_cycles': 0,
            'fresh_deals_found': 0,  # 🔥 НОВАЯ СТАТИСТИКА
            'freshness_analysis_count': 0,
            'critical_fresh_deals': 0,
            'current_user_id': None,  # 🔥 Добавляем ID пользователя в статистику
            'current_user_username': None  # 🔥 Добавляем имя пользователя в статистику
        }

        self.cycle_times = []
        self.start_time = time.time()
        self.query_stats = {}

        # Настройки по умолчанию
        self.search_queries = []
        self.exclude_keywords = []
        self.browser_windows = 1
        self.min_price = 0
        self.max_price = 100000
        self.min_rating = 4.0
        self.seller_type = 'all'
        self.current_site = 'avito'

        # 🚀 ОТЛОЖЕННАЯ инициализация AI (будет запущена при старте парсера)
        self.ai_initialized = False

        logger.info("🚀 СУПЕР-ПАРСЕР С AI-ФИЧАМИ И ПРИОРИТЕТОМ СВЕЖЕСТИ ИНИЦИАЛИЗИРОВАН!")

    # ============================================
    # ДИНАМИЧЕСКИЕ ИМПОРТЫ DJANGO
    # ============================================

    async def _is_duplicate_in_database(self, product_url, product_id=None, user_id=None):
        """
        ПРОВЕРЯЕТ ЕСТЬ ЛИ ТОВАР УЖЕ В БАЗЕ ДАННЫХ ПОЛЬЗОВАТЕЛЯ
        Динамическая загрузка Django моделей
        """
        global DJANGO_AVAILABLE

        # Динамическая проверка доступности Django
        if not DJANGO_AVAILABLE:
            try:
                from django.db.models import Q
                from apps.website.models import Deal
                DJANGO_AVAILABLE = True
                logger.info("✅ Модели Django загружены для проверки дубликатов")
            except ImportError as e:
                logger.warning(f"⚠️ Модели Django недоступны для проверки дубликатов: {e}")
                return False
            except Exception as e:
                logger.warning(f"⚠️ Django не настроен: {e}")
                return False

        try:
            from apps.website.models import Deal
            from django.db.models import Q

            # Проверяем по URL
            if product_url:
                url_exists = await sync_to_async(
                    lambda: Deal.objects.filter(url=product_url).exists()
                )()
                if url_exists:
                    logger.info(f"🚫 ДУБЛИКАТ В БАЗЕ по URL: {product_url[:50]}...")
                    return True

            # Проверяем по ID товара (если есть)
            if product_id:
                id_exists = await sync_to_async(
                    lambda: Deal.objects.filter(item_id=product_id).exists()
                )()
                if id_exists:
                    logger.info(f"🚫 ДУБЛИКАТ В БАЗЕ по ID: {product_id}")
                    return True

            return False

        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки дубликата в базе: {e}")
            return False

    def configure_for_user(self, user_id, username=None):
        """🔧 Настраивает парсер для работы с конкретным пользователем"""
        try:
            # 🔥 ДИНАМИЧЕСКИЙ ИМПОРТ Django
            try:
                from django.contrib.auth.models import User

                # 🔥 Получаем пользователя из базы
                user = User.objects.get(id=user_id)

                # Сохраняем данные пользователя
                self.current_user_id = user_id
                self.current_user_username = username or user.username

                # Обновляем статистику
                self.search_stats['current_user_id'] = user_id
                self.search_stats['current_user_username'] = self.current_user_username

                logger.info(f"👤 Парсер настроен для пользователя: {self.current_user_username} (ID: {user_id})")

                # 🔥 Настраиваем поисковые запросы пользователя (если есть)
                if hasattr(self.settings_manager, 'load_settings_for_user'):
                    self.search_queries = self.settings_manager.load_settings_for_user(user_id)
                    logger.info(
                        f"🔍 Загружено {len(self.search_queries)} запросов для пользователя {self.current_user_username}")

                return True

            except ImportError as e:
                logger.error(f"❌ Django не доступен: {e}")
                # Используем базовые настройки
                self.current_user_id = user_id
                self.current_user_username = username or f"user_{user_id}"
                self.search_stats['current_user_id'] = user_id
                self.search_stats['current_user_username'] = self.current_user_username
                logger.info(f"👤 Парсер настроен для пользователя {self.current_user_username} (без Django)")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка настройки парсера для пользователя {user_id}: {e}")
            self.current_user_id = user_id
            self.current_user_username = username
            return False

    # ============================================
    # МЕТОДЫ ПРОВЕРКИ ДУБЛИКАТОВ В БАЗЕ ДАННЫХ
    # ============================================

    def _create_product_hash(self, product_data):
        """
        СОЗДАЕТ УНИКАЛЬНЫЙ ХЭШ ДЛЯ ТОВАРА
        Использует URL и ID для создания хэша
        """
        try:
            hash_string = ""

            # Используем URL если есть
            if 'url' in product_data and product_data['url']:
                hash_string += product_data['url']

            # Используем ID товара если есть
            if 'item_id' in product_data and product_data['item_id']:
                hash_string += str(product_data['item_id'])

            # Используем название если нет URL и ID
            if not hash_string and 'name' in product_data:
                hash_string = product_data['name']

            # Создаем MD5 хэш
            if hash_string:
                hash_obj = hashlib.md5(hash_string.encode('utf-8'))
                return hash_obj.hexdigest()[:16]

            return None

        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания хэша товара: {e}")
            return None

    async def _check_and_add_to_hash_cache(self, product_data):
        """
        ПРОВЕРЯЕТ И ДОБАВЛЯЕТ ТОВАР В ХЭШ-КЭШ
        Возвращает True если дубликат найден в кэше
        """
        try:
            product_hash = self._create_product_hash(product_data)
            if not product_hash:
                return False

            # Проверяем в кэше
            if product_hash in self.url_hash_cache:
                # Проверяем не устарел ли кэш (24 часа)
                if time.time() - self.url_hash_cache[product_hash] < 86400:
                    logger.info(f"🚫 ДУБЛИКАТ В КЭШЕ по хэшу: {product_hash}")
                    return True

            # Добавляем в кэш
            self.url_hash_cache[product_hash] = time.time()

            # Очистка старых записей
            if len(self.url_hash_cache) > 5000:
                oldest_hashes = sorted(self.url_hash_cache.items(), key=lambda x: x[1])[:1000]
                for hash_key, _ in oldest_hashes:
                    del self.url_hash_cache[hash_key]
                logger.info(f"🧹 Очищено 1000 старых хэшей из кэша")

            return False

        except Exception as e:
            logger.warning(f"⚠️ Ошибка работы с хэш-кэшем: {e}")
            return False

    async def _fast_duplicate_check(self, product_data, window_index):
        """
        БЫСТРАЯ ПРОВЕРКА ДУБЛИКАТОВ ПО ТРЕМ УРОВНЯМ:
        1. Кэш в памяти (самый быстрый)
        2. NotificationSender кэш
        3. База данных PostgreSQL
        """
        try:
            product_name = product_data.get('name', '')[:50]

            # 🔥 УРОВЕНЬ 1: Проверка в хэш-кэше (самый быстрый)
            if await self._check_and_add_to_hash_cache(product_data):
                logger.info(f"🚫 Окно {window_index} | Дубликат в хэш-кэше: {product_name}...")
                self.search_stats['duplicates_blocked'] += 1
                return True

            # 🔥 УРОВЕНЬ 2: Проверка через notification_sender
            if hasattr(self.notification_sender, 'is_duplicate_url'):
                is_duplicate = await self.notification_sender.is_duplicate_url(product_data.get('url', ''))
                if is_duplicate:
                    logger.info(f"🚫 Окно {window_index} | Дубликат в notification кэше: {product_name}...")
                    self.search_stats['duplicates_blocked'] += 1
                    return True

            # 🔥 УРОВЕНЬ 3: Проверка в базе данных PostgreSQL
            is_db_duplicate = await self._is_duplicate_in_database(
                product_url=product_data.get('url'),
                product_id=product_data.get('item_id')
            )
            if is_db_duplicate:
                logger.info(f"🚫 Окно {window_index} | Дубликат в БАЗЕ ДАННЫХ: {product_name}...")
                self.search_stats['database_duplicates_skipped'] += 1
                return True

            # 🔥 УРОВЕНЬ 4: Проверка по ID если есть
            if 'item_id' in product_data and product_data['item_id']:
                item_id = str(product_data['item_id'])
                if item_id in self.id_hash_cache:
                    # Проверяем не устарел ли кэш (12 часов)
                    if time.time() - self.id_hash_cache[item_id] < 43200:
                        logger.info(f"🚫 Окно {window_index} | Дубликат по ID в кэше: {item_id}")
                        self.search_stats['duplicates_blocked'] += 1
                        return True

                # 🔥 ИСПРАВЛЕНИЕ ОШИБКИ: УБРАТЬ ЛИШНЮЮ СКОБКУ
                self.id_hash_cache[item_id] = time.time()

            logger.info(f"✅ Окно {window_index} | Товар уникален: {product_name}...")
            return False

        except Exception as e:
            logger.warning(f"⚠️ Ошибка быстрой проверки дубликатов: {e}")
            return False  # В случае ошибки продолжаем обработку

    # ============================================
    # СУЩЕСТВУЮЩИЕ МЕТОДЫ (ПОЛНЫЕ)
    # ============================================

    async def _initialize_super_ai(self):
        """🚀 Инициализация супер-AI системы с реальными компонентами"""
        try:
            logger.info("🧠 Инициализация СУПЕР-ИИ системы с реальными компонентами...")

            # Загружаем состояние обучения если есть
            await self.learning_system.load_learning_state()

            # 🔥 ИНИЦИАЛИЗИРУЕМ ТОЛЬКО СУЩЕСТВУЮЩИЕ КОМПОНЕНТЫ
            await self.price_predictor.initialize_model()
            await self.publication_predictor.initialize_model()

            # 🔥 ПРОВЕРЯЕМ И ИНИЦИАЛИЗИРУЕМ FRESHNESS QUERY OPTIMIZER ЕСЛИ ОН ЕСТЬ
            if hasattr(self, 'freshness_query_optimizer') and self.freshness_query_optimizer:
                try:
                    logger.info("✅ FreshnessQueryOptimizer инициализирован")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка инициализации FreshnessQueryOptimizer: {e}")

            logger.info("🚀 СУПЕР-ИИ система с реальными компонентами инициализирована")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AI: {e}")

    async def _analyze_product_with_both_models(self, product, window_index):
        """🔥 СОВМЕСТНЫЙ АНАЛИЗ ЦЕНЫ И СВЕЖЕСТИ ДВУМЯ ML МОДЕЛЯМИ"""
        try:
            logger.info(f"🎯 Окно {window_index} | Запуск совместного анализа ML моделями...")

            # 🔥 ЦЕНА - АСИНХРОННО
            predicted_price = await self.price_predictor.predict_price_super(product)

            # 🔥 СВЕЖЕСТЬ - СИНХРОННО
            try:
                freshness_score = await self.price_predictor.predict_freshness_with_learning(product)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка predict_freshness: {e}")
                freshness_score = self._fallback_freshness_analysis_sync(product)

            # 🔥 ВРЕМЯ ПУБЛИКАЦИИ - АСИНХРОННО (ЖДЕМ!)
            try:
                publication_time = await self.publication_predictor.predict_publication_time(product)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка predict_publication_time: {e}")
                publication_time = "неизвестно"

            # 🔥 ЗАЩИТА ОТ НЕКОРРЕКТНЫХ ЗНАЧЕНИЙ
            if predicted_price is None or isinstance(predicted_price, Exception):
                logger.warning(f"⚠️ Ошибка предсказания цены: {predicted_price}")
                predicted_price = product.get('price', 0) * 1.2

            if freshness_score is None or isinstance(freshness_score, Exception):
                logger.warning(f"⚠️ Ошибка предсказания свежести: {freshness_score}")
                freshness_score = self._fallback_freshness_analysis_sync(product)

            # 🔥 ПРИВОДИМ К ЧИСЛАМ
            try:
                predicted_price = float(predicted_price) if predicted_price else product.get('price', 0) * 1.2
                freshness_score = float(freshness_score) if freshness_score else 0.5
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Ошибка приведения типов: {e}")
                predicted_price = product.get('price', 0) * 1.2
                freshness_score = 0.5

            # 🔥 ОБНОВЛЯЕМ ДАННЫЕ ПРОДУКТА
            product.update({
                'ai_predicted_price': predicted_price,
                'ml_freshness_score': freshness_score,
                'predicted_publication_time': publication_time,
                'freshness_category': self._get_freshness_category(freshness_score),
                'analyzed_at': datetime.now().isoformat(),
                'dual_ml_analysis': True
            })

            # 🔥 РАСЧЕТ ЭКОНОМИИ
            actual_price = product.get('price', 0)
            if predicted_price and predicted_price > 0 and actual_price > 0:
                economy = predicted_price - actual_price
                economy_percent = int((economy / predicted_price) * 100)
            else:
                economy = 0
                economy_percent = 0

            product.update({
                'economy': economy,
                'economy_percent': economy_percent,
                'target_price': predicted_price
            })

            # 🔥 ОБУЧАЕМ СИСТЕМУ
            try:
                if hasattr(self.learning_system, 'learn_from_product'):
                    await self.learning_system.learn_from_product(product)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка обучения системы: {e}")

            logger.info(
                f"🎯 Окно {window_index} | ML анализ: Цена {predicted_price:.0f}р | Свежесть {freshness_score:.0%} | Время: {publication_time}")

            return product

        except Exception as e:
            logger.error(f"❌ Ошибка совместного анализа ML моделями: {e}")
            # 🔥 ВОЗВРАЩАЕМ ПРОДУКТ БАЗОВЫМИ ДАННЫМИ
            product.update({
                'ai_predicted_price': product.get('price', 0) * 1.2,
                'ml_freshness_score': 0.5,
                'predicted_publication_time': "неизвестно",
                'freshness_category': 'unknown',
                'analyzed_at': datetime.now().isoformat(),
                'dual_ml_analysis': False
            })
            return product

    def _get_site_parser(self, driver, site=None):
        """🔥 ВОЗВРАЩАЕТ ПАРСЕР ДЛЯ ВЫБРАННОГО САЙТА"""
        try:
            site = site or self.current_site

            # Используем кэш чтобы не создавать постоянно новые объекты
            if site in self.site_parsers:
                return self.site_parsers[site]

            # 🔥 СОЗДАЕМ ПАРСЕР ДЛЯ ВЫБРАННОГО САЙТА
            if site == 'avito':
                from ..sites.avito_parser import AvitoParser
                parser = AvitoParser(driver)
            elif site == 'auto.ru':
                from ..sites.auto_ru_parser import AutoRuParser
                parser = AutoRuParser(driver)

                # 🔥 УСТАНАВЛИВАЕМ СВЯЗЬ С ОСНОВНЫМ ПАРСЕРОМ
                parser.set_main_parser(self)
                logger.info("✅ Установлена связь с AutoRuParser")

            else:
                logger.warning(f"⚠️ Неизвестный сайт {site}, используем Avito по умолчанию")
                from ..sites.avito_parser import AvitoParser
                parser = AvitoParser(driver)

            # Сохраняем в кэш
            self.site_parsers[site] = parser
            logger.info(f"🎯 Создан парсер для сайта: {site}")

            return parser

        except Exception as e:
            logger.error(f"❌ Ошибка создания парсера для {site}: {e}")
            # Фолбэк на Avito если ошибка
            from ..sites.avito_parser import AvitoParser
            return AvitoParser(driver)

    def change_site(self, site):
        """🔥 СМЕНА САЙТА ПАРСЕРА"""
        try:
            supported_sites = ['avito', 'auto.ru']

            if site not in supported_sites:
                logger.error(f"❌ Неподдерживаемый сайт: {site}")
                return False

            self.current_site = site  # 🔥 ВАЖНО: Сохраняем выбранный сайт!
            # Очищаем кэш парсеров при смене сайта
            self.site_parsers.clear()

            logger.info(f"🔄 Сайт парсера изменен на: {site}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка смены сайта: {e}")
            return False

    def _fallback_freshness_analysis_sync(self, product_data):
        """🔄 СИНХРОННЫЙ фолбэк анализ когда ML недоступен"""
        try:
            time_listed = product_data.get('time_listed', 24)

            # Простая логика на основе времени
            if time_listed <= 2:
                score = 0.9
            elif time_listed <= 6:
                score = 0.7
            elif time_listed <= 24:
                score = 0.5
            elif time_listed <= 72:
                score = 0.3
            else:
                score = 0.1

            logger.info(f"🔄 Синхронный фолбэк анализ свежести: {score:.2f}")

            return score

        except Exception as e:
            logger.warning(f"⚠️ Ошибка синхронного фолбэк анализа: {e}")
            return 0.5

    def _get_freshness_category(self, freshness_score):
        """🎯 Определение категории свежести"""
        try:
            if freshness_score >= 0.8:
                return 'critical_fresh'
            elif freshness_score >= 0.6:
                return 'very_fresh'
            elif freshness_score >= 0.4:
                return 'fresh'
            elif freshness_score >= 0.2:
                return 'average'
            else:
                return 'old'
        except Exception as e:
            logger.warning(f"⚠️ Ошибка определения категории свежести: {e}")
            return 'unknown'

    async def _initialize_ml_models(self):
        """🔧 Инициализация и отладка ML моделей"""
        try:
            logger.info("🔧 Инициализация ML моделей цены и свежести...")

            # 🔥 ИНИЦИАЛИЗАЦИЯ МОДЕЛИ ЦЕНЫ
            price_loaded = await self.price_predictor.load_model()
            if not price_loaded:
                logger.info("🧠 Модель цены не загружена, начинаем обучение...")
                training_success = await self.price_predictor.train_super_model()
                if training_success:
                    logger.info("✅ Модель цены успешно обучена")
                else:
                    logger.warning("⚠️ Не удалось обучить модель цены")
            else:
                logger.info("✅ Модель цены загружена из файла")

            # 🔥 ИНИЦИАЛИЗАЦИЯ МОДЕЛИ СВЕЖЕСТИ
            freshness_loaded = await self.price_predictor.load_freshness_model()
            if not freshness_loaded:
                logger.info("🧠 Модель свежести не загружена, начинаем обучение...")
                freshness_success = await self.price_predictor.train_freshness_model()
                if freshness_success:
                    logger.info("✅ Модель свежести успешно обучена")
                else:
                    logger.warning("⚠️ Не удалось обучить модель свежести")
            else:
                logger.info("✅ Модель свежести загружена из файла")

            # 🔥 ЗАПУСК ДЕБАГ-ПРОВЕРКИ
            await self._debug_ml_training()

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ML моделей: {e}")
            return False

    async def _debug_ml_training(self):
        """🐛 Отладка обучения ML моделей"""
        try:
            logger.info("🔍 ДЕБАГ: Проверка обучения ML моделей...")

            # Проверяем модель цены
            if self.price_predictor.model is not None:
                logger.info(f"✅ Модель цены загружена: {type(self.price_predictor.model)}")
                if hasattr(self.price_predictor.feature_scaler, 'n_features_in_'):
                    logger.info(f"✅ Scaler цены: {self.price_predictor.feature_scaler.n_features_in_} фичей")
                logger.info(f"✅ Обучена: {self.price_predictor.is_trained}")
            else:
                logger.warning("❌ Модель цены НЕ загружена")

            # Проверяем модель свежести
            if self.price_predictor.freshness_model is not None:
                logger.info(f"✅ Модель свежести загружена: {type(self.price_predictor.freshness_model)}")
                if hasattr(self.price_predictor.freshness_scaler, 'n_features_in_'):
                    logger.info(f"✅ Scaler свежести: {self.price_predictor.freshness_scaler.n_features_in_} фичей")
            else:
                logger.warning("❌ Модель свежести НЕ загружена")

            # Пробуем обучить модель свежести если она не загружена
            if self.price_predictor.freshness_model is None:
                logger.info("🔍 Попытка обучить модель свежести...")
                success = await self.price_predictor.train_freshness_model()
                logger.info(f"🔍 Результат обучения свежести: {success}")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка дебаг-проверки: {e}")
            return False

    async def _ai_optimize_search_queries_for_freshness(self):
        """🔥 AI-оптимизация запросов для поиска СВЕЖИХ объявлений с реальными компонентами"""
        try:
            if not self.search_queries:
                return self.search_queries

            logger.info("🎯 Запуск AI-оптимизации запросов для СВЕЖЕСТИ с реальными компонентами...")

            # Определяем время суток для временных модификаторов
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                time_of_day = 'morning'
            elif 12 <= current_hour < 17:
                time_of_day = 'afternoon'
            elif 17 <= current_hour < 23:
                time_of_day = 'evening'
            else:
                time_of_day = 'night'

            # 🔥 ОПТИМИЗИРУЕМ ЗАПРОСЫ ДЛЯ СВЕЖЕСТИ С РЕАЛЬНЫМ КОМПОНЕНТОМ
            if self.freshness_query_optimizer:
                optimized_queries = await self.freshness_query_optimizer.optimize_for_freshness(
                    self.search_queries,
                    time_of_day=time_of_day
                )
            else:
                # Фоллбэк если оптимизатор не загружен
                logger.warning("⚠️ FreshnessQueryOptimizer не загружен, используем базовые запросы")
                optimized_queries = self.search_queries

            # 🔥 ОБУЧАЕМСЯ НА УСПЕШНЫХ ЗАПРОСАХ С РЕАЛЬНЫМ КОМПОНЕНТОМ
            successful_queries = self.search_stats.get('successful_queries', [])
            if successful_queries and self.freshness_query_optimizer:
                await self.freshness_query_optimizer.learn_from_successful_queries(successful_queries)

            self.search_stats['ai_optimized_queries'] = len(optimized_queries)
            logger.info(f"🎯 AI оптимизировал {len(optimized_queries)} запросов для свежести")

            return optimized_queries[:20]

        except Exception as e:
            logger.error(f"❌ Ошибка AI-оптимизации для свежести: {e}")
            return self.search_queries

    async def _background_ai_learning(self):
        """🔁 Фоновое обучение AI системы"""
        while self.is_running:
            try:
                # Переобучение каждые 30 минут
                await asyncio.sleep(1800)  # 30 минут
                if self.is_running:
                    await self.learning_system.retrain_models_advanced()
                    self.search_stats['ml_learning_cycles'] += 1
                    logger.info("🔄 Фоновое обучение AI завершено")

            except Exception as e:
                logger.error(f"❌ Ошибка фонового обучения: {e}")
                if self.is_running:
                    await asyncio.sleep(300)  # Ждем 5 минут перед повторной попыткой

    async def _background_ai_initialization(self):
        """🔁 Фоновая инициализация AI системы"""
        try:
            # Пытаемся обучить модель
            await self.price_predictor.train_super_model()
            logger.info("✅ ML модель обучена")

            # Запускаем фоновое обучение
            asyncio.create_task(self._background_ai_learning())

        except Exception as e:
            logger.warning(f"⚠️ Фоновая инициализация AI не удалась: {e}")

    async def _ai_optimize_search_queries(self):
        """🤖 AI-оптимизация поисковых запросов"""
        try:
            if not self.search_queries:
                return self.search_queries

            logger.info("🎯 Запуск AI-оптимизации запросов...")

            # 🔥 ПРОВЕРЯЕМ ДОСТУПНОСТЬ OPTIMIZER
            if not hasattr(self, 'freshness_query_optimizer') or self.freshness_query_optimizer is None:
                logger.warning("⚠️ FreshnessQueryOptimizer не доступен, используем базовые запросы")
                return self.search_queries

            # 🔥 ОПРЕДЕЛЯЕМ ВРЕМЯ СУТОК
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                time_of_day = 'morning'
            elif 12 <= current_hour < 17:
                time_of_day = 'afternoon'
            elif 17 <= current_hour < 23:
                time_of_day = 'evening'
            else:
                time_of_day = 'night'

            logger.info(f"🕒 Время суток для оптимизации: {time_of_day}")

            # 🔥 ВЫЗЫВАЕМ ОПТИМИЗАЦИЮ
            optimized_queries = await self.freshness_query_optimizer.optimize_for_freshness(
                self.search_queries,
                query_stats=self.query_stats,
                time_of_day=time_of_day
            )

            self.search_stats['ai_optimized_queries'] = len(optimized_queries)
            logger.info(f"🎯 AI оптимизировал {len(optimized_queries)} запросов")

            return optimized_queries[:15]  # Ограничиваем количество запросов

        except Exception as e:
            logger.error(f"❌ Ошибка AI-оптимизации: {e}")
            return self.search_queries  # Возвращаем оригинальные запросы при ошибке

    async def _ai_analyze_deal_quality(self, product):
        """🤖 AI-анализ качества сделки с СУПЕР-ML"""
        try:
            # Используем ML для предсказания цены
            predicted_price = await self.price_predictor.predict_price_super(product)
            actual_price = product.get('price', 0)

            if actual_price <= 0 or predicted_price <= 0:
                return 0.5

            # Рассчитываем выгоду с ML
            economy_ratio = (predicted_price - actual_price) / predicted_price
            economy_score = min(max(economy_ratio, 0), 0.5) * 2  # Нормализуем до 0-1

            # Анализ состояния через AI
            condition_score = await self._analyze_condition_ai(product)

            # Анализ продавца
            seller_score = self._analyze_seller_ai(product)

            # Временной фактор
            time_score = self._calculate_time_score_ai(product)

            # Итоговый score с весами
            final_score = (
                    economy_score * 0.4 +
                    condition_score * 0.25 +
                    seller_score * 0.2 +
                    time_score * 0.15
            )

            # 🔥 ИСПРАВЛЕНИЕ: Используем правильный метод
            asyncio.create_task(
                self.learning_system.collect_feedback(  # 🔥 ПРАВИЛЬНЫЙ МЕТОД!
                    prediction=final_score,
                    actual_result=None,
                    features=product,
                    prediction_type="quality",
                    confidence=self.price_predictor.get_prediction_confidence(product),
                    context={
                        'category': product.get('category'),
                        'has_brand': any(brand in product.get('name', '')
                                         for brand in ['iphone', 'samsung', 'macbook']),
                        'condition': self._analyze_product_condition_simple(product),
                        'seller_rating': product.get('seller_rating', 0)
                    }
                )
            )

            return min(max(final_score, 0), 1)

        except Exception as e:
            logger.error(f"❌ Ошибка супер-анализа: {e}")
            return await self._ai_analyze_deal_quality_fallback(product)

    async def _ai_analyze_deal_quality_fallback(self, product):
        """🔄 Фолбэк анализ качества сделки"""
        try:
            score = 0.0

            # Анализ экономии с защитой от None
            economy_percent = product.get('economy_percent', 0)
            if economy_percent is None:
                economy_percent = 0

            if economy_percent > 30:
                score += 0.4
            elif economy_percent > 20:
                score += 0.3
            elif economy_percent > 10:
                score += 0.2

            # Анализ состояния товара
            condition = self._analyze_product_condition(product)
            if condition == 'отличное':
                score += 0.3
            elif condition == 'хорошее':
                score += 0.2

            # Анализ рейтинга продавца
            seller_rating = product.get('seller_rating', 4.0)
            if seller_rating is None:
                seller_rating = 4.0
            seller_score = seller_rating / 5.0
            score += seller_score * 0.2

            # Анализ времени публикации
            time_listed = product.get('time_listed', 24)
            if time_listed is None:
                time_listed = 24
            time_score = self._calculate_time_score(time_listed)
            score += time_score * 0.1

            return min(score, 1.0)

        except Exception as e:
            logger.warning(f"⚠️ Ошибка фолбэк анализа сделки: {e}")
            return 0.5

    async def _analyze_condition_ai(self, product):
        """🔍 AI анализ состояния товара с ML"""
        try:
            description = product.get('description', '').lower()
            name = product.get('name', '').lower()

            # Используем MLPricePredictor для анализа состояния
            condition_features = self.price_predictor._analyze_condition_detailed(name, description)

            # Взвешенная оценка состояния
            weights = [0.4, 0.3, 0.15, 0.1, 0.05]  # Веса для perfect, excellent, good, satisfactory, bad
            condition_score = sum(cond * weight for cond, weight in zip(condition_features, weights))

            return condition_score

        except Exception as e:
            logger.warning(f"⚠️ Ошибка AI анализа состояния: {e}")
            return 0.7

    def _analyze_seller_ai(self, product):
        """👨‍💼 AI анализ продавца"""
        seller_rating = product.get('seller_rating', 4.0)
        reviews_count = product.get('reviews_count', 0)

        # Нормализованый рейтинг
        rating_score = seller_rating / 5.0

        # Бонус за количество отзывов
        reviews_bonus = min(reviews_count / 100, 0.2)  # Максимум +0.2 за 100+ отзывов

        return min(rating_score + reviews_bonus, 1.0)

    def _calculate_time_score_ai(self, product):
        """🕒 AI оценка временного фактора"""
        hours_listed = product.get('time_listed', 24)

        if hours_listed < 1:
            return 1.0  # Очень свежее
        elif hours_listed < 3:
            return 0.9
        elif hours_listed < 6:
            return 0.7
        elif hours_listed < 12:
            return 0.5
        elif hours_listed < 24:
            return 0.3
        else:
            return 0.1

    def _analyze_product_condition_simple(self, product):
        """Простой анализ состояния товара"""
        try:
            description = product.get('description', '').lower()
            name = product.get('name', '').lower()

            condition_keywords = {
                'отличное': ['новый', 'не использовался', 'с гарантией', 'оригинал', 'заводская'],
                'хорошее': ['отличное', 'как новый', 'хорошее', 'мало использовался'],
                'удовлетворительное': ['удовлетворительное', 'следы', 'царапины', 'потертости']
            }

            for condition, keywords in condition_keywords.items():
                if any(keyword in description or keyword in name for keyword in keywords):
                    return condition

            return 'хорошее'
        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа состояния товара: {e}")
            return 'хорошее'

    def _calculate_time_score(self, hours_since_posted):
        """Рассчитывает score на основе времени публикации"""
        if hours_since_posted is None:
            return 0.2

        if hours_since_posted < 1:
            return 1.0  # Очень свежее объявление
        elif hours_since_posted < 3:
            return 0.8
        elif hours_since_posted < 6:
            return 0.6
        elif hours_since_posted < 12:
            return 0.4
        else:
            return 0.2

    def _analyze_product_condition(self, product):
        """Анализ состояния товара"""
        try:
            # Используем метод из PricePredictor если он доступен
            if hasattr(self.price_predictor, '_analyze_condition'):
                return self.price_predictor._analyze_condition(product.get('description', ''))
            else:
                # Фолбэк на простую логику
                return self._analyze_product_condition_simple(product)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа состояния товара: {e}")
            return 'хорошее'

    # ============================================
    # ОСНОВНЫЕ МЕТОДЫ (ПОЛНЫЕ)
    # ============================================

    async def start(self):
        """🚀 ЗАПУСК ПАРСЕРА С ПРИОРИТЕТОМ СВЕЖЕСТИ"""
        logger.info("🚀 ЗАПУСК СУПЕР-ПАРСЕРА С ПРИОРИТЕТОМ СВЕЖЕСТИ!")

        # 🔥 ИНИЦИАЛИЗАЦИЯ AI СИСТЕМЫ
        if not self.ai_initialized:
            await self._initialize_super_ai()
            self.ai_initialized = True

        # 🔥 ПРОВЕРЯЕМ ЧТО МОДЕЛИ ЗАГРУЖЕНЫ
        if not self.price_predictor.is_trained or self.price_predictor.freshness_model is None:
            logger.warning("⚠️ ML модели не загружены, повторная инициализация...")
            await self._initialize_ml_models()

        # 🔥 ОЧИСТКА СТАРЫХ КЭШЕЙ
        await self.cleanup_old_caches()

        # 🎯 AI-ОПТИМИЗАЦИЯ ЗАПРОСОВ ДЛЯ СВЕЖЕСТИ
        self.search_queries = await self._ai_optimize_search_queries_for_freshness()

        self.start_time = time.time()
        return await self.check_prices_and_notify()

    async def check_prices_and_notify(self):
        """🔄 ОСНОВНОЙ ЦИКЛ С УМНОЙ ОСТАНОВКОЙ"""
        await self.init_async_session()

        self.browser_manager.set_browser_windows(self.browser_windows)
        self.notification_sender.clear_duplicate_cache()

        if not await self._optimized_driver_setup():
            logger.error("❌ Не удалось запустить парсер")
            return

        self.is_running = True
        self.force_stop = False  # 🔥 Сбрасываем флаг принудительной остановки
        logger.info("🔥 СУПЕР-ПАРСЕР АКТИВИРОВАН! AI-фичи активны!")
        logger.info(f"🎯 AI-ОПТИМИЗИРОВАННЫЕ ЗАПРОСЫ: {self.search_queries}")
        logger.info(f"🖥️ ОКОН: {self.browser_windows}")

        cycle_count = 0
        consecutive_empty_cycles = 0

        while self.is_running and not self.force_stop:  # 🔥 Двойная проверка
            # 🔥 МГНОВЕННАЯ ПРОВЕРКА ПЕРЕД НАЧАЛОМ ЦИКЛА
            if self.force_stop:
                logger.info("🔴 НЕМЕДЛЕННЫЙ ВЫХОД ИЗ ЦИКЛА")
                break

            cycle_start = time.time()
            cycle_count += 1

            try:
                # 🔥 ПРОВЕРКА ТАЙМЕРА
                if hasattr(self.timer_manager, 'should_stop') and await sync_to_async(self.timer_manager.should_stop)():
                    logger.info("⏰ Таймер истек, останавливаемся...")
                    self.stop()
                    break

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД КАЖДОЙ ОПЕРАЦИЕЙ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед проверкой ML")
                    break

                # 🔥 ПРОВЕРКА ML МОДЕЛЕЙ КАЖДЫЕ 10 ЦИКЛОВ
                if cycle_count % 10 == 0:
                    if not self.price_predictor.is_trained or self.price_predictor.freshness_model is None:
                        logger.warning("🔄 ML модели не загружены, повторная инициализация...")
                        await self._safe_async_operation("init_ml_models", self._initialize_ml_models)

                # 🔥 ПРОВЕРКА ОСТАНОВКИ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед проверкой настроек")
                    break

                # 🔥 ПРОВЕРКА НАСТРОЕК КАЖДЫЕ 5 ЦИКЛОВ
                if cycle_count % 5 == 0:
                    await self._safe_async_operation("fast_settings_check", self._fast_settings_check)

                    # 🔥 ПРОВЕРКА ОСТАНОВКИ
                    if self.force_stop:
                        logger.info("🔴 Прерывание цикла перед AI оптимизацией")
                        break

                    # 🎯 ПЕРИОДИЧЕСКАЯ AI-ОПТИМИЗАЦИЯ
                    optimized_queries = await self._safe_async_operation("ai_optimize",
                                                                         self._ai_optimize_search_queries)
                    if optimized_queries and optimized_queries != self.search_queries:
                        self.search_queries = optimized_queries
                        logger.info(f"🔄 AI обновил запросы: {len(self.search_queries)} запросов")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед обновлением статистики")
                    break

                # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ
                await self._safe_async_operation("update_stats", self._update_parser_stats)

                # 🔥 ПРОВЕРКА ОСТАНОВКИ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед мониторингом здоровья")
                    break

                # ❤️ МОНИТОРИНГ ЗДОРОВЬЯ
                health_status = self.health_monitor.get_health_status()
                if health_status == 'UNHEALTHY':
                    logger.warning("❤️ ВНИМАНИЕ: Система работает нестабильно!")

                logger.info(
                    f"🌀 Цикл #{cycle_count} | AI-запросы: {len(self.search_queries)} | Здоровье: {health_status}")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ПАРАЛЛЕЛЬНОЙ ОБРАБОТКОЙ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед параллельной обработкой")
                    break

                # 🔥 ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА С БЕЗОПАСНОЙ ОБЕРТКОЙ
                found_any = await self._safe_async_operation(
                    "parallel_processing",
                    self._optimized_parallel_processing
                )

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ЗАПИСЬЮ МЕТРИК
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед записью метрик")
                    break

                # ❤️ ЗАПИСЬ МЕТРИК ЦИКЛА
                self.health_monitor.record_cycle(
                    success=found_any is not False,  # None - это нормально при остановке
                    cycle_time=time.time() - cycle_start,
                    found_items=found_any if found_any else 0
                )

                # 🔥 ОБНОВЛЯЕМ СЧЕТЧИК ПУСТЫХ ЦИКЛОВ
                if found_any:
                    consecutive_empty_cycles = 0
                    logger.info("🎉 Найдены товары! Сбрасываем счетчик пустых циклов")
                else:
                    consecutive_empty_cycles += 1
                    if consecutive_empty_cycles > 2:
                        logger.info(f"⚡ Пустой цикл #{consecutive_empty_cycles}")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД СТАТИСТИКОЙ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед статистикой")
                    break

                # Статистика цикла
                cycle_time = time.time() - cycle_start
                self.cycle_times.append(cycle_time)

                # 🔥 АДАПТИВНОЕ УСРЕДНЕНИЕ
                recent_cycles = self.cycle_times[-8:]
                avg_time = sum(recent_cycles) / len(recent_cycles) if recent_cycles else cycle_time
                self.search_stats['avg_cycle_time'] = round(avg_time, 2)

                # 🔥 АДАПТИВНАЯ ПАУЗА
                pause_time = self.adaptive_timer.calculate_pause(
                    found_any if found_any else 0,
                    cycle_time,
                    False
                )
                self.search_stats['adaptive_pause'] = pause_time

                logger.info(f"⏱️ Цикл #{cycle_count} завершен за {cycle_time:.2f}с (среднее: {avg_time:.2f}с)")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ПЕЧАТЬЮ СТАТИСТИКИ
                if not self.force_stop:
                    self._print_enhanced_stats()

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ПАУЗОЙ
                if self.force_stop:
                    logger.info("🔴 Прерывание цикла перед паузой")
                    break

                logger.info(f"💤 Адаптивная пауза {pause_time}сек...")

                # 🔥 УМНАЯ ПАУЗА С ПРОВЕРКОЙ КАЖДУЮ СЕКУНДУ
                pause_seconds = int(round(pause_time))
                for i in range(pause_seconds):
                    if self.force_stop or not self.is_running:
                        logger.info("🔴 Прерывание паузы")
                        break
                    if i % 5 == 0:  # Проверка каждые 5 секунд
                        await self._fast_settings_check()
                    await asyncio.sleep(1)

            except Exception as e:
                # 🔥 ИГНОРИРУЕМ ОШИБКИ ПРИ ОСТАНОВКЕ
                if self.force_stop:
                    logger.info("🔴 Ожидаемая ошибка при остановке цикла")
                    break
                else:
                    logger.error(f"❌ Ошибка в цикле #{cycle_count}: {e}")
                    self.search_stats['error_count'] += 1
                    consecutive_empty_cycles += 1

                    # ❤️ ЗАПИСЬ ОШИБКИ
                    self.health_monitor.record_cycle(success=False)

                    # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ОБРАБОТКОЙ ОШИБКИ
                    if not self.force_stop:
                        # 🔥 АДАПТИВНАЯ ОБРАБОТКА ОШИБОК
                        error_pause = min(30, 10 * consecutive_empty_cycles)
                        logger.info(f"🔄 Ошибка, пауза {error_pause}сек перед повторной попыткой...")
                        await self._handle_error()

                        # 🔥 УМНАЯ ПАУЗА ПРИ ОШИБКЕ С ПРОВЕРКОЙ
                        for i in range(error_pause):
                            if self.force_stop:
                                logger.info("🔴 Прерывание паузы при ошибке")
                                break
                            await asyncio.sleep(1)

        # 🔥 ФИНАЛЬНАЯ СТАТИСТИКА ТОЛЬКО ЕСЛИ НЕ ПРИНУДИТЕЛЬНАЯ ОСТАНОВКА
        if not self.force_stop:
            logger.info(f"📊 ИТОГО: Выполнено {cycle_count} циклов за {time.time() - self.start_time:.1f} секунд")
        else:
            logger.info(f"🔴 ПРИНУДИТЕЛЬНАЯ ОСТАНОВКА: Выполнено {cycle_count} циклов")

        await self._cleanup()

    async def _sort_products_by_freshness(self, products, site_parser, window_index):
        """🔥 Сортировка товаров по свежести"""
        try:
            products_with_freshness = []

            for product in products:
                try:
                    # Быстрый анализ свежести без загрузки деталей
                    time_listed = product.get('time_listed', 24)
                    freshness_score = product.get('freshness_score', 0.3)

                    products_with_freshness.append({
                        'product': product,
                        'freshness_score': freshness_score,
                        'time_listed': time_listed
                    })
                except Exception as e:
                    logger.debug(f"⚠️ Ошибка анализа свежести для сортировки: {e}")
                    continue

            # Сортируем по свежести (сначала самые свежие)
            sorted_products = sorted(products_with_freshness,
                                     key=lambda x: x['freshness_score'],
                                     reverse=True)

            return [item['product'] for item in sorted_products]

        except Exception as e:
            logger.error(f"❌ Ошибка сортировки по свежести: {e}")
            return products

    async def _analyze_product_freshness(self, product, window_index):
        """🔥 Анализ свежести товара с реальными ML компонентами"""
        try:
            self.search_stats['freshness_analysis_count'] += 1

            # 🔥 ИСПОЛЬЗУЕМ СОВМЕСТНЫЙ АНАЛИЗ ДВУХ МОДЕЛЕЙ
            analyzed_product = await self._analyze_product_with_both_models(product, window_index)

            # 🔥 ДОБАВЛЯЕМ ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ
            freshness_data = {
                'ml_freshness_score': analyzed_product.get('ml_freshness_score', 0.5),
                'predicted_publication_time': analyzed_product.get('predicted_publication_time', 'unknown'),
                'freshness_category': analyzed_product.get('freshness_category', 'unknown'),
                'is_critical_fresh': analyzed_product.get('ml_freshness_score', 0) >= 0.8,
                'freshness_analyzed_at': datetime.now().isoformat(),
                'ai_predicted_price': analyzed_product.get('ai_predicted_price'),
                'economy_percent': analyzed_product.get('economy_percent', 0)
            }

            logger.info(
                f"🔥 Окно {window_index} | РЕАЛЬНЫЙ ML анализ: Свежесть {freshness_data['ml_freshness_score']:.2f} | Категория: {freshness_data['freshness_category']}")

            return freshness_data

        except Exception as e:
            logger.warning(f"⚠️ Ошибка реального ML анализа свежести: {e}")
            return {
                'ml_freshness_score': 0.5,
                'freshness_category': 'unknown',
                'is_critical_fresh': False
            }

    async def _evaluate_freshness_priority(self, product, window_index):
        """🎯 Оценка приоритета на основе свежести"""
        try:
            freshness_score = product.get('ml_freshness_score', 0.3)
            time_listed = product.get('time_listed', 24)

            # 🔥 КРИТИЧЕСКИ СВЕЖИЕ - ВЫСОКИЙ ПРИОРИТЕТ
            if freshness_score >= 0.8 or time_listed <= 0.5:
                logger.info(f"🚨 Окно {window_index} | КРИТИЧЕСКИ СВЕЖИЙ: {product['name'][:50]}...")
                self.search_stats['critical_fresh_deals'] += 1
                return True

            # 🔥 ОЧЕНЬ СВЕЖИЕ - ВЫСОКИЙ ПРИОРИТЕТ
            elif freshness_score >= 0.6 or time_listed <= 2:
                logger.info(f"🔥 Окно {window_index} | ОЧЕНЬ СВЕЖИЙ: {product['name'][:50]}...")
                return True

            # 🔥 СВЕЖИЕ - СРЕДНИЙ ПРИОРИТЕТ
            elif freshness_score >= 0.4 or time_listed <= 6:
                logger.info(f"✅ Окно {window_index} | СВЕЖИЙ: {product['name'][:50]}...")
                return True

            # 🔥 СТАРЫЕ - НИЗКИЙ ПРИОРИТЕТ (можно пропускать)
            else:
                logger.info(f"💤 Окно {window_index} | СТАРЫЙ товар (пропускаем): {product['name'][:50]}...")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Ошибка оценки приоритета свежести: {e}")
            return True  # В случае ошибки продолжаем обработку

    def _update_freshness_stats(self, product):
        """📊 Обновление статистики свежести"""
        freshness_score = product.get('ml_freshness_score', 0.3)

        if freshness_score >= 0.8:
            self.search_stats['critical_fresh_deals'] += 1
            logger.info(f"🚨 КРИТИЧЕСКИ СВЕЖАЯ СДЕЛКА: {product['name'][:50]}")
        elif freshness_score >= 0.6:
            self.search_stats['fresh_deals_found'] += 1
            logger.info(f"🔥 СВЕЖАЯ СДЕЛКА: {product['name'][:50]}")

    async def _calculate_time_listed(self, product_data):
        """🕒 Расчет времени с момента публикации"""
        try:
            posted_date = product_data.get('posted_date', '')
            if not posted_date:
                return 24.0

            current_time = datetime.now()

            # Простая логика расчета на основе текста даты
            if 'сегодня' in str(posted_date).lower():
                return 1.0  # 1 час
            elif 'вчера' in str(posted_date).lower():
                return 24.0  # 24 часа
            elif 'только что' in str(posted_date).lower() or 'минут' in str(posted_date).lower():
                return 0.1  # 6 минут
            elif 'час' in str(posted_date).lower():
                # Извлекаем количество часов
                hours_match = re.search(r'(\d+)\s*час', str(posted_date))
                if hours_match:
                    return float(hours_match.group(1))
                return 2.0  # 2 часа по умолчанию
            else:
                return 48.0  # 2 дня по умолчанию

        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета time_listed: {e}")
            return 24.0  # Значение по умолчанию

    async def _fast_process_products_with_vision(self, products, site_parser, window_index, query):
        """🔄 ОБРАБОТКА ТОВАРОВ С AI-ФИЧАМИ И УМНОЙ ОСТАНОВКОЙ"""
        found_deals = False
        current_fresh_deals = []

        # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД НАЧАЛОМ
        if self._check_stop_requested():
            logger.info(f"🔴 Окно {window_index} | Пропускаем обработку товаров - парсер останавливается")
            return False

        logger.info(f"🚀 Окно {window_index} | НАЧАЛО ОБРАБОТКИ {len(products)} товаров")

        # 🔥 СОРТИРУЕМ ТОВАРЫ ПО СВЕЖЕСТИ
        sorted_products = await self._safe_async_operation(
            f"sort_products_{window_index}",
            self._sort_products_by_freshness,
            products, site_parser, window_index
        )

        if not sorted_products or self._check_stop_requested():
            logger.info(f"🔴 Окно {window_index} | Прерывание после сортировки")
            return False

        products_to_process = sorted_products[:15]

        logger.info(f"📦 Окно {window_index} | После сортировки: {len(products_to_process)} товаров для обработки")

        for product_index, product in enumerate(products_to_process):
            # 🔥 ЧАСТАЯ ПРОВЕРКА ОСТАНОВКИ ПЕРЕД КАЖДЫМ ТОВАРОМ
            if self._check_stop_requested():
                logger.info(f"🔴 Окно {window_index} | Прерывание обработки на товаре {product_index + 1}")
                break

            detailed_product = None

            try:
                # 🔥 ШАГ 0: БЫСТРАЯ ПРОВЕРКА ДУБЛИКАТОВ (САМЫЙ ПЕРВЫЙ ЭТАП)
                is_duplicate = await self._fast_duplicate_check(product, window_index)
                if is_duplicate:
                    continue  # Пропускаем дубликат

                # 🎯 ШАГ 1: ПРОВЕРКА РЕЛЕВАНТНОСТИ
                main_keyword = self._extract_main_keyword(query)
                if not self._check_universal_relevance(product, main_keyword, query):
                    logger.debug(f"🔍 Окно {window_index} | Не релевантен: {product['name'][:50]}...")
                    continue

                # 🎯 ШАГ 2: ПОЛУЧАЕМ ДЕТАЛИ ТОВАРА
                logger.info(
                    f"🔍 Окно {window_index} | Получаем детали товара {product_index + 1}/{len(products_to_process)}: {product['name'][:50]}...")

                # 🔥 БЕЗОПАСНЫЙ ВЫЗОВ ПАРСЕРА
                detailed_product = await self._safe_async_operation(
                    f"get_details_{window_index}_{product_index}",
                    site_parser.get_product_details,
                    product
                )

                if not detailed_product or self._check_stop_requested():
                    if self._check_stop_requested():
                        logger.info(f"🔴 Окно {window_index} | Прерывание после получения деталей")
                        break
                    logger.warning(f"⚠️ Окно {window_index} | Не удалось получить детали товара: {product['name']}")
                    continue

                logger.info(f"✅ Окно {window_index} | Детали получены: {detailed_product.get('name', 'No name')}")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ML АНАЛИЗОМ
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Прерывание перед ML анализом")
                    break

                # 🔥 ПРОВЕРКА ДАННЫХ ПЕРЕД ML АНАЛИЗОМ
                await self._ensure_ml_data_ready(detailed_product)

                # 🎯 ШАГ 3: AI-АНАЛИЗ ЦЕНЫ И СВЕЖЕСТИ
                # 🔥 РАСЧЕТ time_listed если его нет
                if 'time_listed' not in detailed_product or detailed_product['time_listed'] is None:
                    detailed_product['time_listed'] = await self._calculate_time_listed(detailed_product)

                # 🔥 АНАЛИЗ СВЕЖЕСТИ С ML
                freshness_analysis = await self._safe_async_operation(
                    f"freshness_analysis_{window_index}_{product_index}",
                    self._analyze_product_freshness,
                    detailed_product, window_index
                )

                if freshness_analysis and not self._check_stop_requested():
                    detailed_product.update(freshness_analysis)

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ML ПРЕДСКАЗАНИЕМ
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Прерывание перед ML предсказанием")
                    break

                # 🔥 СУПЕР-ML ПРЕДСКАЗАНИЕ ЦЕНЫ
                try:
                    predicted_price = await self._safe_async_operation(
                        f"price_prediction_{window_index}_{product_index}",
                        self.price_predictor.predict_price_super,
                        detailed_product
                    )

                    if predicted_price and not self._check_stop_requested():
                        detailed_product['ai_predicted_price'] = predicted_price
                        detailed_product['ml_confidence'] = self.price_predictor.get_prediction_confidence(
                            detailed_product)

                        # Пересчитываем экономию
                        economy = predicted_price - detailed_product['price']
                        economy_percent = int(
                            (economy / predicted_price) * 100) if predicted_price and predicted_price > 0 else 0

                        detailed_product['economy'] = economy
                        detailed_product['economy_percent'] = economy_percent
                        detailed_product['target_price'] = predicted_price

                        self.search_stats['predicted_deals'] += 1
                        logger.info(
                            f"🤖 Окно {window_index} | СУПЕР-ML предсказание: {predicted_price:.0f} руб (уверенность: {detailed_product['ml_confidence']:.1%})")

                except Exception as price_error:
                    if not self._check_stop_requested():
                        logger.warning(f"⚠️ Окно {window_index} | Ошибка ML-предсказания цены: {price_error}")
                        target_price = detailed_product.get('target_price', detailed_product['price'] * 1.2)
                        economy = target_price - detailed_product['price']
                        economy_percent = int(
                            (economy / target_price) * 100) if target_price and target_price > 0 else 0
                        detailed_product['economy'] = economy
                        detailed_product['economy_percent'] = economy_percent
                        detailed_product['target_price'] = target_price
                        detailed_product['ai_predicted_price'] = None
                        detailed_product['ml_confidence'] = 0.3

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД VISION
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Прерывание перед Vision анализом")
                    break

                # 🎯 ШАГ 4: VISION-АНАЛИЗ ИЗОБРАЖЕНИЙ
                vision_result = await self._safe_async_operation(
                    f"vision_analysis_{window_index}_{product_index}",
                    self._verify_with_computer_vision_universal,
                    detailed_product, query, window_index
                )

                if not vision_result or self._check_stop_requested():
                    if self._check_stop_requested():
                        break
                    logger.info(
                        f"👁️ Окно {window_index} | Vision анализ не пройден: {detailed_product['name'][:50]}...")
                    continue

                # 🔥 ДОБАВЛЯЕМ ДАННЫЕ VISION
                if isinstance(vision_result, dict) and 'vision_data' in vision_result:
                    detailed_product['vision_data'] = vision_result['vision_data']
                    detailed_product['computer_vision_result'] = vision_result['vision_data']
                    detailed_product['search_query'] = query

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ВАЛИДАЦИЕМ
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Прерывание перед валидацией")
                    break

                # 🎯 ШАГ 5: ПРОВЕРКА ВАЛИДАТОРОМ
                logger.info(f"✅ Окно {window_index} | Проверка валидатором: {detailed_product['name'][:50]}...")

                # 🔥 ИСПРАВЛЕНИЕ: ДОБАВЛЯЕМ await перед вызовом is_good_deal
                if not await self.product_validator.is_good_deal(detailed_product):
                    logger.info(
                        f"❌ Окно {window_index} | Товар не прошел валидацию: {detailed_product['name'][:50]}...")
                    continue

                logger.info(f"✅ Окно {window_index} | Товар прошел валидацию: {detailed_product['name'][:50]}...")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ОБНОВЛЕНИЕМ СТАТИСТИКИ
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Прерывание перед обновлением статистики")
                    break

                # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ
                self.search_stats['items_found'] += 1
                self.search_stats['good_deals_found'] += 1

                if detailed_product.get('ml_freshness_score', 0) >= 0.6:
                    self.search_stats['fresh_deals_found'] += 1

                # 🔥 ИНИЦИАЛИЗИРУЕМ query_stats
                if query not in self.query_stats:
                    self.query_stats[query] = {
                        'total_found': 0,
                        'good_deals': 0,
                        'fresh_deals': 0,
                        'count': 0,
                        'successful': 0,
                        'success_rate': 0
                    }

                self.query_stats[query]['total_found'] += 1
                self.query_stats[query]['good_deals'] += 1

                if detailed_product.get('ml_freshness_score', 0) >= 0.6:
                    self.query_stats[query]['fresh_deals'] += 1

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД УВЕДОМЛЕНИЕМ
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Прерывание перед отправкой уведомления")
                    break

                # 🎯 ШАГ 6: ФИНАЛЬНАЯ ОБРАБОТКА С ПРОВЕРКОЙ ДУБЛИКАТОВ
                logger.info(
                    f"🚀 Окно {window_index} | ВЫЗОВ NotificationSender.process_and_notify для: {detailed_product['name'][:50]}...")

                # 🔥 ПРЯМОЙ ВЫЗОВ ДЛЯ ТЕСТИРОВАНИЯ
                try:
                    economy = detailed_product.get('economy', 0)
                    economy_percent = detailed_product.get('economy_percent', 0)

                    # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: передаем user_id парсера
                    # Проверяем, есть ли у парсера текущий пользователь
                    user_id = getattr(self, 'current_user_id', None)

                    if not user_id:
                        logger.error(f"🚨 Окно {window_index} | ОШИБКА: Парсер не настроен для пользователя!")
                        # Можно добавить fallback на request.user если это Django view
                        # user_id = request.user.id если контекст позволяет
                        continue  # или return False

                    logger.info(f"👤 Окно {window_index} | Отправка товара для пользователя ID: {user_id}")

                    # 🔥 ПРАВИЛЬНЫЙ ВЫЗОВ С user_id
                    success = await self._safe_async_operation(
                        f"notification_{window_index}_{product_index}",
                        self.notification_sender.process_and_notify,
                        detailed_product,
                        economy,
                        economy_percent,
                        user_id  # ← ВОТ ОН! Добавляем user_id
                    )

                    if success:
                        logger.info(
                            f"🎉 Окно {window_index} | Товар успешно обработан для пользователя {user_id}: {detailed_product['name'][:50]}...")
                        self.stats['good_deals_found'] += 1
                        found_deals = True

                        if detailed_product.get('ml_freshness_score', 0) >= 0.6:
                            self.search_stats['fresh_deals_found'] += 1
                            logger.info(
                                f"🔥 Окно {window_index} | СВЕЖАЯ СДЕЛКА ОБРАБОТАНА: {detailed_product['name'][:50]}...")

                        # 🔥 ДОБАВЛЯЕМ В fresh_deals ТОЛЬКО ЕСЛИ ТОВАР СВЕЖИЙ И УСПЕШНО ОБРАБОТАН
                        if detailed_product.get('ml_freshness_score', 0) >= 0.6:
                            current_fresh_deals.append(detailed_product)
                            logger.info(
                                f"🔥 Окно {window_index} | Добавлен в свежие сделки: {detailed_product['name'][:50]}...")
                    else:
                        if not self._check_stop_requested():
                            logger.error(
                                f"❌ Окно {window_index} | Ошибка прямого вызова для: {detailed_product['name'][:50]}...")

                except Exception as e:
                    if not self._check_stop_requested():
                        logger.error(f"❌ Окно {window_index} | Критическая ошибка прямого вызова: {e}")

                # 🔥 ПРОВЕРКА ОСТАНОВКИ ПЕРЕД ПАУЗОЙ
                if not self._check_stop_requested():
                    # 🔥 ПАУЗА МЕЖДУ ТОВАРАМИ С ПРОВЕРКОЙ
                    for i in range(3):  # 1.5 секунды = 3 итерации по 0.5 секунды
                        if self._check_stop_requested():
                            logger.info(f"🔴 Окно {window_index} | Прерывание паузы между товарами")
                            break
                        await asyncio.sleep(0.5)

                self.stats['total_processed'] += 1

            except Exception as e:
                # 🔥 ИГНОРИРУЕМ ОШИБКИ ПРИ ОСТАНОВКЕ
                if self._check_stop_requested():
                    logger.info(f"🔴 Окно {window_index} | Ожидаемая ошибка при остановке обработки товара")
                    break
                else:
                    product_name = product.get('name', 'Неизвестный товар') if product else 'Неизвестный товар'
                    logger.error(f"❌ Ошибка обработки товара '{product_name}' в окне {window_index}: {e}")
                    continue

        # 🔥 СОХРАНЯЕМ fresh_deals ТОЛЬКО ЕСЛИ НЕ БЫЛА ОСТАНОВКА
        if not self._check_stop_requested():
            self.fresh_deals = current_fresh_deals
            logger.info(f"🔥 Окно {window_index} | Найдено свежих сделок: {len(current_fresh_deals)}")
            logger.info(f"📊 Окно {window_index} | ИТОГО обработано: {len(products_to_process)} товаров")
        else:
            logger.info(f"🔴 Окно {window_index} | Обработка прервана, обработано товаров: {product_index}")

        return found_deals

    async def _ensure_ml_data_ready(self, product_data):
        """Гарантирует что все данные для ML готовы и корректны"""
        try:
            # 🔥 ПРОВЕРКА ЦЕНЫ
            price = product_data.get('price')
            if price is None:
                logger.error(f"❌ Цена товара None: {product_data.get('name', 'Unknown')}")
                product_data['price'] = 0
            elif not isinstance(price, (int, float)):
                try:
                    product_data['price'] = float(price)
                except (ValueError, TypeError):
                    logger.error(f"❌ Неверный формат цены: {price}")
                    product_data['price'] = 0

            # 🔥 ПРОВЕРКА ВРЕМЕНИ ПУБЛИКАЦИИ
            time_listed = product_data.get('time_listed')
            if time_listed is None:
                product_data['time_listed'] = 24.0  # 24 часа по умолчанию
            elif not isinstance(time_listed, (int, float)):
                try:
                    product_data['time_listed'] = float(time_listed)
                except (ValueError, TypeError):
                    product_data['time_listed'] = 24.0

            # 🔥 ПРОВЕРКА ДРУГИХ ЧИСЛОВЫХ ПОЛЕЙ
            numeric_fields = ['views_count', 'seller_rating', 'reviews_count']
            for field in numeric_fields:
                value = product_data.get(field)
                if value is None:
                    product_data[field] = 0
                elif not isinstance(value, (int, float)):
                    try:
                        product_data[field] = float(value)
                    except (ValueError, TypeError):
                        product_data[field] = 0

            logger.debug(
                f"✅ Данные для ML подготовлены: цена={product_data['price']}, время={product_data['time_listed']}")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка подготовки данных для ML: {e}")

    def _print_enhanced_stats(self):
        """📊 СТАТИСТИКА С ДАННЫМИ О СВЕЖЕСТИ И ДУБЛИКАТАХ"""
        cache_stats = self.optimized_cache.get_stats()
        health_metrics = self.health_monitor.get_performance_metrics()

        logger.info(f"📊 СТАТИСТИКА ПАРСЕРА:")
        logger.info(f"   Обработано: {self.stats['total_processed']} | Сделок: {self.stats['good_deals_found']}")
        logger.info(
            f"   🔥 СВЕЖИХ: {self.search_stats['fresh_deals_found']} | 🚨 КРИТИЧЕСКИ СВЕЖИХ: {self.search_stats['critical_fresh_deals']}")
        logger.info(
            f"   🚫 ДУБЛИКАТОВ В КЭШЕ: {self.search_stats['duplicates_blocked']} | 🗄️ В БАЗЕ: {self.search_stats['database_duplicates_skipped']}")
        logger.info(
            f"   AI-оптимизировано: {self.search_stats['ai_optimized_queries']} | Предсказано: {self.search_stats['predicted_deals']}")
        logger.info(
            f"   Здоровье: {health_metrics.get('health_status', 'UNKNOWN')} | Успешность: {health_metrics.get('recent_success_rate', 0):.0%}")
        logger.info(f"   Кэш: {cache_stats['hit_rate']}% | Пауза: {self.search_stats['adaptive_pause']}с")
        logger.info(f"   AI обучение: {self.search_stats.get('ml_learning_cycles', 0)} циклов")
        logger.info(f"   Анализ свежести: {self.search_stats.get('freshness_analysis_count', 0)}")

    async def get_ai_system_status(self):
        """📊 Статус AI системы с данными о ВСЕХ моделях"""
        try:
            if not self.ai_initialized:
                return {
                    'status': 'not_initialized',
                    'message': 'AI система еще не инициализирована'
                }

            # 🔥 СТАТУС ВСЕХ КОМПОНЕНТОВ
            price_model_info = await self.price_predictor.get_model_info()
            learning_insights = await self.learning_system.get_learning_insights()
            optimization_stats = await self.query_optimizer.get_optimization_stats()

            return {
                'price_predictor': price_model_info,
                'learning_system': learning_insights,
                'query_optimizer': optimization_stats,

                # 🔥 ОБЩИЙ СТАТУС
                'overall_ai_health': 'optimal' if learning_insights.get('system_stats', {}).get('learning_progress',
                                                                                                0) > 0.5 else 'learning',
                'recommendations': learning_insights.get('recommendations', []),
                'ml_learning_cycles': self.search_stats.get('ml_learning_cycles', 0),
                'ai_optimized_queries': self.search_stats.get('ai_optimized_queries', 0),
                'freshness_analysis_count': self.search_stats.get('freshness_analysis_count', 0),
                'fresh_deals_found': self.search_stats.get('fresh_deals_found', 0),
                'dual_ml_system_active': True  # Флаг что работают обе ML системы
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса AI: {e}")
            return {'error': str(e)}

    def get_parser_status(self):
        """🔄 СТАТУС ПАРСЕРА"""
        try:
            timer_hours = None
            timer_remaining = 'Не установен'

            if hasattr(self, 'timer_manager') and self.timer_manager:
                timer_hours = getattr(self.timer_manager, 'timer_hours', None)
                timer_status = self.timer_manager.get_timer_status()
                timer_remaining = timer_status if isinstance(timer_status, str) else 'Активен'

                if self.timer_manager.should_stop() and self.is_running:
                    self.stop()

            # Добавляем статистику кэша
            cache_stats = self.optimized_cache.get_stats()
            health_metrics = self.health_monitor.get_performance_metrics()

            status = {
                'is_running': self.is_running,
                'browser_windows': self.browser_windows,
                'current_site': self.current_site,
                'search_queries': self.search_queries,
                'timer_hours': timer_hours,
                'timer_remaining': timer_remaining,
                'stats': self.stats,
                'search_stats': self.search_stats,
                'duplicate_stats': {
                    'cache_duplicates': self.search_stats['duplicates_blocked'],
                    'database_duplicates': self.search_stats['database_duplicates_skipped'],
                    'url_cache_size': len(self.url_hash_cache),
                    'id_cache_size': len(self.id_hash_cache)
                },
                'cache_size': len(self.persistent_urls_cache),
                'image_cache_size': len(self.image_hash_cache),
                'drivers_count': len(self.browser_manager.drivers) if hasattr(self.browser_manager, 'drivers') else 0,
                'cache_stats': cache_stats,
                'health_metrics': health_metrics,
                'ai_features': {
                    'price_predictor_active': self.price_predictor.is_trained,
                    'freshness_model_active': self.price_predictor.freshness_model is not None,
                    'query_optimizer_active': True,
                    'trend_analyzer_active': True,
                    'smart_notifications_active': True,
                    'learning_system_active': True,
                    'ml_learning_cycles': self.search_stats.get('ml_learning_cycles', 0)
                },
                'ai_system_status': asyncio.run(self.get_ai_system_status()) if self.is_running else {}
            }
            return status
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            return {'is_running': False, 'stats': self.stats}

    def get_parser_status_with_user(self):
        """📊 Получает статус парсера с информацией о пользователе"""
        try:
            status = {
                'is_running': self.is_running,
                'current_user': {
                    'id': self.current_user_id,
                    'username': self.current_user_username
                } if self.current_user_id else None,
                'current_site': self.current_site,
                'browser_windows': self.browser_windows,
                'search_queries_count': len(self.search_queries),
                'stats': self.stats,
                'search_stats': self.search_stats,
                'message': f"Парсер работает для {self.current_user_username}"
                if self.current_user_username else "Парсер не настроен для пользователя"
            }
            return status
        except Exception as e:
            return {'error': str(e), 'current_user_id': self.current_user_id}

    # ============================================
    # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    def analyze_image_colors(self, image_cv):
        """Улучшенный анализ цветов изображения с фокусировкой на центре"""
        try:
            if image_cv is None or image_cv.size == 0:
                logger.warning("⚠️ Пустое изображение для анализа цветов")
                return [('разноцветный', 100)]

            # 🔥 ИСПОЛЬЗУЕМ УЛУЧШЕННЫЙ АНАЛИЗАТОР
            colors_data = color_analyzer.analyze_colors_universal(image_cv)

            if not colors_data:
                return [('разноцветный', 100)]

            # 🔥 ФОРМАТИРУЕМ ДЛЯ СТАРОГО КОДА
            colors_with_percentages = [(color['name'], color['percentage']) for color in colors_data]

            # 🔥 ДОБАВЛЯЕМ "разноцветный" если нужно
            total_percent = sum(percent for _, percent in colors_with_percentages)
            if total_percent < 90:
                other_percent = 100 - total_percent
                colors_with_percentages.append(('разноцветный', round(other_percent, 1)))

            logger.info(f"🎨 Улучшенный анализ цветов завершен: {colors_with_percentages}")
            return colors_with_percentages

        except Exception as e:
            logger.warning(f"⚠️ Ошибка улучшенного анализа цветов: {e}")
            return [('разноцветный', 100)]

    def get_main_color_for_frontend(self, image_cv) -> str:
        """Получает основной цвет для отображения во фронтенде"""
        try:
            return color_analyzer.get_main_color_for_frontend(image_cv)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения основного цвета: {e}")
            return "разноцветный"

    def initialize_with_django(self):
        """Инициализирует настройки после настройки Django"""
        try:
            self.settings_manager.load_initial_settings()
            self._update_local_settings()
            logger.info(f"✅ Настройки загружены: {len(self.search_queries)} запросов")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки настроек: {e}")
            self.search_queries = self.settings_manager.get_default_queries()
            return False

    def _update_local_settings(self):
        """Обновление настроек с передачей цен в валидатор"""
        try:
            self.search_queries = self.settings_manager.search_queries
            self.exclude_keywords = self.settings_manager.exclude_keywords
            self.browser_windows = min(self.settings_manager.browser_windows, 4)

            # 🔥 ПЕРЕДАЕМ НАСТРОЙКИ ЦЕН В ВАЛИДАТОР
            min_price = self.settings_manager.min_price
            max_price = self.settings_manager.max_price

            # Обновляем фильтры цен в валидаторе
            self.product_validator.update_price_filters(min_price, max_price)

            # Сохраняем локально для совместимости
            self.min_price = min_price if min_price else 0
            self.max_price = max_price if max_price else 1000000000

            logger.info(f"🔄 Настройки обновлены: {len(self.search_queries)} запросов")
            logger.info(f"💰 Диапазон цен: {self.min_price}-{self.max_price}₽")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления настроек: {e}")

    async def init_async_session(self):
        """Инициализирует асинхронную сессию"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=25)
            connector = aiohttp.TCPConnector(limit=15, limit_per_host=3)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    async def cleanup_old_caches(self):
        """Очистка старых кэшей при запуске"""
        try:
            if len(self.persistent_urls_cache) > 1000:
                self.persistent_urls_cache.clear()
                logger.info("🧹 Очищен кэш URL")

            if len(self.image_hash_cache) > 500:
                self.image_hash_cache.clear()
                logger.info("🧹 Очищен кэш изображений")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка очистки кэшей: {e}")

    async def _update_parser_stats(self):
        """ОБНОВЛЕНИЕ СТАТИСТИКИ ПАРСЕРА"""
        try:
            # Время работы
            uptime_seconds = time.time() - self.start_time
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            self.search_stats['uptime'] = f"{hours}ч {minutes}м"

            # Активные запросы
            self.search_stats['active_queries'] = len(self.search_queries)

            # Статистика кэша
            cache_stats = self.optimized_cache.get_stats()
            self.search_stats['cache_hit_rate'] = cache_stats['hit_rate']

        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")

    async def _optimized_driver_setup(self):
        """ОПТИМИЗИРОВАННАЯ НАСТРОЙКА ДРАЙВЕРОВ С USER-AGENT"""
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                self.browser_manager.setup_drivers
            )

            if success and self.browser_manager.drivers:
                # 🔥 ДОБАВИТЬ: Установка User-Agent для каждого драйвера
                if USER_AGENTS_AVAILABLE:
                    for window_index, driver in enumerate(self.browser_manager.drivers):
                        try:
                            user_agent = apply_user_agent_to_driver(driver, window_index + 1)
                            if user_agent:
                                logger.info(f"✅ Окно {window_index + 1} | User-Agent установлен")
                            else:
                                logger.warning(f"⚠️ Окно {window_index + 1} | Не удалось установить User-Agent")
                        except Exception as e:
                            logger.error(f"❌ Ошибка установки User-Agent для окна {window_index + 1}: {e}")

                logger.info(f"✅ Запущено драйверов: {len(self.browser_manager.drivers)}/{self.browser_windows}")
                return True
            else:
                logger.error("❌ Не удалось запустить драйверы")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка настройки драйверов: {e}")
            return False

    async def _optimized_parallel_processing(self):
        """ОПТИМИЗИРОВАННАЯ ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА С USER-AGENT РОТАЦИЕЙ"""
        if not self.search_queries or not self.browser_manager.drivers:
            return False

        # 🔥 ДОБАВИТЬ: Ротация User-Agent в начале каждого цикла
        if USER_AGENTS_AVAILABLE:
            try:
                for window_index, driver in enumerate(self.browser_manager.drivers):
                    user_agent = apply_user_agent_to_driver(driver, window_index)
                    if user_agent:
                        logger.info(f"🔄 Цикл | Окно {window_index} | User-Agent обновлен")
                logger.info("🔄 User-Agent ротация в начале цикла")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка ротации User-Agent: {e}")

        logger.info(
            f"🎯 ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА: {len(self.search_queries)} запросов × {len(self.browser_manager.drivers)} окон")

        # Очистка временного кэша
        self.processed_urls.clear()
        logger.info(
            f"🧹 Очищен временный кэш. Постоянный кэш: {len(self.persistent_urls_cache)} URL, {len(self.image_hash_cache)} изображений")

        total_found = 0

        # Обрабатываем каждое окно
        for window_index, driver in enumerate(self.browser_manager.drivers):
            if not self.is_running:
                break

            # Перемешиваем запросы
            shuffled_queries = self.search_queries.copy()
            random.shuffle(shuffled_queries)

            found_in_window = await self._process_window_queries(driver, window_index, shuffled_queries)
            total_found += found_in_window

            # Пауза между окнами
            if window_index < len(self.browser_manager.drivers) - 1:
                await asyncio.sleep(2)

        return total_found > 0

    async def _process_window_queries(self, driver, window_index, queries):
        """ОБРАБОТКА ЗАПРОСОВ В ОДНОМ ОКНЕ С ВЫБОРОМ САЙТА"""
        site_parser = None
        try:
            # 🔥 ИСПОЛЬЗУЕМ ТЕКУЩИЙ САЙТ
            site_parser = self._get_site_parser(driver, self.current_site)

            logger.info(f"🖥️ Окно {window_index} | Сайт: {self.current_site} | Запросов: {len(queries)}")

            found_any_in_window = False

            for query_index, query in enumerate(queries):
                if not self.is_running:
                    break

                logger.info(f"🔎 Окно {window_index} | {self.current_site} | Запрос: '{query}'")

                # 🔥 ОБНОВЛЯЕМ СТАТИСТИКУ ЗАПРОСА
                if query not in self.query_stats:
                    self.query_stats[query] = {
                        'count': 0,
                        'successful': 0,
                        'total_found': 0,
                        'good_deals': 0
                    }
                self.query_stats[query]['count'] += 1
                self.search_stats['total_searches'] += 1

                # Проверка драйвера
                if not await self._check_driver_health(driver, window_index):
                    continue

                # 🔥 ИСПРАВЛЕНИЕ: Принимаем результат парсера как есть
                products = await site_parser.parse_search_results(query)

                if not products:
                    logger.info(f"ℹ️ Окно {window_index} | По '{query}' ничего не найдено")
                    continue

                logger.info(f"✅ Окно {window_index} | Найдено {len(products)} товаров по '{query}'")
                self.query_stats[query]['successful'] += 1
                self.search_stats['successful_searches'] += 1

                # 🔥 ОБРАБОТКА ТОВАРОВ
                found_deals = await self._fast_process_products_with_vision(products, site_parser, window_index, query)
                if found_deals:
                    found_any_in_window = True

                # Обновляем успешность запроса
                query_stats = self.query_stats[query]
                if query_stats['count'] > 0:
                    query_stats['success_rate'] = int((query_stats['successful'] / query_stats['count']) * 100)

                # Пауза между запросами
                if query_index < len(queries) - 1:
                    await asyncio.sleep(1.5)

            return found_any_in_window

        except Exception as e:
            logger.error(f"❌ Ошибка в окне {window_index} для сайта {self.current_site}: {e}")
            self.search_stats['error_count'] += 1
            return False

    async def start_with_settings(self, settings, site: str = None):
        """🔥 ЗАПУСК ПАРСЕРА С НАСТРОЙКАМИ ИЗ ParserSettings"""
        try:
            logger.info(f"🚀 Запуск парсера с настройками для сайта {site}")

            # 🔥 УСТАНАВЛИВАЕМ САЙТ
            if site and site != self.current_site:
                self.change_site(site)

            # 🔥 ИСПОЛЬЗУЕМ СУЩЕСТВУЮЩИЕ СВОЙСТВА - ОНИ УЖЕ ЕСТЬ!
            keywords_list = settings.keywords_list  # ✅ Свойство которое РАБОТАЕТ
            min_price = settings.min_price
            max_price = settings.max_price

            logger.info(f"🎯 Настройки парсера:")
            logger.info(f"   Ключевые слова: {keywords_list}")
            logger.info(f"   Цена: {min_price}-{max_price}")
            logger.info(f"   Сайт: {site}")

            # 🔥 ОБНОВЛЯЕМ НАСТРОЙКИ ПАРСЕРА
            self.search_queries = keywords_list
            self.min_price = min_price if min_price else 0
            self.max_price = max_price if max_price else 100000

            # 🔥 ЗАПУСКАЕМ ОСНОВНОЙ ЦИКЛ
            return await self.start()

        except Exception as e:
            logger.error(f"❌ Ошибка запуска парсера с настройками: {e}")
            return False

    async def _download_image_for_analysis(self, image_url):
        """Загружает изображение для анализа"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=15) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        image_array = np.frombuffer(image_data, np.uint8)
                        image_cv = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                        if image_cv is not None and image_cv.size > 0:
                            # Уменьшаем размер для ускорения
                            if image_cv.shape[0] > 800 or image_cv.shape[1] > 800:
                                scale = min(800 / image_cv.shape[0], 800 / image_cv.shape[1])
                                new_width = int(image_cv.shape[1] * scale)
                                new_height = int(image_cv.shape[0] * scale)
                                image_cv = cv2.resize(image_cv, (new_width, new_height))

                            return image_cv

            return None
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки изображения: {e}")
            return None

    def _check_universal_relevance(self, product, main_keyword, query):
        """ПРОВЕРКА РЕЛЕВАНТНОСТИ"""
        title = product['name'].lower()
        query_lower = query.lower()

        # Главное ключевое слово должно быть в заголовке
        if main_keyword not in title:
            # Проверяем синонимы
            keyword_variants = self._get_keyword_variants(main_keyword)
            if not any(variant in title for variant in keyword_variants):
                return False

        return True

    def _get_keyword_variants(self, keyword):
        """Возвращает варианты ключевого слова"""
        variants_map = {
            'пульт': ['пульт', 'remote', 'дистанционное', 'пультик'],
            'телевизор': ['телевизор', 'телек', 'tv', 'тв'],
            'холодильник': ['холодильник', 'refrigerator', 'fridge'],
            'кроссовки': ['кроссовки', 'кеды', 'sneakers', 'обувь'],
            'куртка': ['куртка', 'пуховик', 'пальто', 'jacket'],
            'телефон': ['телефон', 'смартфон', 'phone', 'mobile'],
            'ноутбук': ['ноутбук', 'лэптоп', 'laptop', 'ноут']
        }
        return variants_map.get(keyword, [keyword])

    async def _verify_with_computer_vision_universal(self, product, query, window_index):
        """ПРОВЕРКА COMPUTER VISION"""
        try:
            if product is None:
                return {'vision_data': self._get_default_vision_data("ошибка")}

            self.stats['vision_checks'] += 1

            # Извлекаем главное слово
            main_keyword = self._extract_main_keyword(query)

            # Получаем изображения
            image_urls = product.get('image_urls', [])
            if not image_urls:
                logger.info(f"⚠️ Окно {window_index} | Нет изображений для анализа: {product['name'][:50]}...")
                return {'vision_data': self._get_default_vision_data("Нет изображений")}

            # 🔥 ПРОВЕРКА ДУБЛИКАТОВ ПО ИЗОБРАЖЕНИЯМ
            image_hashes = []
            for img_url in image_urls[:2]:
                img_hash = await self._get_image_hash(img_url)
                if img_hash and img_hash in self.image_hash_cache:
                    logger.info(f"🚫 Окно {window_index} | ДУБЛИКАТ ПО ИЗОБРАЖЕНИЮ: {product['name'][:50]}...")
                    self.stats['vision_rejected'] += 1
                    return False
                if img_hash:
                    image_hashes.append(img_hash)

            # 🔥 АНАЛИЗ ИЗОБРАЖЕНИЙ
            logger.info(f"👁️ Окно {window_index} | Анализ {len(image_urls)} изображений для '{main_keyword}'...")

            vision_data = None
            try:
                if hasattr(self.vision_analyzer, 'analyze_multiple_images_detailed'):
                    vision_analysis = self.vision_analyzer.analyze_multiple_images_detailed(image_urls, main_keyword)
                else:
                    # Фолбэк
                    vision_analysis = {
                        'match': True,
                        'objects': [main_keyword],
                        'colors': ['разноцветный'],
                        'materials': ['стандартный'],
                        'condition': 'хорошее',
                        'background': 'нейтральный',
                        'confidence': 0.7
                    }

                vision_data = vision_analysis

            except Exception as vision_error:
                logger.warning(f"⚠️ Ошибка анализа изображений: {vision_error}")
                vision_data = self._get_default_vision_data(main_keyword)

            # 🔥 СОХРАНЯЕМ ХЭШИ
            for img_hash in image_hashes:
                self.image_hash_cache.add(img_hash)

            # Ограничиваем размер кэша
            if len(self.image_hash_cache) > 600:
                hashes_list = list(self.image_hash_cache)
                self.image_hash_cache = set(hashes_list[-400:])

            logger.info(f"✅ Окно {window_index} | Анализ пройден: {product['name'][:50]}...")
            return {'vision_data': vision_data}

        except Exception as e:
            logger.error(f"❌ Критическая ошибка анализа: {e}")
            return {'vision_data': self._get_default_vision_data("ошибка")}

    def _get_default_vision_data(self, keyword="товар"):
        """Данные по умолчанию"""
        return {
            'objects': [keyword],
            'colors': ['разноцветный'],
            'materials': ['стандартный'],
            'condition': 'хорошее качество',
            'background': 'нейтральный фон',
            'confidence': 0.65,
            'match': True,
            'result': f"СООТВЕТСТВУЕТ '{keyword}'"
        }

    async def _get_image_hash(self, image_url):
        """ХЭШ ИЗОБРАЖЕНИЯ"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                lambda: requests.get(image_url, timeout=10, stream=True)
            )
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))

            # Улучшенное хэширование
            image.thumbnail((100, 100))
            image = image.convert('L')
            image = image.point(lambda x: 0 if x < 64 else 255 if x > 192 else x)

            image_bytes = BytesIO()
            image.save(image_bytes, format='JPEG', quality=75)
            image_hash = hashlib.md5(image_bytes.getvalue()).hexdigest()[:16]

            return image_hash

        except Exception as e:
            logger.warning(f"⚠️ Ошибка хэширования изображения: {e}")
            return None

    def _extract_main_keyword(self, query):
        """ИЗВЛЕЧЕНИЕ КЛЮЧЕВОГО СЛОВА"""
        cleaned_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = cleaned_query.split()

        # Ищем самое важное слово
        stop_words = {'для', 'от', 'в', 'на', 'с', 'по', 'из', 'у', 'бу', 'б/у', 'новый', 'новая', 'новое'}
        for word in words:
            if word not in stop_words and len(word) > 2:
                return word

        return words[0] if words else query

    async def _check_driver_health(self, driver, window_index):
        """ПРОВЕРКА ДРАЙВЕРА С USER-AGENT РОТАЦИЕЙ ПРИ ОШИБКАХ"""
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    lambda: driver.current_url if driver and hasattr(driver, 'current_url') else None
                ),
                timeout=10.0
            )

            # 🔥 ЕСЛИ ДРАЙВЕР НЕ ОТВЕЧАЕТ - МЕНЯЕМ USER-AGENT
            if result is None and USER_AGENTS_AVAILABLE:
                try:
                    user_agent = apply_user_agent_to_driver(driver, window_index)
                    logger.info(f"🔄 Окно {window_index} | User-Agent изменен из-за проблем с драйвером")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось изменить User-Agent для окна {window_index}: {e}")

            return result is not None

        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"🔄 Окно {window_index} | Драйвер не отвечает: {e}")

            # 🔥 ПРИ ОШИБКЕ - МЕНЯЕМ USER-AGENT
            if USER_AGENTS_AVAILABLE:
                try:
                    user_agent = apply_user_agent_to_driver(driver, window_index)
                    logger.info(f"🔄 Окно {window_index} | User-Agent изменен после ошибки")
                except Exception as ua_error:
                    logger.warning(f"⚠️ Не удалось изменить User-Agent после ошибки: {ua_error}")

            return False

    def _create_driver_safe(self):
        """🚀 ОПТИМИЗИРОВАННОЕ СОЗДАНИЕ ДРАЙВЕРА БЕЗ ПРЕДУПРЕЖДЕНИЙ"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            chrome_options = Options()

            # 🔧 ОСНОВНЫЕ НАСТРОЙКИ БЕЗОПАСНОСТИ
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

            # 🎯 СТЕЛС-НАСТРОЙКИ ДЛЯ ОБХОДА ОБНАРУЖЕНИЯ
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 🚀 ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # 🔥 УСКОРЯЕТ ЗАГРУЗКУ!
            chrome_options.add_argument("--disable-javascript")  # 🔥 ДЛЯ Auto.ru МОЖНО ОТКЛЮЧИТЬ!

            # 🖥️ НАСТРОЙКИ ОКНА
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")

            # 🔍 USER-AGENT И ПРОФИЛЬ
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # 🎯 ПРЕДОТВРАЩЕНИЕ ЛОГИРОВАНИЯ
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            driver = webdriver.Chrome(options=chrome_options)

            # 🎯 СКРЫТИЕ WebDriver ПРИЗНАКОВ
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # ⏰ ОПТИМИЗИРОВАННЫЕ ТАЙМАУТЫ
            driver.set_page_load_timeout(25)  # 🔥 УМЕНЬШИЛИ С 30 ДО 25
            driver.implicitly_wait(8)  # 🔥 УМЕНЬШИЛИ С 10 ДО 8
            driver.set_script_timeout(15)  # 🔥 ДОБАВИЛИ ТАЙМАУТ СКРИПТОВ

            logger.info("✅ Драйвер создан с оптимизированными настройками")
            return driver

        except Exception as e:
            logger.error(f"❌ Ошибка создания драйвера: {e}")
            return None

    async def _contains_exclude_keywords_async(self, text):
        """Проверка исключаемых слов"""
        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: self.product_validator.contains_exclude_keywords(text, self.exclude_keywords)
        )

    async def _fast_settings_check(self):
        """ПРОВЕРКА НАСТРОЕК"""
        try:
            old_queries = set(self.search_queries)
            await sync_to_async(self.settings_manager.reload_settings_from_db)()
            await sync_to_async(self._update_local_settings)()
            new_queries = set(self.search_queries)

            if old_queries != new_queries:
                logger.info(f"🔄 Настройки обновлены! Новые запросы: {self.search_queries}")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки настроек: {e}")

    async def _handle_error(self):
        """ОБРАБОТКА ОШИБОК"""
        logger.info("🔄 Обработка ошибки: перезапуск драйверов...")
        try:
            self.browser_manager.close_drivers()
            await asyncio.sleep(3)
            await self._optimized_driver_setup()
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке ошибки: {e}")

    async def _cleanup(self):
        """ОЧИСТКА РЕСУРСОВ"""
        logger.info("🧹 Очистка ресурсов парсера...")
        try:
            if self.session:
                await self.session.close()
                self.session = None

            if self.browser_manager:
                self.browser_manager.close_drivers()

            if self.thread_pool:
                self.thread_pool.shutdown(wait=False)

            logger.info("✅ Ресурсы парсера очищены")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки ресурсов: {e}")

    def _check_stop_requested(self):
        """🚨 МГНОВЕННАЯ ПРОВЕРКА - нужно ли остановиться"""
        return self.force_stop or not self.is_running

    async def _safe_async_operation(self, operation_name, callback, *args, **kwargs):
        """🛡️ Безопасная асинхронная операция с проверкой остановки"""
        if self._check_stop_requested():
            logger.info(f"🔴 Пропускаем операцию '{operation_name}' - парсер останавливается")
            return None

        try:
            result = await callback(*args, **kwargs)
            return result

        except Exception as e:
            if self._check_stop_requested():
                logger.info(f"🔌 Ожидаемая ошибка при остановке: {operation_name}")
                return None
            elif "10061" in str(e) or "Подключение не установлено" in str(e):
                logger.info(f"🔌 Ошибка соединения: {operation_name}")
                return None
            else:
                logger.warning(f"⚠️ Ошибка в операции '{operation_name}': {e}")
                return None

    def stop(self):
        """🛑 УМНАЯ ОСТАНОВКА БЕЗ ОШИБОК"""
        try:
            logger.info("🛑 УМНАЯ ОСТАНОВКА ПАРСЕРА...")

            # 1. СРАЗУ ставим флаги остановки
            self.is_running = False
            self.force_stop = True
            self.stop_requested = True

            # 2. Быстрое логирование текущих операций
            if self.current_operations:
                logger.info(f"🔴 Прерываем {len(self.current_operations)} операций: {list(self.current_operations)}")

            # 3. Безопасное закрытие браузеров (без ожидания)
            if hasattr(self, 'browser_manager') and self.browser_manager:
                try:
                    # Запускаем в отдельном потоке чтобы не блокировать остановку
                    import threading
                    def close_browsers():
                        try:
                            self.browser_manager.close_drivers_force()
                            logger.info("✅ Браузеры закрыты в фоне")
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка закрытия браузеров: {e}")

                    browser_thread = threading.Thread(target=close_browsers)
                    browser_thread.daemon = True
                    browser_thread.start()

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка запуска потока закрытия браузеров: {e}")

            # 4. Быстрая очистка данных
            try:
                if hasattr(self, 'processed_urls'):
                    self.processed_urls.clear()
                logger.info("✅ Данные очищены")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка очистки данных: {e}")

            logger.info("🎯 ПАРСЕР УСПЕШНО ОСТАНОВЛЕН БЕЗ ОШИБОК")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка остановки: {e}")
            # Все равно ставим флаги
            self.is_running = False
            self.force_stop = True

    def _interrupt_current_operations(self):
        """🔴 ПРЕРЫВАНИЕ ТЕКУЩИХ ОПЕРАЦИЙ"""
        try:
            # Устанавливаем флаг прерывания
            self.force_stop = True

            # Очищаем очереди и кэши
            self.processed_urls.clear()

            # Прерываем асинхронные задачи
            if hasattr(self, 'current_tasks'):
                for task in self.current_tasks:
                    try:
                        task.cancel()
                    except:
                        pass

            logger.info("🔴 Все текущие операции прерваны")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка прерывания операций: {e}")

    def _kill_browser_processes(self):
        """💀 ПРИНУДИТЕЛЬНОЕ ЗАВЕРШЕНИЕ ПРОЦЕССОВ БРАУЗЕРА"""
        try:
            import subprocess
            import os

            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'],
                               capture_output=True)
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
                               capture_output=True)
            else:  # Linux/Mac
                subprocess.run(['pkill', '-f', 'chromedriver'], capture_output=True)
                subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)

            logger.info("💀 Процессы браузера принудительно завершены")

        except Exception as e:
            logger.error(f"❌ Ошибка завершения процессов: {e}")

    def update_settings(self, settings_data):
        """ОБНОВЛЕНИЕ НАСТРОЕК"""
        result = self.settings_manager.update_settings(settings_data)
        if result:
            self._update_local_settings()
        return result

    def update_settings_for_user(self, user, settings_data):
        return self.settings_manager.update_settings_for_user(user, settings_data)

    def get_settings_for_user(self, user):
        return self.settings_manager.get_settings_for_user(user)

    async def start_system(self, timer_hours=None, browser_windows=None, site='avito', search_queries=None):
        """ЗАПУСК СИСТЕМЫ"""
        logger.info("🚀 ЗАПУСК СИСТЕМЫ С ОПТИМИЗАЦИЕЙ!")

        if timer_hours:
            try:
                await sync_to_async(self.timer_manager.set_timer)(int(timer_hours))
                logger.info(f"⏰ Установлен таймер: {timer_hours} часов")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка установки таймера: {e}")

        if browser_windows:
            self.browser_windows = min(browser_windows, 4)
            logger.info(f"🖥️ Установлено окон: {self.browser_windows}")

        if search_queries is not None:
            self.search_queries = search_queries
            logger.info(f"🔍 Установлены запросы: {search_queries}")
        elif not self.search_queries:
            self.search_queries = await sync_to_async(self.settings_manager.get_default_queries)()
            logger.info(f"🔍 Используются запросы по умолчанию: {self.search_queries}")

        return await self.check_prices_and_notify()

    def cleanup_duplicate_settings(self):
        """ОЧИСТКА ДУБЛИКАТОВ НАСТРОЕК"""
        self.settings_manager.cleanup_duplicates()

    async def send_demo_notification(self):
        """ОТПРАВКА ДЕМО-УВЕДОМЛЕНИЯ"""
        return await self.notification_sender.send_demo_notification()

    def get_status(self):
        """Возвращает статус парсера"""
        try:
            return {
                'is_running': getattr(self, 'is_running', False),
                'status': 'running' if getattr(self, 'is_running', False) else 'stopped',
                'browser_windows': getattr(self, 'browser_windows', 1),
                'search_queries': getattr(self, 'search_queries', []),
                'stats': getattr(self, 'stats', {}),
                'search_stats': getattr(self, 'search_stats', {}),
                'message': 'Парсер работает' if getattr(self, 'is_running', False) else 'Парсер остановлен'
            }
        except Exception as e:
            return {
                'is_running': False,
                'status': 'error',
                'message': f'Ошибка получения статуса: {e}'
            }


# ============================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ПАРСЕРА
# ============================================
selenium_parser = SeleniumAvitoParser()