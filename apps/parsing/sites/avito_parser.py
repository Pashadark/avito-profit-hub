import re
import time
import logging
from datetime import datetime
from urllib.parse import quote, quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from typing import Dict, Any, List

# Важные импорты для парсинга
from bs4 import BeautifulSoup
import aiohttp

from .base_site_parser import BaseSiteParser
from ..utils.product_validator import ProductValidator
from ..utils.image_processor import ImageProcessor
from ..utils.moscow_metro import MOSCOW_METRO_DATABASE

# ✅ Создаем логгер для парсера Avito
logger = logging.getLogger('parser.avito')

try:
    from apps.parsing.utils.custom_user_agents import apply_user_agent_to_driver

    USER_AGENTS_AVAILABLE = True
except ImportError as e:
    USER_AGENTS_AVAILABLE = False


class AvitoParser(BaseSiteParser):
    """Парсер для Avito.ru с поддержкой городов и совместимостью со старой логикой"""

    def __init__(self, driver, city=None):
        super().__init__(driver)

        # 🔥 ИСПРАВЛЕНИЕ: Используем правильный логгер
        self.logger = logger

        self.validator = ProductValidator()
        self.image_processor = ImageProcessor(driver)

        # 🔥 ИМПОРТИРУЕМ БАЗУ СТАНЦИЙ МЕТРО
        self.metro_database = MOSCOW_METRO_DATABASE

        # 🔥 ИНИЦИАЛИЗИРУЕМ ФЛАГ КАПЧИ
        self._captcha_notification_sent = False

        # 🔥 ИНИЦИАЛИЗИРУЕМ СИСТЕМУ ОБНАРУЖЕНИЯ СВЕЖЕСТИ
        self.freshness_indicators = [
            '[data-marker*="new"]',
            '[class*="fresh"]',
            '[class*="new"]',
            '.iva-item-dateStep-__qB8a',
            '[data-marker="item-date"]',
            '[data-marker*="date"]',
            '.styles_root-_oF2u',
            '[class*="date"]',
            '.styles_remainingTime__P_aaq',
        ]

        # 🔥 ИЗМЕНЕНИЕ: Используем переданный город или Москву по умолчанию
        self.city = city if city else "Москва"
        self.site_name = "avito"
        self.base_url = "https://www.avito.ru"

        self.logger.info(f"🌍 AvitoParser: город {self.city}")
        self.logger.info(f"🌍 Base URL: {self.base_url}")

        # 🔥 ДОБАВИТЬ: Инициализация User-Agent
        if USER_AGENTS_AVAILABLE:
            try:
                user_agent = apply_user_agent_to_driver(driver, getattr(self, 'window_id', 0))
                self.logger.info(f"🌐 AvitoParser инициализирован с User-Agent")
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось инициализировать User-Agent: {e}")

    # 🔥 🔥 🔥 ИСПРАВЛЕНИЕ: Метод build_search_url должен быть таким же как в старом парсере
    def build_search_url(self, query, page=1, **kwargs):
        """Построение URL для поиска на Avito (совместимый со старой версией)"""
        try:
            # Кодируем запрос
            encoded_query = quote_plus(query)

            # Определяем часть URL для города
            if self.city:
                # 🔥 ИСПРАВЛЕНИЕ: Используем глобальный CITY_MAPPING
                try:
                    from apps.parsing.utils.city_translator import CITY_MAPPING
                    city_mapping = CITY_MAPPING
                    city_lower = self.city.strip().lower()

                    if city_lower in city_mapping:
                        city_part = city_mapping[city_lower]
                    else:
                        # Ищем русское название в маппинге
                        found = False
                        for rus_name, eng_name in city_mapping.items():
                            if rus_name.lower() == city_lower:
                                city_part = eng_name
                                found = True
                                break

                        if not found:
                            # Фолбэк: транслитерация
                            import re
                            translit_map = {
                                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
                                'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
                                'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
                                'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
                                'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
                                'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
                                'э': 'e', 'ю': 'yu', 'я': 'ya'
                            }

                            city_translit = ''
                            for char in city_lower:
                                if char in translit_map:
                                    city_translit += translit_map[char]
                                elif char in ' -':
                                    city_translit += '-'
                                else:
                                    city_translit += char

                            city_part = city_translit
                except ImportError:
                    # Локальный маппинг как фолбэк
                    local_mapping = {
                        'москва': 'moskva',
                        'санкт-петербург': 'sankt-peterburg',
                        'новосибирск': 'novosibirsk',
                        'екатеринбург': 'ekaterinburg',
                        'казань': 'kazan',
                        'нижний новгород': 'nizhniy_novgorod',
                        'челябинск': 'chelyabinsk',
                        'самара': 'samara',
                        'омск': 'omsk',
                        'ростов-на-дону': 'rostov-na-donu',
                        'уфа': 'ufa',
                        'красноярск': 'krasnoyarsk',
                        'пермь': 'perm',
                        'воронеж': 'voronezh',
                        'волгоград': 'volgograd',
                        'пенза': 'penza',
                        'сочи': 'sochi'  # 🔥 ДОБАВЛЕНО!
                    }
                    city_lower = self.city.strip().lower()
                    city_part = local_mapping.get(city_lower, 'moskva')
            else:
                city_part = 'moskva'

            # Убираем возможные двойные дефисы
            import re
            city_part = re.sub(r'-+', '-', city_part)

            # Базовый URL
            url = f"{self.base_url}/{city_part}?q={encoded_query}"

            # Добавляем параметры
            params = []

            # Цена (если есть в настройках)
            if hasattr(self, 'min_price') and self.min_price:
                params.append(f"pmin={int(self.min_price)}")
            if hasattr(self, 'max_price') and self.max_price:
                params.append(f"pmax={int(self.max_price)}")

            # Сортировка по дате (свежие) - ТОЧНО КАК В СТАРОМ ПАРСЕРЕ!
            params.append("s=104")

            # Страница
            if page > 1:
                params.append(f"p={page}")

            # Добавляем параметры если есть
            if params:
                url += "&" + "&".join(params)

            self.logger.info(f"🔗 Построен URL: {url}")
            return url

        except Exception as e:
            self.logger.error(f"❌ Ошибка построения URL: {e}")
            # Возвращаем базовый URL в случае ошибки
            return f"{self.base_url}/moskva?q={quote_plus(query)}&s=104"

    async def search_items(self, query, **kwargs):
        """
        Поиск товаров по запросу - СОВМЕСТИМЫЙ СО СТАРОЙ ЛОГИКОЙ!

        🔥 ВАЖНО: Должен возвращать товары с ключом 'name', а не 'title'!
        """
        try:
            self.logger.info(f"🎯 ПОИСК НА AVITO СТАРТ: '{query}'")
            self.logger.info(f"🎯 kwargs: {kwargs}")

            # 🔥 КРИТИЧЕСКАЯ ПРОВЕРКА 1: Драйвер существует
            if not hasattr(self, 'driver') or not self.driver:
                self.logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: драйвер не существует!")
                return []

            self.logger.info(f"🚗 Драйвер доступен: {type(self.driver).__name__}")
            self.logger.info(f"🚗 Текущий URL драйвера ДО: '{self.driver.current_url}'")

            # Строим URL
            url = self.build_search_url(query)
            self.logger.info(f"🔗 Построен URL: {url}")

            # 🔥 ВАЛИДАЦИЯ URL
            if not url or len(url) < 20:
                self.logger.error(f"❌ Некорректный URL: '{url}'")
                return []

            # 🔥 ПРОВЕРКА ДОСТУПА К ИНТЕРНЕТУ
            import socket
            try:
                socket.create_connection(("www.avito.ru", 443), timeout=10)
                self.logger.info("🌐 Интернет соединение: OK")
            except OSError as e:
                self.logger.error(f"🌐 Нет доступа к Avito: {e}")
                return []

            # 🔥 ОТКРЫВАЕМ СТРАНИЦУ
            self.logger.info(f"🌐 Открываем страницу: {url[:100]}...")
            start_time = time.time()

            try:
                self.driver.get(url)
            except Exception as e:
                self.logger.error(f"❌ Ошибка при driver.get(): {e}")
                return []

            load_time = time.time() - start_time
            self.logger.info(f"🌐 Страница загружена за {load_time:.2f} сек")

            # 🔥 ЖДЕМ ЗАГРУЗКИ
            time.sleep(3)

            # 🔥 ПРОВЕРЯЕМ РЕЗУЛЬТАТ
            current_url = self.driver.current_url
            page_title = self.driver.title
            self.logger.info(f"📍 Текущий URL драйвера ПОСЛЕ: '{current_url}'")
            self.logger.info(f"📄 Заголовок страницы: '{page_title}'")

            # 🔥 ПОЛУЧАЕМ HTML
            html = self.driver.page_source
            html_length = len(html)
            self.logger.info(f"📄 Размер HTML: {html_length} символов")

            # 🔥 ПРОВЕРКА РАЗМЕРА HTML
            if html_length < 5000:
                self.logger.error(f"❌ ОШИБКА: Слишком маленький HTML ({html_length} символов)")
                return []

            # 🔥 ПАРСИМ РЕЗУЛЬТАТЫ С ПОМОЩЬЮ СТАРОГО МЕТОДА parse_search_results
            self.logger.info(f"🔍 Начинаем парсинг HTML...")
            items = await self.parse_search_results(query)

            # 🔥 🔥 🔥 ИСПРАВЛЕНИЕ: Конвертируем товары в старый формат!
            converted_items = []
            for item in items:
                # Если товар имеет ключ 'title', конвертируем его в 'name'
                if 'title' in item:
                    converted_item = item.copy()
                    converted_item['name'] = converted_item['title']
                    # Удаляем 'title' чтобы не было конфликта
                    if 'title' in converted_item:
                        del converted_item['title']
                    converted_items.append(converted_item)
                else:
                    # Если уже есть 'name', оставляем как есть
                    converted_items.append(item)

            self.logger.info(f"✅ Найдено {len(converted_items)} товаров для запроса: '{query}'")

            self.logger.info(f"🎯 ПОИСК НА AVITO ЗАВЕРШЕН: '{query}'")
            return converted_items  # 🔥 ВОЗВРАЩАЕМ КОНВЕРТИРОВАННЫЕ ТОВАРЫ!

        except Exception as e:
            self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в search_items: {e}", exc_info=True)
            import traceback
            self.logger.error(f"❌ Трассировка:\n{traceback.format_exc()}")
            return []

    # 🔥 🔥 🔥 СТАРЫЙ МЕТОД parse_search_results (перенесен из старого парсера)
    async def parse_search_results(self, query):
        """Парсит результаты поиска на Avito с приоритетом по точному соответствию в заголовке"""
        try:
            # 🔥 СБРАСЫВАЕМ ФЛАГ КАПЧИ ПРИ НАЧАЛЕ НОВОГО ПАРСИНГА
            self._captcha_notification_sent = False

            # 🔥 ПРОВЕРКА КАПЧИ ТОЛЬКО ЕСЛИ СТРАНИЦА НЕ ЗАГРУЖАЕТСЯ НОРМАЛЬНО
            time.sleep(2)  # Даем странице немного загрузиться

            # Проверяем, есть ли признаки реальной блокировки
            if self._check_real_captcha_block():
                await self._handle_captcha_situation()
                return []

            try:
                self.wait_for_element('[data-marker="item"]', timeout=10)
                self.logger.info("✅ Страница поиска загружена")
            except:
                self.logger.warning("⚠️ Не дождались загрузки товаров, проверяем на блокировку...")

                # 🔥 ПРОВЕРЯЕМ НА РЕАЛЬНУЮ БЛОКИРОВКУ ТОЛЬКО ЕСЛИ ТОВАРЫ НЕ ЗАГРУЗИЛИСЬ
                if self._check_real_captcha_block():
                    await self._handle_captcha_situation()
                    return []
                else:
                    self.logger.info("🔄 Продолжаем без товаров (возможно медленная загрузка)")

            items = await self._find_all_items()

            if not items:
                self.logger.warning("❌ Не найдено товаров на странице")
                # 🔥 НЕ СЧИТАЕМ ЭТО КАПЧЕЙ - ПРОСТО НЕТ ТОВАРОВ
                return []

            self.logger.info(f"🔍 Анализируем {len(items)} товаров по запросу: '{query}'")

            # Разделяем запрос на ключевые слова
            search_keywords = self._parse_search_query(query)
            self.logger.info(f"📝 Ключевые слова для поиска: {search_keywords}")

            products = []
            exact_match_products = []  # Точное соответствие в заголовке
            partial_match_products = []  # Частичное соответствие
            other_products = []  # Остальные товары

            for item in items[:25]:
                try:
                    product = await self.parse_item_advanced(item, query)
                    if product:
                        # Проверяем релевантность товара
                        relevance_type = self._check_relevance(product, search_keywords, query)

                        if relevance_type == "exact":
                            exact_match_products.append(product)
                            self.logger.info(f"🎯 ТОЧНОЕ СООТВЕТСТВИЕ: {product['name']}")
                        elif relevance_type == "partial":
                            partial_match_products.append(product)
                            self.logger.info(f"✅ Частичное соответствие: {product['name']}")
                        else:
                            other_products.append(product)

                except Exception as e:
                    continue

            # 🔥 ВРЕМЕННО ОТКЛЮЧАЕМ СТРОГУЮ ФИЛЬТРАЦИЮ - БЕРЕМ ВСЕ ТОВАРЫ
            final_products = []

            # Берем ВСЕ точные соответствия
            if exact_match_products:
                final_products.extend(exact_match_products)
                self.logger.info(f"✅ Добавлено {len(exact_match_products)} товаров с точным соответствием")

            # Берем ВСЕ частичные соответствия
            if partial_match_products:
                final_products.extend(partial_match_products)
                self.logger.info(f"✅ Добавлено {len(partial_match_products)} товаров с частичным соответствием")

            # Берем ВСЕ остальные товары
            if other_products:
                final_products.extend(other_products)
                self.logger.info(f"✅ Добавлено {len(other_products)} других товаров")

            # Ограничиваем общее количество для производительности
            if len(final_products) > 20:
                final_products = final_products[:20]
                self.logger.info(f"📊 Ограничили до {len(final_products)} товаров для обработки")

            # Фильтруем только хорошие сделки
            good_deals = []
            for product in final_products:
                if await self.validator.is_good_deal(product):
                    good_deals.append(product)
                else:
                    self.logger.info(f"❌ Отфильтрован неподходящий товар: {product['name']} - {product['price']}₽")

            self.logger.info(f"🎯 Итоговый результат: {len(good_deals)} хороших сделок")
            return good_deals

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга: {e}")
            return []

    def _check_real_captcha_block(self):
        """Проверяет только РЕАЛЬНЫЕ случаи блокировки, а не фоновую reCAPTCHA"""
        try:
            page_title = self.driver.title.lower()
            page_url = self.driver.current_url

            self.logger.info(f"🔍 Проверка на реальную блокировки. Заголовок: {page_title}")

            # 🔥 ТОЛЬКО ЯВНЫЕ ПРИЗНАКИ БЛОКИРОВКИ
            blocking_indicators = [
                "подозрительная активность",
                "проблемы с ip",
                "доступ ограничен",
                "автоматические запросы",
                "вы робот",
                "подтвердите что вы не робот"
            ]

            # Проверяем только в заголовке (не во всей странице)
            for indicator in blocking_indicators:
                if indicator in page_title:
                    self.logger.warning(f"🚨 РЕАЛЬНАЯ блокировка: '{indicator}'")
                    return True

            # Проверяем URL на явные признаки блокировки
            if "blocked" in page_url or "robot" in page_url:
                self.logger.warning(f"🚨 URL указывает на блокировку: {page_url}")
                return True

            # 🔥 Проверяем наличие ВИДИМОЙ формы капчи (не скрытой reCAPTCHA)
            try:
                # Элементы, которые явно показывают капчу пользователю
                visible_captcha_elements = [
                    'div[class*="captcha"][style*="visible"]',
                    '.captcha-form',
                    '#captcha-container',
                    'form[action*="captcha"]'
                ]

                for selector in visible_captcha_elements:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.size['height'] > 50:  # Достаточно большой чтобы быть видимым
                            self.logger.warning(f"🚨 Обнаружена ВИДИМАЯ капча: {selector}")
                            return True
            except:
                pass

            # 🔥 Если страница содержит нормальный контент Avito - блокировки нет
            if any(indicator in page_title for indicator in ["avito", "авито", "объявления", "купить", "продать"]):
                self.logger.debug("✅ Страница нормальная, блокировки нет")
                return False

            # 🔥 Если не можем определить - считаем что блокировки нет
            self.logger.info("⚠️ Неясная ситуация, но продолжаем работу")
            return False

        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки блокировки: {e}")
            return False

    async def _handle_captcha_situation(self):
        """Обрабатывает ситуацию с капчей - отправляет уведомление только один раз"""
        try:
            # 🔥 ПРОВЕРЯЕМ, НЕ ОТПРАВЛЯЛИ ЛИ МЫ УЖЕ УВЕДОМЛЕНИЕ
            if hasattr(self, '_captcha_notification_sent') and self._captcha_notification_sent:
                self.logger.info("⚠️ Уведомление о капче уже отправлено, пропускаем")
                return True

            self.logger.error("🚨 ПАРСЕР ОСТАНОВЛЕН! ОБНАРУЖЕНА КАПЧА ИЛИ БЛОКИРОВКА!")

            # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ В ТЕЛЕГРАМ (только один раз)
            await self._send_captcha_notification()

            # 🔥 ПОМЕЧАЕМ, ЧТО УВЕДОМЛЕНИЕ ОТПРАВЛЕНО
            self._captcha_notification_sent = True

            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки капчи: {e}")
            return False

    async def _send_captcha_notification(self):
        """Отправляет уведомление о капче в Telegram"""
        try:
            from telegram import Bot
            from shared.utils.config import get_bot_token, get_chat_id

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                self.logger.error("❌ Не удалось отправить уведомление о капче: нет токена или chat_id")
                return False

            bot = Bot(token=token)

            message = (
                "🚨 <b>ПАРСЕР ОСТАНОВЛЕН!</b>\n\n"
                "Обнаружена капча или блокировка по IP!\n\n"
                "📝 <b>Что произошло:</b>\n"
                "• Avito заподозрил автоматические запросы\n"
                "• Требуется подтверждение, что вы не робот\n"
                "• Парсер временно приостановлен\n\n"
                "⚡ <b>Что делать:</b>\n"
                "1. Откройте браузер с Avito\n"
                "2. Решите капчу вручную\n"
                "3. Дождитесь разблокировки\n"
                "4. Перезапустите парсер\n\n"
                "⏰ <b>Статус:</b> Ожидание действий пользователя"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )

            self.logger.info("✅ Уведомление о капче отправлено в Telegram")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления о капчи: {e}")
            return False

    async def _find_all_items(self):
        """Находит все товары на странице с разными селекторами"""
        items = []
        selectors = [
            '[data-marker="item"]',
            '.iva-item-root-_lk9K',
            '.items-items-kAJAg',
            '.item',
            '.js-item'
        ]

        for selector in selectors:
            try:
                found_items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if found_items:
                    items = found_items
                    self.logger.info(f"✅ Найдено элементов с '{selector}': {len(items)}")
                    break
            except:
                continue
        return items

    def _parse_search_query(self, query):
        """Парсит поисковый запрос на ключевые слова"""
        cleaned_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = cleaned_query.split()

        stop_words = {'для', 'от', 'в', 'на', 'с', 'по', 'из', 'у', 'о', 'об', 'бу', 'б/у'}

        keywords = []
        for word in words:
            cleaned_word = word.strip()
            if (cleaned_word and
                    cleaned_word not in stop_words and
                    len(cleaned_word) > 1):
                keywords.append(cleaned_word)

        if not keywords:
            keywords = [word for word in words if len(word) > 1]

        return keywords

    def _check_relevance(self, product, search_keywords, original_query):
        """Проверяет релевантность товара поисковому запросу"""
        # 🔥 ИСПРАВЛЕНИЕ: Используем 'name' который мы гарантированно имеем
        title = product['name'].lower()
        original_query_lower = original_query.lower()

        if original_query_lower in title:
            return "exact"

        all_keywords_in_title = all(keyword in title for keyword in search_keywords)
        if all_keywords_in_title and len(search_keywords) > 0:
            return "exact"

        if search_keywords:
            matched_keywords = sum(1 for keyword in search_keywords if keyword in title)
            match_percentage = matched_keywords / len(search_keywords)
            if match_percentage >= 0.5:
                return "partial"

        if any(keyword in title for keyword in search_keywords):
            return "partial"

        return "other"

    async def parse_item_advanced(self, item, category):
        """Парсит товар с улучшенной проверкой данных - СТАРАЯ ЛОГИКА!"""
        try:
            title = self._extract_title(item)
            if not title:
                return None

            price = self._extract_price(item)
            if price <= 0:
                return None

            # 🔥 ИЗМЕНЕНИЕ: Теперь получаем и ссылку и ID
            link, item_id = self._extract_link_and_id(item)
            if not link:
                return None

            target_price = self._calculate_target_price(price)

            # 🔥 ДОБАВЛЯЕМ АНАЛИЗ СВЕЖЕСТИ
            time_listed = self._parse_time_listed(item)
            freshness_score = await self.analyze_listing_freshness(item, {
                'name': title,
                'price': price,
                'time_listed': time_listed
            })

            # 🔥 🔥 🔥 ВАЖНО: Возвращаем с ключом 'name', а не 'title'!
            return {
                'name': title[:200],  # ← КЛЮЧ 'name' ДЛЯ СОВМЕСТИМОСТИ!
                'price': price,
                'target_price': target_price,
                'url': link,
                'item_id': item_id,
                'product_id': item_id,
                'category': category,
                'description': f"Найден по запросу: '{category}'",
                'time_listed': time_listed,
                'freshness_score': freshness_score,
                'is_fresh_by_indicators': self._detect_fresh_listing_indicators(item),
                'site': 'avito',  # 🔥 ДОБАВЛЯЕМ САЙТ
                'city': self.city  # 🔥 ДОБАВЛЯЕМ ГОРОД
            }

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга товара: {e}")
            return None

    def _extract_title(self, item):
        """Извлекает заголовок товара"""
        title_selectors = [
            '[data-marker="item-title"]',
            '.iva-item-titleStep-_CxvN',
            '.title-root-zZCwT',
            'h3',
            '[itemprop="name"]',
            'a[data-marker="item-title"]',
            '.iva-item-title-py3i_'
        ]

        for selector in title_selectors:
            try:
                title_elem = item.find_element(By.CSS_SELECTOR, selector)
                title = title_elem.text.strip()
                if title and len(title) > 3:
                    return title
            except:
                continue
        return None

    def _extract_price(self, item):
        """Извлекает цену товара"""
        price_selectors = [
            '[data-marker="item-price"]',
            '.price-price-_P9LN',
            '.iva-item-priceStep-U3B7L',
            '[itemprop="price"]',
            '.price-text-_YGDY',
            'span[data-marker="item-price"]',
            '.iva-item-price-py3i_'
        ]

        for selector in price_selectors:
            try:
                price_elem = item.find_element(By.CSS_SELECTOR, selector)
                price_text = price_elem.text.replace('₽', '').replace(' ', '').strip()
                price = self.parse_price(price_text)
                if price > 0:
                    return price
            except:
                continue
        return 0

    def _extract_link_and_id(self, item):
        """Извлекает ссылку на товар и ID товара"""
        link_selectors = [
            '[data-marker="item-title"]',
            'a[href*="/moskva/"]',
            '.iva-item-titleStep-_CxvN a',
            'a.link-link',
            'a[data-marker="item-title"]',
            '.iva-item-title-py3i_ a'
        ]

        for selector in link_selectors:
            try:
                link_elem = item.find_element(By.CSS_SELECTOR, selector)
                link = link_elem.get_attribute('href')
                if link and 'avito.ru' in link:
                    # 🔥 ИЗВЛЕКАЕМ ID ТОВАРА ИЗ URL
                    item_id = self._extract_item_id_from_url(link)
                    self.logger.info(f"✅ Ссылка и ID извлечены: {link} -> ID: {item_id}")
                    return link, item_id
            except Exception as e:
                self.logger.debug(f"❌ Ошибка извлечения ссылки с селектором {selector}: {e}")
                continue

        self.logger.warning("❌ Не удалось извлечь ссылку и ID товара")
        return None, None

    def _extract_item_id_from_url(self, url):
        """Извлекает ID товара из URL Avito"""
        try:
            # Паттерны для разных форматов URL Avito
            patterns = [
                r'avito\.ru/.+/(\d+)$',  # /category/ID
                r'avito\.ru/.+/.+_(\d+)$',  # /category/item_NAME_ID
                r'avito\.ru/items/(\d+)$',  # /items/ID (как в твоем примере)
                r'/(\d+)(?:\?|$)',  # /ID? или /ID
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    item_id = match.group(1)
                    if item_id.isdigit():
                        self.logger.info(f"✅ ID товара извлечен из URL: {item_id}")
                        return int(item_id)

            self.logger.warning(f"❌ Не удалось извлечь ID из URL: {url}")
            return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения ID из URL: {e}")
            return None

    def _calculate_target_price(self, price):
        """Простой расчет целевой цены (БЕЗ НАЦЕНКИ)"""
        return price

    def _detect_fresh_listing_indicators(self, item_element):
        """🎯 Обнаруживает признаки свежего объявления"""
        try:
            self.logger.debug("🔍 Поиск признаков свежести объявления...")

            for indicator in self.freshness_indicators:
                try:
                    elements = item_element.find_elements(By.CSS_SELECTOR, indicator)
                    if elements:
                        element_text = elements[0].text.lower() if elements[0].text else ""
                        self.logger.debug(f"✅ Найден индикатор свежести: {indicator} - текст: {element_text}")
                        return True
                except Exception as e:
                    self.logger.debug(f"⚠️ Ошибка проверки индикатора {indicator}: {e}")
                    continue

            # 🔥 ТЕКСТОВЫЙ АНАЛИЗ
            try:
                item_text = item_element.text.lower()
                freshness_keywords = [
                    'только что', 'только что', 'сегодня', 'минут', 'час',
                    'только добавлен', 'свежий', 'новый', 'срочно', 'новинка'
                ]

                for keyword in freshness_keywords:
                    if keyword in item_text:
                        self.logger.debug(f"✅ Найден текстовый индикатор свежести: '{keyword}'")
                        return True
            except Exception as e:
                self.logger.debug(f"⚠️ Ошибка текстового анализа: {e}")

            return False

        except Exception as e:
            self.logger.debug(f"⚠️ Ошибка обнаружения свежести: {e}")
            return False

    def _parse_time_listed(self, item_element):
        """🕒 Парсит время публикации с улучшенной логикой"""
        try:
            self.logger.debug("⏰ Парсинг времени публикации...")

            # СЕЛЕКТОРЫ ВРЕМЕНИ AVITO
            time_selectors = [
                '[data-marker="item-date"]',
                '.iva-item-dateStep-__qB8a',
                '.date-text-2t4QT',
                '.styles_remainingTime__P_aaq',
                '.styles_root-_oF2u',
                '[class*="date"]',
                '.styles_text-_oF2u'
            ]

            for selector in time_selectors:
                try:
                    time_elements = item_element.find_elements(By.CSS_SELECTOR, selector)
                    if time_elements:
                        time_text = time_elements[0].text.lower().strip()
                        self.logger.debug(f"📅 Найден текст времени: '{time_text}'")

                        if not time_text:
                            continue

                        # 🔥 ПАРСИМ ВРЕМЯ С ПРИОРИТЕТОМ СВЕЖЕСТИ
                        time_listed = self._parse_time_text(time_text)
                        if time_listed is not None:
                            self.logger.debug(f"✅ Время распознано: {time_listed} часов")
                            return time_listed

                except Exception as e:
                    self.logger.debug(f"⚠️ Ошибка парсинга селектора {selector}: {e}")
                    continue

            self.logger.debug("⏰ Время не распознано, используем значение по умолчанию")
            return 24.0

        except Exception as e:
            self.logger.debug(f"⚠️ Ошибка парсинга времени: {e}")
            return 24.0

    def _parse_time_text(self, time_text):
        """🕐 Парсит текстовое представление времени"""
        try:
            # 🚨 ТОЛЬКО ЧТО / МИНУТЫ
            if 'только что' in time_text:
                return 0.1

            elif 'минут' in time_text:
                minutes_match = re.search(r'(\d+)\s*минут', time_text)
                if minutes_match:
                    minutes = int(minutes_match.group(1))
                    return max(minutes / 60.0, 0.1)
                return 0.5

            # 🔥 ЧАСЫ
            elif 'час' in time_text:
                hours_match = re.search(r'(\d+)\s*час', time_text)
                if hours_match:
                    return float(hours_match.group(1))

                if any(phrase in time_text for phrase in ['час назад', 'часа назад']):
                    return 1.0
                return 1.0

            # 📅 СЕГОДНЯ
            elif 'сегодня' in time_text:
                time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
                if time_match:
                    hour = int(time_match.group(1))
                    current_hour = datetime.now().hour
                    hours_ago = current_hour - hour
                    if hours_ago < 0:
                        hours_ago += 24
                    return max(hours_ago, 1.0)
                return 6.0

            # 📆 ВЧЕРА
            elif 'вчера' in time_text:
                time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
                if time_match:
                    hour = int(time_match.group(1))
                    return 24.0 + (datetime.now().hour - hour)
                return 24.0

            # 📅 ДНИ
            elif 'день' in time_text or 'дн' in time_text:
                days_match = re.search(r'(\d+)\s*(день|дн|дня)', time_text)
                if days_match:
                    days = int(days_match.group(1))
                    return days * 24.0
                return 24.0

            # 🗓️ НЕДЕЛИ
            elif 'недел' in time_text:
                weeks_match = re.search(r'(\d+)\s*недел', time_text)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    return weeks * 24.0 * 7
                return 24.0 * 7

            else:
                numbers_match = re.search(r'(\d+)', time_text)
                if numbers_match:
                    number = int(numbers_match.group(1))
                    if number < 24:
                        return float(number)
                    elif number < 100:
                        return number * 24.0

                self.logger.debug(f"❓ Неизвестный формат времени: '{time_text}'")
                return 48.0

        except Exception as e:
            self.logger.debug(f"⚠️ Ошибка парсинга текста времени '{time_text}': {e}")
            return 24.0

    async def analyze_listing_freshness(self, item_element, product_data):
        """🎯 Анализирует свежесть объявления"""
        try:
            # 🔥 ПРОВЕРЯЕМ ПРИЗНАКИ СВЕЖЕСТИ
            is_fresh_by_indicators = self._detect_fresh_listing_indicators(item_element)

            # 🔥 ПАРСИМ ВРЕМЯ
            time_listed = product_data.get('time_listed', 24)

            # 🔥 ИЗВЛЕКАЕМ ПРИЗНАКИ ДЛЯ ML
            freshness_features = self._extract_freshness_features(item_element, product_data)
            product_data['freshness_features'] = freshness_features

            # 🔥 РАСЧЕТ SCORE СВЕЖЕСТИ
            freshness_score = self._calculate_freshness_score(time_listed, is_fresh_by_indicators, freshness_features)
            product_data['freshness_score'] = freshness_score

            self.logger.info(
                f"🎯 Анализ свежести: {freshness_score:.2f} (время: {time_listed}ч, индикаторы: {is_fresh_by_indicators})")

            return freshness_score

        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа свежести: {e}")
            product_data['freshness_score'] = 0.3
            return 0.3

    def _extract_freshness_features(self, item_element, product_data):
        """🔍 Извлекает признаки свежести для ML"""
        try:
            features = {}

            # 🔥 ВРЕМЕННЫЕ ПРИЗНАКИ
            time_listed = product_data.get('time_listed', 24)
            features['time_listed_hours'] = time_listed
            features['is_very_fresh'] = 1.0 if time_listed <= 2 else 0.0
            features['is_fresh'] = 1.0 if time_listed <= 6 else 0.0
            features['is_old'] = 1.0 if time_listed > 24 else 0.0

            # 🔥 ТЕКСТОВЫЕ ПРИЗНАКИ
            try:
                item_text = item_element.text.lower()
                freshness_keywords = {
                    'keyword_tolko_chto': 'только что',
                    'keyword_segodnya': 'сегодня',
                    'keyword_minut': 'минут',
                    'keyword_chas': 'час',
                    'keyword_svejiy': 'свежий',
                    'keyword_noviy': 'новый',
                    'keyword_srochno': 'срочно'
                }

                for feature_name, keyword in freshness_keywords.items():
                    features[feature_name] = 1.0 if keyword in item_text else 0.0

            except Exception as e:
                self.logger.debug(f"⚠️ Ошибка извлечения текстовых признаков: {e}")

            # 🔥 ВИЗУАЛЬНЫЕ ПРИЗНАКИ
            features['has_fresh_badge'] = 1.0 if self._detect_fresh_listing_indicators(item_element) else 0.0

            # 🔥 СТИЛЕВЫЕ ПРИЗНАКИ
            try:
                special_classes = ['new', 'fresh', 'highlight', 'promoted']
                for css_class in special_classes:
                    try:
                        elements = item_element.find_elements(By.CSS_SELECTOR, f'[class*="{css_class}"]')
                        features[f'css_{css_class}'] = 1.0 if elements else 0.0
                    except:
                        features[f'css_{css_class}'] = 0.0
            except Exception as e:
                self.logger.debug(f"⚠️ Ошибка проверки стилей: {e}")

            self.logger.debug(f"🔍 Извлечены признаки свежести: {features}")
            return features

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения признаков свежести: {e}")
            return {}

    def _calculate_freshness_score(self, time_listed, has_indicators, features):
        """📊 Расчет score свежести"""
        try:
            base_score = 0.0

            # 🔥 ОСНОВНОЙ ВЕС - ВРЕМЯ
            if time_listed <= 0.5:
                base_score = 0.95
            elif time_listed <= 2:
                base_score = 0.85
            elif time_listed <= 6:
                base_score = 0.70
            elif time_listed <= 24:
                base_score = 0.40
            else:
                base_score = 0.10

            # 🔥 БОНУС ЗА ВИЗУАЛЬНЫЕ ПРИЗНАКИ
            if has_indicators:
                base_score += 0.15

            # 🔥 БОНУС ЗА ТЕКСТОВЫЕ ПРИЗНАКИ
            text_bonus = sum([
                features.get('keyword_tolko_chto', 0) * 0.1,
                features.get('keyword_segodnya', 0) * 0.08,
                features.get('keyword_srochno', 0) * 0.07,
                features.get('keyword_noviy', 0) * 0.05
            ])
            base_score += text_bonus

            return min(max(base_score, 0.0), 1.0)

        except Exception as e:
            self.logger.debug(f"⚠️ Ошибка расчета score свежести: {e}")
            return 0.5

    async def get_freshness_analysis_report(self, item_element, product_data):
        """📊 Полный отчет по свежести объявления"""
        try:
            report = {
                'time_listed_hours': product_data.get('time_listed', 24),
                'has_fresh_indicators': self._detect_fresh_listing_indicators(item_element),
                'freshness_features': self._extract_freshness_features(item_element, product_data),
                'calculated_score': 0.0,
                'freshness_category': 'unknown'
            }

            # 🔥 РАСЧЕТ ФИНАЛЬНОГО SCORE
            freshness_score = await self.analyze_listing_freshness(item_element, product_data)
            report['calculated_score'] = freshness_score

            # 🔥 КАТЕГОРИЯ СВЕЖЕСТИ
            if freshness_score >= 0.8:
                report['freshness_category'] = 'critical_fresh'
            elif freshness_score >= 0.6:
                report['freshness_category'] = 'very_fresh'
            elif freshness_score >= 0.4:
                report['freshness_category'] = 'fresh'
            elif freshness_score >= 0.2:
                report['freshness_category'] = 'average'
            else:
                report['freshness_category'] = 'old'

            self.logger.info(f"📊 Отчет свежести: {report['freshness_category']} (score: {freshness_score:.2f})")
            return report

        except Exception as e:
            self.logger.error(f"❌ Ошибка создания отчета свежести: {e}")
            return {
                'time_listed_hours': 24,
                'has_fresh_indicators': False,
                'freshness_features': {},
                'calculated_score': 0.3,
                'freshness_category': 'error'
            }

    async def get_product_details(self, product):
        """Основной метод получения детальной информации о товаре"""
        try:
            if not product.get('url'):
                return product

            # 🔥 ИЗМЕНЕНИЕ: Извлекаем ID товара из URL если его еще нет
            if not product.get('item_id') or not product.get('product_id'):
                item_id = self._extract_item_id_from_url(product['url'])
                if item_id:
                    product['item_id'] = item_id
                    product['product_id'] = item_id
                    self.logger.info(f"✅ ID товара извлечен из URL: {item_id}")

            self.logger.info(f"🔍 Получаем детали товара ID {product.get('product_id')}: {product['url']}")
            self.driver.get(product['url'])

            # 🔥 ПРОВЕРКА КАПЧИ
            if self._check_captcha_page():
                await self._handle_captcha_situation()
                return product

            try:
                self.wait_for_element('[data-marker="item-view"]')
                self.logger.info("✅ Страница товара загружена")
            except:
                self.logger.warning("⚠️ Не дождались полной загрузки страницы товара")

            # 🔥 ПАРСИМ ТОЛЬКО СОСТОЯНИЕ
            condition = self._extract_condition()

            # 🔥 ПАРСИМ ЦВЕТ
            color = self._extract_color_from_details()

            # 🔥 УЛУЧШЕННЫЙ ПОИСК МЕТРО И АДРЕСА
            location_data = self._extract_location_details_improved()

            # 🔥 ИЗВЛЕКАЕМ ИНФОРМАЦИЮ О ПРОДАВЦЕ С АВАТАРКОЙ И ССЫЛКОЙ НА ПРОФИЛЬ
            seller_info = await self._extract_seller_info_with_avatar()

            # 🔥🔥🔥 ВОТ ЭТА СТРОКА ТЕПЕРЬ БУДЕТ ПАРСИТЬ БОЛЬШИЕ ФОТО!
            image_urls = self.image_processor.get_avito_images()
            main_image_url = image_urls[0] if image_urls else None

            # Подготавливаем изображение для Telegram
            image_data = None
            if main_image_url:
                try:
                    image_data = self.image_processor.download_image_to_base64(main_image_url)
                    self.logger.info("✅ Изображение подготовлено для Telegram")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка подготовки изображения: {e}")

            # 🔥🔥🔥 ИЗВЛЕКАЕМ ПОЛНОЕ ОПИСАНИЕ С СОХРАНЕНИЕМ ФОРМАТИРОВАНИЯ
            description = self._extract_description()

            # Извлекаем дополнительную информацию
            try:
                seller_name = seller_info.get('seller_name') or self._extract_seller_name()
                seller_rating, reviews_count = self._extract_seller_rating()
                avito_category = self._extract_category()
                city = self._extract_city()
                posted_date = self.extract_posted_date()

                # 🔥 ИСПРАВЛЕНИЕ: Получаем оба значения просмотров
                views_data = self._extract_views_count()
                views_count = views_data.get('total_views', 0)
                views_today = views_data.get('today_views', 0)

                metro_stations_data = location_data['metro_stations']

                # 🔥 ОБНОВЛЯЕМ ПРОДУКТ С ПОЛНЫМ ОПИСАНИЕМ И ОБОИМИ ПОЛЯМИ ПРОСМОТРОВ
                product.update({
                    'description': description,
                    'seller_name': seller_name or 'Не указан',
                    'seller_rating': seller_rating,
                    'reviews_count': reviews_count or 0,
                    'avito_category': avito_category or product.get('category', 'Не указана'),
                    'city': city or 'Москва',
                    'image_url': main_image_url,
                    'image_urls': image_urls,
                    'image_data': image_data,
                    'posted_date': posted_date or 'Дата не указана',
                    'views_count': views_count,
                    'views_today': views_today,
                    'parsed_at': time.time(),
                    'metro_stations': metro_stations_data,
                    'address': location_data['address'],
                    'full_location': location_data['full_location'],
                    'color': color,
                    'condition': condition,
                    'seller_avatar': seller_info.get('seller_avatar'),
                    'seller_type': seller_info.get('seller_type', 'Не указан'),
                    'seller_profile_url': seller_info.get('seller_profile_url'),
                    'item_id': product.get('item_id'),
                    'product_id': product.get('product_id')
                })

                self.logger.info(f"✅ Детали товара получены!:")
                self.logger.info(f"├──🆔 ID товара: {product.get('product_id')}")
                self.logger.info(f"├──📝 Описание: {len(description)} символов")
                self.logger.info(f"├──📦 Продавец: {seller_name}")
                self.logger.info(f"├──⭐ Рейтинг: {seller_rating}")
                self.logger.info(f"├──👁 Просмотры: {views_count} (сегодня: {views_today})")
                self.logger.info(f"├──🎨 Цвет: {color}")
                self.logger.info(f"├──🔧 Состояние: {condition}")
                self.logger.info(f"├──🏙️ Город: '{city}'")

            except Exception as e:
                self.logger.error(f"❌ Ошибка получения деталей: {e}")

            return product

        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки страницы товара: {e}")
            return product

    def _check_captcha_page(self):
        """УМНАЯ проверка капчи - только реальные случаи блокировки"""
        try:
            page_title = self.driver.title.lower()
            page_url = self.driver.current_url.lower()

            self.logger.info(f"🔍 Проверка капчи. Заголовок: {page_title}")

            critical_indicators = [
                "подозрительная активность",
                "проблемы с ip",
                "доступ ограничен",
                "автоматические запросы",
                "вы робот",
                "подтвердите что вы не робот",
                "капча"
            ]

            for indicator in critical_indicators:
                if indicator in page_title:
                    self.logger.warning(f"🚨 КРИТИЧЕСКИЙ индикатор капчи в заголовке: '{indicator}'")
                    return True

            if "blocked" in page_url or "captcha" in page_url or "robot" in page_url:
                self.logger.warning(f"🚨 URL указывает на блокировки: {page_url}")
                return True

            visible_captcha_selectors = [
                'div[class*="captcha"]:visible',
                '.captcha-container',
                '#captcha',
                'form[action*="captcha"]'
            ]

            for selector in visible_captcha_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            self.logger.warning(f"🚨 Обнаружена ВИДИМАЯ капча: {selector}")
                            return True
                except:
                    continue

            normal_indicators = [
                "avito",
                "авито",
                "объявления",
                "товары",
                "поиск",
                "купить",
                "продать"
            ]

            normal_indicators_count = sum(1 for indicator in normal_indicators if indicator in page_title)
            if normal_indicators_count >= 1:
                self.logger.debug("✅ Страница нормально загружена, капчи нет")
                return False

            try:
                items = self.driver.find_elements(By.CSS_SELECTOR, '[data-marker="item"]')
                if items:
                    self.logger.debug("✅ На странице есть товары, капчи нет")
                    return False
            except:
                pass

            self.logger.info("⚠️ Неясная ситуация, но считаем что капчи нет для продолжения работы")
            return False

        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки капчи: {e}")
            return False

    def _extract_color_from_details(self):
        """Парсит цвет из характеристик товара на странице Avito"""
        try:
            self.logger.info("🎨 Поиск цвета в характеристиках товара...")

            params_selectors = [
                '[data-marker="item-view/item-params"]',
                '#bx_item-params',
                '[data-marker="item-params"]',
                '[class*="params-params"]',
                '[class*="item-params"]',
                '.params__paramsList___XzY3MG',
                '.params__paramsList__item___XzY3MG',
                '[class*="params__paramsList"]'
            ]

            for selector in params_selectors:
                try:
                    params_blocks = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🎨 Проверяем селектор '{selector}': найдено {len(params_blocks)} блоков")

                    for block in params_blocks:
                        try:
                            color = self._find_color_in_params_block(block)
                            if color and color != "Разноцветный":
                                self.logger.info(f"✅ Цвет найден в блоке: '{color}'")
                                return color

                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка анализа блока: {e}")
                            continue

                except Exception as e:
                    self.logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            try:
                self.logger.info("🔍 Поиск цвета по элементам с текстом 'Цвет'...")
                color_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Цвет')]")
                self.logger.info(f"🔍 Найдено элементов с 'Цвет': {len(color_elements)}")

                for color_elem in color_elements:
                    try:
                        elem_text = color_elem.text.strip()
                        self.logger.info(f"🔍 Текст элемента с цветом: '{elem_text}'")

                        if 'Цвет' in elem_text:
                            separators = [':', ' ']

                            for separator in separators:
                                if f'Цвет{separator}' in elem_text:
                                    parts = elem_text.split(f'Цвет{separator}')
                                    if len(parts) > 1:
                                        color_value = parts[1].strip()
                                        if color_value:
                                            normalized_color = self._normalize_color_name(color_value)
                                            self.logger.info(
                                                f"✅ Цвет найден через '{separator}': '{color_value}' -> '{normalized_color}'")
                                            return normalized_color

                            if 'Цвет' in elem_text and not any(sep in elem_text for sep in [':', ' ']):
                                color_value = elem_text.replace('Цвет', '').strip()
                                if color_value:
                                    normalized_color = self._normalize_color_name(color_value)
                                    self.logger.info(
                                        f"✅ Цвет найден (без разделителя): '{color_value}' -> '{normalized_color}'")
                                    return normalized_color

                    except Exception as e:
                        self.logger.debug(f"❌ Ошибка извлечения цвета из элемента: {e}")
                        continue

            except Exception as e:
                self.logger.debug(f"❌ Поиск по элементам 'Цвет' не сработал: {e}")

            try:
                self.logger.info("🔍 Поиск цвета в описании товара...")
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-marker="item-view/item-description"]')
                description = desc_elem.text.lower()

                color_patterns = [
                    r'цвет[:\s]*([^\n\r.,!?]+)',
                    r'цвет[а]?[:\s]*([^\n\r.,!?]+)',
                    r'colou?r[:\s]*([^\n\r.,!?]+)'
                ]

                for pattern in color_patterns:
                    color_matches = re.findall(pattern, description)
                    if color_matches:
                        color_value = color_matches[0].strip()
                        if color_value:
                            normalized_color = self._normalize_color_name(color_value)
                            self.logger.info(f"✅ Цвет найден в описании: '{color_value}' -> '{normalized_color}'")
                            return normalized_color
            except Exception as e:
                self.logger.debug(f"❌ Поиск в описании не сработал: {e}")

            self.logger.info("🎨 Цвет не найден в характеристиках")
            return "Разноцветный"

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга цвета: {e}")
            return "Разноцветный"

    def _find_color_in_params_block(self, block):
        """Ищет параметр 'Цвет' в блоке характеристик"""
        try:
            item_elements = block.find_elements(By.CSS_SELECTOR, '.params__paramsList__item___XzY3MG')
            self.logger.info(f"🎨 Найдено элементов характеристик: {len(item_elements)}")

            for item in item_elements:
                try:
                    item_text = item.text.strip()
                    self.logger.info(f"🎨 Текст элемента характеристик: '{item_text}'")

                    if 'Цвет' in item_text:
                        separators = [':', ' ']

                        for separator in separators:
                            if f'Цвет{separator}' in item_text:
                                parts = item_text.split(f'Цвет{separator}')
                                if len(parts) > 1:
                                    value = parts[1].strip()
                                    if value:
                                        self.logger.info(f"✅ Цвет найден через '{separator}': '{value}'")
                                        return value

                        if 'Цвет' in item_text and not any(sep in item_text for sep in [':', ' ']):
                            value = item_text.replace('Цвет', '').strip()
                            if value:
                                self.logger.info(f"✅ Цвет найден (без разделителя): '{value}'")
                                return value

                except Exception as e:
                    self.logger.debug(f"❌ Ошибка анализа элемента цвета: {e}")
                    continue

            return None

        except Exception as e:
            self.logger.debug(f"❌ Ошибка поиска цвета в блоке: {e}")
            return None

    def _normalize_color_name(self, color_text):
        """Нормализует название цвета с учетом русского языка"""
        if not color_text:
            return "Разноцветный"

        color_text = color_text.strip()

        color_mapping = {
            'черный': 'Черный',
            'чёрный': 'Черный',
            'белый': 'Белый',
            'красный': 'Красный',
            'синий': 'Синий',
            'зеленый': 'Зеленый',
            'зелёный': 'Зеленый',
            'желтый': 'Желтый',
            'жёлтый': 'Желтый',
            'оранжевый': 'Оранжевый',
            'фиолетовый': 'Фиолетовый',
            'розовый': 'Розовый',
            'коричневый': 'Коричневый',
            'серый': 'Серый',
            'голубой': 'Голубой',
            'бирюзовый': 'Бирюзовый',
            'бежевый': 'Бежевый',
            'бордовый': 'Бордовый',
            'салатовый': 'Зеленый',
            'изумрудный': 'Зеленый',
            'вишневый': 'Красный',
            'вишнёвый': 'Красный',
            'малиновый': 'Розовый',
            'лиловый': 'Фиолетовый',
            'сиреневый': 'Фиолетовый',
            'хаки': 'Зеленый',
            'золотой': 'Золотой',
            'серебряный': 'Серебряный',
            'серебристый': 'Серебряный',
            'темно-синий': 'Синий',
            'тёмно-синий': 'Синий',
            'светло-синий': 'Голубой',
            'темно-зеленый': 'Зеленый',
            'тёмно-зелёный': 'Зеленый',
            'светло-зеленый': 'Зеленый',
            'светло-зелёный': 'Зеленый',
            'темно-серый': 'Серый',
            'тёмно-серый': 'Серый',
            'светло-серый': 'Серый',
            'фиолетовый': 'Фиолетовый',
            'коричневый': 'Коричневый'
        }

        color_lower = color_text.lower()

        if color_lower in color_mapping:
            return color_mapping[color_lower]

        for key, value in color_mapping.items():
            if key in color_lower:
                return value

        if color_text and len(color_text) < 30 and not any(
                word in color_lower for word in ['размер', 'состояние', 'бренд', 'материал']):
            return color_text.capitalize()

        return "Разноцветный"

    def _extract_location_details_improved(self):
        """УЛУЧШЕННЫЙ метод извлечения деталей местоположения"""
        try:
            self.logger.info("🔍 УЛУЧШЕННЫЙ поиск данных о местоположении...")

            location_data = {
                'metro_stations': [],
                'address': None,
                'full_location': None
            }

            self._find_location_on_main_page(location_data)

            if not location_data['metro_stations'] or not location_data['address']:
                self.logger.info("🗺️ Раскрываем карту для детального поиска...")
                if self._expand_location_map_improved():
                    time.sleep(3)
                    self._find_location_after_map_expansion_improved(location_data)

            if not location_data['metro_stations']:
                self._find_metro_in_expanded_card(location_data)

            self._build_final_location_improved(location_data)

            self.logger.info(f"📍 Итоговое местоположение: {location_data['full_location']}")
            self.logger.info(f"📍 Станций метро найдено: {len(location_data['metro_stations'])}")

            return location_data

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения местоположения: {e}")
            return {
                'metro_stations': [],
                'address': None,
                'full_location': 'Местоположение не указано'
            }

    def _find_location_on_main_page(self, location_data):
        """УПРОЩЕННЫЙ поиск местоположения на основной странице"""
        try:
            self.logger.info("🔍 Поиск местоположения на основной странице...")

            address_selectors = [
                '[data-marker="item-view/item-address"]',
                '[class*="address"]',
                '.style-address',
                '.item-address',
                '.seller-address',
                '.xLPJ6',
                '//span[contains(text(), "Москва")]',
                '//*[contains(text(), "ул.") or contains(text(), "проспект") or contains(text(), "шоссе")]'
            ]

            for selector in address_selectors:
                try:
                    if selector.startswith('//'):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for elem in elements:
                        text = elem.text.strip()
                        if text and self._is_valid_address_simple(text):
                            location_data['address'] = text
                            self.logger.info(f"🏠 Адрес найден на основной странице: '{text}'")
                            break

                    if location_data['address']:
                        break

                except Exception as e:
                    self.logger.debug(f"❌ Селектор адреса '{selector}' не сработал: {e}")
                    continue

            metro_selectors = [
                '[data-marker*="metro"]',
                '[class*="metro"]',
                '.style-metro',
                '.metro-station',
                '//*[contains(@class, "metro")]',
                '//*[contains(text(), "метро") or contains(text(), "Метро")]',
                '//*[contains(@class, "geo-geo")]',
                '.geo-geo',
            ]

            for selector in metro_selectors:
                try:
                    if selector.startswith('//'):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for elem in elements:
                        text = elem.text.strip()
                        if text:
                            self.logger.info(f"🔍 Найден элемент метро: '{text}'")
                            self._extract_metro_from_text_simple(text, location_data)

                except Exception as e:
                    self.logger.debug(f"❌ Селектор метро '{selector}' не сработал: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска на основной странице: {e}")

    def _is_valid_address_simple(self, line):
        """УЛУЧШЕННАЯ проверка валидности адреса"""
        try:
            if not line or len(line) < 5:
                return False

            line_lower = line.lower()

            critical_address_indicators = [
                'москва, ул.',
                'москва, улица',
                'москва, проспект',
                'москва, шоссе',
                'москва, бульвар',
                'москва, переулок',
                'москва, набережная',
                'ул. ',
                'улица ',
                'проспект ',
                'шоссе ',
                'бульвар ',
                'переулок ',
                'набережная ',
                'пл. ',
                'площадь '
            ]

            additional_indicators = [
                'дом', 'д.', 'корпус', 'корп.', 'строение', 'стр.',
                'район', 'р-н', 'микрорайон', 'мкр.', 'квартал'
            ]

            exclude_indicators = [
                'цена', 'руб', '₽', 'просмотр', 'отзыв', 'рейтинг',
                'продавец', 'объявление', 'избранное', 'метро', 'станция'
            ]

            has_critical_indicator = any(indicator in line_lower for indicator in critical_address_indicators)
            has_additional_indicator = any(indicator in line_lower for indicator in additional_indicators)
            has_exclude_indicator = any(indicator in line_lower for indicator in exclude_indicators)
            has_russian_letters = re.search(r'[а-яА-Я]', line)

            result = (
                    (has_critical_indicator and not has_exclude_indicator) or
                    (line_lower.startswith('москва,') and has_russian_letters and not has_exclude_indicator) or
                    (has_additional_indicator and has_russian_letters and not has_exclude_indicator and len(line) > 10)
            )

            if result:
                self.logger.info(f"✅ Строка определена как адрес: '{line}'")
                return True

            self.logger.debug(f"❌ Строка не распознана как адрес: '{line}'")
            return False

        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки адреса: {e}")
            return False

    def _extract_metro_from_text_simple(self, text, location_data):
        """ПРОСТОЕ извлечение станций метро из текста"""
        try:
            text_lower = text.lower()

            for station_name in self.metro_database.keys():
                station_lower = station_name.lower()

                if station_lower in text_lower:
                    metro_data = self._get_metro_data_by_station(station_name)
                    station_data = {
                        'name': station_name,
                        'color': metro_data['color'],
                        'line_number': metro_data['line_number'],
                        'line_name': metro_data['line_name'],
                        'circle_color': metro_data['circle_color']
                    }

                    if not any(s['name'] == station_name for s in location_data['metro_stations']):
                        location_data['metro_stations'].append(station_data)
                        self.logger.info(f"🚇 Найдена станция метро: {station_name} (линия {metro_data['line_number']})")
                        return True

            return False

        except Exception as e:
            self.logger.debug(f"❌ Ошибка извлечения метро из текста: {e}")
            return False

    def _expand_location_map_improved(self):
        """УЛУЧШЕННОЕ раскрытие карты местоположения"""
        try:
            self.logger.info("🗺️ УЛУЧШЕННОЕ раскрытие карты местоположения...")

            map_button_selectors = [
                '[data-marker="item-map-button"]',
                '[data-text-open="Узнать подробности"]',
                'button[data-text-open*="Узнать подробности"]',
                '.style-item-address-button-1yOgg',
                '[class*="map-button"]',
                '[class*="address-button"]',
                '.fDM1R',
                'button[class*="fDM1R"]',
                '.desktop-1q9f1w0',
                'button[class*="desktop"]',
                '//button[contains(text(), "Узнать подробности")]',
                '//span[contains(text(), "Узнать подробности")]',
                '//a[contains(text(), "Узнать подробности")]',
                '//*[contains(text(), "Узнать подробности")]',
                '//*[contains(@class, "item-map-button")]',
            ]

            for selector in map_button_selectors:
                try:
                    if selector.startswith('//'):
                        map_buttons = self.driver.find_elements(By.XPATH, selector)
                    else:
                        map_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    self.logger.info(f"🔍 Найдено кнопок '{selector}': {len(map_buttons)}")

                    for button in map_buttons:
                        try:
                            button_text = button.text.strip()
                            self.logger.info(f"🔍 Текст кнопки: '{button_text}'")

                            if any(word in button_text.lower() for word in
                                   ['узнать', 'подробности', 'карта', 'map', 'адрес', 'location']):
                                self.logger.info(f"🎯 Нажатие на кнопку: '{button_text}'")

                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", button)
                                time.sleep(1)

                                try:
                                    button.click()
                                    self.logger.info("✅ Клик по кнопке выполнен")
                                    time.sleep(3)
                                    return True
                                except:
                                    try:
                                        self.driver.execute_script("arguments[0].click();", button)
                                        self.logger.info("✅ Клик по кнопке выполнен через JavaScript")
                                        time.sleep(3)
                                        return True
                                    except:
                                        try:
                                            ActionChains(self.driver).move_to_element(button).click().perform()
                                            self.logger.info("✅ Клик по кнопке выполнен через ActionChains")
                                            time.sleep(3)
                                            return True
                                        except Exception as e:
                                            self.logger.debug(f"❌ Все способы клика не сработали: {e}")
                                            continue

                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка клика по кнопке: {e}")
                            continue

                except Exception as e:
                    self.logger.debug(f"❌ Селектор кнопки '{selector}' не сработал: {e}")
                    continue

            self.logger.warning("⚠️ Кнопка раскрытия карты не найдена")
            return False

        except Exception as e:
            self.logger.error(f"❌ Ошибка раскрытия карты: {e}")
            return False

    def _find_location_after_map_expansion_improved(self, location_data):
        """УЛУЧШЕННЫЙ поиск местоположения после раскрытия карты"""
        try:
            self.logger.info("🔍 УЛУЧШЕННЫЙ поиск после раскрытия карты...")
            time.sleep(2)

            address_card_selectors = [
                '[data-marker="sellerAddressInfoCard"]',
            ]

            for selector in address_card_selectors:
                try:
                    address_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🔍 Проверяем селектор '{selector}': найдено {len(address_cards)} элементов")

                    for card in address_cards:
                        try:
                            card_text = card.text.strip()
                            if card_text:
                                self.logger.info(f"📍 Карточка содержит текст: '{card_text}'")
                                self._parse_location_card_content_improved(card_text, location_data)
                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка анализа карточки: {e}")
                            continue

                except Exception as e:
                    self.logger.debug(f"❌ Селектор карточки '{selector}' не сработал: {e}")
                    continue

            expanded_selectors = [
                '//*[contains(@class, "address")]',
                '//*[contains(text(), "ул.")]',
                '//*[contains(@class, "geo")]',
            ]

            for selector in expanded_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text:
                            if not location_data['address'] and self._is_valid_address_simple(text):
                                location_data['address'] = text
                                self.logger.info(f"🏠 Адрес найден после раскрытия карты: '{text}'")

                            self._extract_metro_from_text_simple(text, location_data)

                except Exception as e:
                    self.logger.debug(f"❌ Селектор после раскрытия '{selector}' не сработал: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска после раскрытия карты: {e}")

    def _find_metro_in_expanded_card(self, location_data):
        """Специализированный поиск метро в раскрытой карточке"""
        try:
            self.logger.info("🔍 Специализированный поиск метро в раскрытой карточке...")

            metro_specific_selectors = [
                '//*[contains(@class, "metro-station")]',
                '//*[contains(@class, "metro-list")]',
                '//*[contains(@class, "station-item")]',
                '//*[contains(@class, "geo-station")]',
                '//span[contains(@class, "metro")]',
                '//div[contains(@class, "metro")]',
            ]

            for selector in metro_specific_selectors:
                try:
                    metro_elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in metro_elements:
                        text = elem.text.strip()
                        if text:
                            self.logger.info(f"🔍 Найден элемент метро: '{text}'")
                            self._extract_metro_from_text_simple(text, location_data)
                except Exception as e:
                    self.logger.debug(f"❌ Селектор метро '{selector}' не сработал: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"❌ Ошибка специализированного поиска метро: {e}")

    def _parse_location_card_content_improved(self, card_text, location_data):
        """УЛУЧШЕННЫЙ парсинг содержимого карточки местоположения"""
        try:
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            self.logger.info(f"🔍 Анализируем строки карточки: {lines}")

            for line in lines:
                if 'москва,' in line.lower() and any(
                        addr_indicator in line.lower() for addr_indicator in ['ул.', 'улица', 'проспект', 'шоссе']):
                    location_data['address'] = line
                    self.logger.info(f"🏠 АДРЕС НАЙДЕН ПРИОРИТЕТНО: '{line}'")
                    break

            if not location_data['address']:
                for line in lines:
                    if self._is_valid_address_simple(line):
                        location_data['address'] = line
                        self.logger.info(f"🏠 Адрес найден альтернативно: '{line}'")
                        break

            for line in lines:
                self._extract_metro_from_text_simple(line, location_data)

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга карточки: {e}")

    def _get_metro_data_by_station(self, station_name):
        """Возвращает данные станции метро из базы"""
        if station_name in self.metro_database:
            data = self.metro_database[station_name]
            return {
                'color': data['color'],
                'line_number': data['line_number'],
                'line_name': data['line_name'],
                'circle_color': self._get_circle_color_for_line(data['line_number'])
            }

        return {
            'color': '#666666',
            'line_number': '?',
            'line_name': 'Неизвестная линия',
            'circle_color': '#ffffff'
        }

    def _get_circle_color_for_line(self, line_number):
        """Определяет цвет кружка (белый или черный) в зависимости от цвета линии"""
        dark_lines = {'1', '2', '3', '5', '7', '8', '9', '10', '11', '12'}
        return '#000000' if line_number in dark_lines else '#ffffff'

    def _build_final_location_improved(self, location_data):
        """УЛУЧШЕННОЕ формирование итогового местоположения"""
        location_parts = []

        if location_data['metro_stations']:
            metro_names = [station['name'] for station in location_data['metro_stations']]
            location_parts.extend(metro_names)

        if location_data['address']:
            location_parts.append(location_data['address'])

        if location_parts:
            location_data['full_location'] = ' | '.join(location_parts)
            self.logger.info(f"📍 Сформировано местоположение: {location_data['full_location']}")
        else:
            location_data['full_location'] = 'Местоположение не указано'
            self.logger.warning("📍 Местоположение не указано")

        return location_data

    def extract_posted_date(self):
        """Извлекает дату размещения объявления"""
        try:
            self.logger.info("🔍 Поиск даты на странице...")

            date_selectors = [
                '[data-marker="item-view/item-date"]',
                'span[data-marker="item-view/item-date"]',
                '.T7ujv.Tdsqf.dsi88.cujIu.aStJv [data-marker="item-view/item-date"]',
                'article.jxYGn [data-marker="item-view/item-date"]',
            ]

            for selector in date_selectors:
                try:
                    date_elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🔍 Проверяем селектор '{selector}': найдено {len(date_elems)} элементов")

                    for date_elem in date_elems:
                        date_text = date_elem.text.strip()
                        self.logger.info(f"🔍 Текст элемента: '{date_text}'")

                        if date_text:
                            cleaned_date = date_text.replace('·', '').replace(' в ', ' ').strip()

                            if cleaned_date:
                                cleaned_date = cleaned_date[0].upper() + cleaned_date[1:]

                            if cleaned_date:
                                self.logger.info(f"✅ Дата найдена через '{selector}': '{cleaned_date}'")
                                return cleaned_date
                except Exception as e:
                    self.logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            try:
                all_date_markers = self.driver.find_elements(By.CSS_SELECTOR, '[data-marker*="date"]')
                self.logger.info(f"🔍 Найдено элементов с data-marker содержащим 'date': {len(all_date_markers)}")

                for elem in all_date_markers:
                    date_text = elem.text.strip()
                    if date_text:
                        self.logger.info(f"🔍 Дата из data-marker: '{date_text}'")
                        cleaned_date = date_text.replace('·', '').replace(' в ', ' ').strip()

                        if cleaned_date:
                            cleaned_date = cleaned_date[0].upper() + cleaned_date[1:]

                        if cleaned_date:
                            self.logger.info(f"✅ Дата найдена через data-marker: '{cleaned_date}'")
                            return cleaned_date
            except Exception as e:
                self.logger.debug(f"❌ Поиск по data-marker не сработал: {e}")

            self.logger.warning("❌ Дата не найдена после всех попыток")
            return 'Дата не указана'

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения даты: {e}")
            return 'Дата не указана'

    def _extract_description(self):
        """Извлекает полное описание товара с сохранением форматирования"""
        try:
            self.logger.info("🔍 Поиск полного описания товара...")

            read_more_selectors = [
                '//a[contains(text(), "Читать полностью")]',
                '//button[contains(text(), "Читать полностью")]',
                '//*[contains(text(), "Читать полностью")]',
                '[data-marker="item-description/expand"]',
                '.styles.module__root___XzVhMW',
                'a[role="button"]',
                '.style__item-description-expand___XzQzYT'
            ]

            button_clicked = False
            for selector in read_more_selectors:
                try:
                    if selector.startswith('//'):
                        buttons = self.driver.find_elements(By.XPATH, selector)
                    else:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for button in buttons:
                        try:
                            button_text = button.text.strip()
                            if any(phrase in button_text.lower() for phrase in
                                   ['читать полностью', 'развернуть', 'показать полностью']):
                                self.logger.info(f"🎯 Нажимаем кнопку: '{button_text}'")

                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", button)
                                time.sleep(1)

                                try:
                                    button.click()
                                    self.logger.info("✅ Клик по кнопке выполнен")
                                    button_clicked = True
                                    time.sleep(2)
                                    break
                                except:
                                    try:
                                        self.driver.execute_script("arguments[0].click();", button)
                                        self.logger.info("✅ Клик по кнопке выполнен через JavaScript")
                                        button_clicked = True
                                        time.sleep(2)
                                        break
                                    except:
                                        continue

                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка клика по кнопке: {e}")
                            continue

                    if button_clicked:
                        break

                except Exception as e:
                    self.logger.debug(f"❌ Селектор кнопки '{selector}' не сработал: {e}")
                    continue

            description = None

            description_selectors = [
                '[data-marker="item-view/item-description"]',
                '.item-description-text',
                '.description-text',
                '[itemprop="description"]',
                '.iva-item-text-Ge6dR'
            ]

            for selector in description_selectors:
                try:
                    desc_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🔍 Проверяем селектор описания '{selector}': найдено {len(desc_elements)}")

                    for desc_elem in desc_elements:
                        try:
                            desc_text = desc_elem.text.strip()
                            if desc_text and len(desc_text) > 10:
                                description = desc_text
                                self.logger.info(f"✅ Описание найдено через '{selector}': {len(description)} символов")
                                break
                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка извлечения текста: {e}")
                            continue

                    if description:
                        break

                except Exception as e:
                    self.logger.debug(f"❌ Селектор описания '{selector}' не сработал: {e}")
                    continue

            if not description:
                try:
                    self.logger.info("🔍 Поиск описания в HTML содержимом...")

                    html_description_selectors = [
                        '.style__item-description-html___XzQzYT',
                        '[data-marker="item-view/item-description-html"]',
                        '.item-description-html',
                        '.description-html'
                    ]

                    for selector in html_description_selectors:
                        try:
                            html_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for html_elem in html_elements:
                                try:
                                    html_content = html_elem.get_attribute('innerHTML')
                                    if html_content:
                                        from bs4 import BeautifulSoup
                                        soup = BeautifulSoup(html_content, 'html.parser')

                                        for br in soup.find_all("br"):
                                            br.replace_with("\n")

                                        text_content = soup.get_text(separator='\n', strip=False)
                                        if text_content and len(text_content) > 10:
                                            description = text_content.strip()
                                            self.logger.info(f"✅ Описание из HTML: {len(description)} символов")
                                            break
                                except Exception as e:
                                    self.logger.debug(f"❌ Ошибка парсинга HTML: {e}")
                                    continue

                            if description:
                                break

                        except Exception as e:
                            self.logger.debug(f"❌ HTML селектор '{selector}' не сработал: {e}")
                            continue
                except Exception as e:
                    self.logger.debug(f"❌ Поиск в HTML не сработал: {e}")

            if not description:
                try:
                    self.logger.info("🔍 Поиск любого текста в блоке описания...")

                    parent_selectors = [
                        '#bx_item-description',
                        '.style__item-description___XzQzYT',
                        '[class*="item-description"]',
                        '.item-view-description'
                    ]

                    for selector in parent_selectors:
                        try:
                            parent_elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for parent_elem in parent_elems:
                                full_text = parent_elem.text
                                if full_text and len(full_text) > 50:
                                    lines = full_text.split('\n')
                                    description_lines = []
                                    for line in lines:
                                        clean_line = line.strip()
                                        if clean_line and clean_line.lower() not in ['описание', 'description']:
                                            description_lines.append(clean_line)

                                    if description_lines:
                                        description = '\n'.join(description_lines)
                                        self.logger.info(
                                            f"✅ Описание из родительского блока: {len(description)} символов")
                                        break
                        except Exception as e:
                            self.logger.debug(f"❌ Родительский селектор '{selector}' не сработал: {e}")
                            continue
                except Exception as e:
                    self.logger.debug(f"❌ Поиск в родительском блоке не сработал: {e}")

            if description:
                self.logger.info(f"✅ ФИНАЛЬНОЕ ОПИСАНИЕ: {len(description)} символов")
                return description
            else:
                self.logger.warning("❌ Описание не найдено")
                return "Описание отсутствует"

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения описания: {e}")
            return "Описание отсутствует"

    def _extract_condition(self):
        """Парсит только параметр 'Состояние' из характеристик"""
        try:
            self.logger.info("🔍 Поиск параметра 'Состояние' в характеристиках...")

            params_selectors = [
                '[data-marker="item-view/item-params"]',
                '#bx_item-params',
                '[data-marker="item-params"]',
                '[class*="params-params"]',
                '[class*="item-params"]',
                '.styles.module__root___XzUyYW.styles.module__root___XzIyMW.styles.module__size_xxxl___XzE0MG',
                '[class*="styles.module__root"]',
                '.params__paramsList___XzY3MG',
                '.params__paramsList__item___XzY3MG',
                '[class*="params__paramsList"]',
                '.item-params',
                '.params'
            ]

            for selector in params_selectors:
                try:
                    params_blocks = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🔍 Проверяем селектор '{selector}': найдено {len(params_blocks)} блоков")

                    for block in params_blocks:
                        try:
                            condition = self._find_condition_in_block(block)
                            if condition:
                                condition_lower = condition.lower()
                                if any(word in condition_lower for word in ['нов', 'new', 'бирк']):
                                    condition = "Новое с биркой"
                                elif any(word in condition_lower for word in ['б/у', 'бу', 'used']):
                                    condition = "Б/у"
                                elif any(word in condition_lower for word in ['как нов', 'like new']):
                                    condition = "Как новый"

                                self.logger.info(f"✅ Состояние найдено и нормализовано: '{condition}'")
                                return condition

                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка анализа блока: {e}")
                            continue

                except Exception as e:
                    self.logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            self.logger.info("🔧 Состояние не найдено в характеристиках")
            return "Не указано"

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга состояния: {e}")
            return "Не указано"

    def _find_condition_in_block(self, block):
        """Ищет параметр 'Состояние' в блоке характеристик"""
        try:
            item_elements = block.find_elements(By.CSS_SELECTOR, '.params__paramsList__item___XzY3MG')
            self.logger.info(f"🔍 Найдено элементов характеристик: {len(item_elements)}")

            for item in item_elements:
                try:
                    item_text = item.text.strip()
                    self.logger.info(f"🔍 Текст элемента характеристик: '{item_text}'")

                    if 'Состояние' in item_text:
                        separators = [':', ' ']

                        for separator in separators:
                            if f'Состояние{separator}' in item_text:
                                parts = item_text.split(f'Состояние{separator}')
                                if len(parts) > 1:
                                    value = parts[1].strip()
                                    if value:
                                        self.logger.info(f"✅ Состояние найдено через '{separator}': '{value}'")
                                        return value

                        if 'Состояние' in item_text and not any(sep in item_text for sep in [':', ' ']):
                            value = item_text.replace('Состояние', '').strip()
                            if value:
                                self.logger.info(f"✅ Состояние найдено (без разделителя): '{value}'")
                                return value

                except Exception as e:
                    self.logger.debug(f"❌ Ошибка анализа элемента: {e}")
                    continue

            try:
                state_spans = block.find_elements(By.XPATH, ".//span[contains(text(), 'Состояние')]")
                self.logger.info(f"🔍 Найдено span с 'Состояние': {len(state_spans)}")

                for span in state_spans:
                    try:
                        parent = span.find_element(By.XPATH, "./..")
                        full_text = parent.text.strip()
                        self.logger.info(f"🔍 Текст родительского элемента: '{full_text}'")

                        if 'Состояние' in full_text:
                            if ':' in full_text:
                                value = full_text.split(':')[-1].strip()
                            else:
                                value = full_text.replace('Состояние', '').strip()

                            if value and value != 'Состояние':
                                self.logger.info(f"✅ Состояние найдено через span: '{value}'")
                                return value
                    except Exception as e:
                        self.logger.debug(f"❌ Ошибка анализа span: {e}")
                        continue
            except Exception as e:
                self.logger.debug(f"❌ Поиск по span не сработал: {e}")

            return None

        except Exception as e:
            self.logger.debug(f"❌ Ошибка поиска состояния в блоке: {e}")
            return None

    def _extract_seller_name(self):
        """Извлекает имя продавца"""
        seller_selectors = [
            '[data-marker="seller-info/name"]',
            '.seller-info-name',
            '.style-title-_wF5H',
            '[data-marker="seller-link/link"]'
        ]

        for selector in seller_selectors:
            try:
                seller_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                seller_name = seller_elem.text.strip()
                if seller_name:
                    return seller_name
            except:
                continue
        return None

    def _extract_seller_rating(self):
        """Извлекает рейтинг продавца и количество отзывов"""
        try:
            rating = None
            reviews_count = None

            rating_selectors = [
                '.seller-info-rating span',
                '[data-marker="seller-rating/score"]',
                '.index-score-DR6fx'
            ]

            for selector in rating_selectors:
                try:
                    rating_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in rating_elements:
                        text = elem.text.strip()
                        if text and re.match(r'^\d+[.,]?\d*$', text):
                            rating_text = text.replace(',', '.')
                            rating = float(rating_text)
                            if 1 <= rating <= 5:
                                break
                    if rating:
                        break
                except:
                    continue

            reviews_selectors = [
                '[data-marker="seller-rating/count"]',
                '.seller-info-rating a',
                '.index-sellerReviewsCount-1H6g_'
            ]

            for selector in reviews_selectors:
                try:
                    reviews_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    reviews_text = reviews_elem.text.strip()
                    reviews_match = re.search(r'(\d+)', reviews_text)
                    if reviews_match:
                        reviews_count = int(reviews_match.group(1))
                        break
                except:
                    continue

            return rating, reviews_count

        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось получить рейтинг продавца: {e}")
            return None, None

    def _extract_category(self):
        """Извлекает категорию из навигационной цепочки"""
        try:
            navigation_selectors = [
                '[data-marker="breadcrumbs"]',
                '[data-marker="item-navigation"]',
                '.breadcrumbs',
                '.js-breadcrumbs',
                '.breadcrumb'
            ]

            navigation_element = None
            for selector in navigation_selectors:
                try:
                    navigation_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue

            if not navigation_element:
                return None

            try:
                links = navigation_element.find_elements(By.TAG_NAME, 'a')
                breadcrumbs = []
                for link in links:
                    try:
                        text = link.text.strip()
                        if text and text not in ['Главная', 'Avito', 'Все категории', '']:
                            breadcrumbs.append(text)
                    except:
                        continue

                if len(breadcrumbs) >= 3:
                    return breadcrumbs[-2]
                elif breadcrumbs:
                    return breadcrumbs[-1]
                else:
                    return None

            except Exception as e:
                self.logger.error(f"❌ Ошибка парсинга навигации: {e}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения категории: {e}")
            return None

    def _extract_city(self):
        """🔍 Поиск города на странице..."""
        try:
            try:
                location_blocks = self.driver.find_elements(By.XPATH,
                                                            "//h2[contains(text(), 'Местоположение')]/following-sibling::div")
                self.logger.info(f"🔍 Найдено блоков 'Местоположение': {len(location_blocks)}")

                for block in location_blocks:
                    block_text = block.text.strip()
                    if block_text:
                        self.logger.info(f"🔍 Текст блока 'Местоположение': '{block_text}'")

                        city = self._parse_city_from_text(block_text)
                        if city:
                            self.logger.info(f"✅ Город найден в блоке 'Местоположение': '{city}'")
                            return city

                        address_spans = block.find_elements(By.XPATH,
                                                            ".//span[contains(@class, 'address') or contains(text(), 'Москва') or contains(text(), 'Санкт-Петербург')]")
                        for span in address_spans:
                            span_text = span.text.strip()
                            if span_text:
                                city = self._parse_city_from_text(span_text)
                                if city:
                                    self.logger.info(f"✅ Город найден в span блока 'Местоположение': '{city}'")
                                    return city
            except Exception as e:
                self.logger.debug(f"⚠️ Поиск в блоке 'Местоположение' не сработал: {e}")

            new_selectors = [
                '.style-item-address-string-N33h3',
                '[class*="item-address-string"]',
                '.style__item-address__string___XzQ5MT',
                '[class*="item-address__string"]',
                '.style__item-address___XzQ5MT',
                '[data-marker="item-view/title-address"]',
                '.style-item-view-title-address',
                '[class*="title-address"]',
                '[class*="address-root"]',
                '.style-item-view-description-address',
            ]

            for selector in new_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🔍 Проверяем селектор '{selector}': найдено {len(elements)} элементов")
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 1:
                            self.logger.info(f"🔍 Текст элемента: '{text}'")
                            city = self._parse_city_from_text(text)
                            if city:
                                self.logger.info(f"✅ Город найден через '{selector}': '{city}'")
                                return city
                except Exception as e:
                    self.logger.debug(f"⚠️ Селектор {selector} не сработал: {e}")
                    continue

            self.logger.warning("❌ Город не найден, используем 'Москва' по умолчанию")
            return "Москва"

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска города: {e}")
            return "Москва"

    def _parse_city_from_text(self, text):
        """Парсит город из текста"""
        try:
            self.logger.info(f"🔍 _parse_city_from_text вызван с текстом: '{text}'")

            if not text:
                return None

            major_cities = {
                'москва': 'Москва',
                'мск': 'Москва',
                'санкт-петербург': 'Санкт-Петербург',
                'спб': 'Санкт-Петербург',
                'питер': 'Санкт-Петербург',
                'воронеж': 'Воронеж',
                'барнаул': 'Барнаул',
                'казань': 'Казань',
                'екатеринбург': 'Екатеринбург',
                'новосибирск': 'Новосибирск',
                'нижний новгород': 'Нижний Новгород',
                'самара': 'Самара',
                'омск': 'Омск',
                'челябинск': 'Челябинск',
                'ростов-на-дону': 'Ростов-на-Дону',
                'уфа': 'Уфа',
                'красноярск': 'Красноярск',
                'пермь': 'Пермь',
                'волгоград': 'Волгоград',
                'сочи': 'Сочи',  # 🔥 ДОБАВЛЕНО!
                'пенза': 'Пенза'  # 🔥 ДОБАВЛЕНО!
            }

            cleaned_text = ' '.join(text.split())
            text_lower = cleaned_text.lower()

            for city_pattern, city_name in major_cities.items():
                if city_pattern in text_lower:
                    self.logger.info(f"✅ Город распознан по паттерну '{city_pattern}': '{city_name}'")
                    return city_name

            if ',' not in text and len(text) < 30 and not any(char.isdigit() for char in text):
                self.logger.info(f"✅ Город из текста (простой): '{text}'")
                return text

            self.logger.info(f"❌ Город не распознан в тексте: '{text}'")
            return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга города: {e}")
            return None

    def _extract_address(self):
        """🔍 Извлечение адреса из карточки"""
        try:
            address_selectors = [
                '[data-marker="sellerAddressInfoCard"]',
                '.style-addressInfoCard',
                '.seller-address-info-card',
                '.address-info-card',
                '[class*="addressInfoCard"]',
                '[class*="address-card"]'
            ]

            for selector in address_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 10:
                            self.logger.info(f"📍 Адрес найден в '{selector}': '{text}'")
                            return text
                except:
                    continue
            return None
        except:
            return None

    def _extract_city_from_address(self, address):
        """🎯 Извлечение города из адресной строки"""
        try:
            if ',' in address:
                possible_city = address.split(',')[0].strip()

                main_cities = [
                    'Москва', 'Санкт-Петербург', 'Екатеринбург', 'Новосибирск', 'Казань',
                    'Нижний Новгород', 'Самара', 'Омск', 'Челябинск', 'Ростов-на-Дону',
                    'Уфа', 'Красноярск', 'Пермь', 'Воронеж', 'Волгоград', 'Подольск',
                    'Сочи', 'Пенза'  # 🔥 ДОБАВЛЕНО!
                ]

                if possible_city in main_cities:
                    self.logger.info(f"✅ Город из адреса: '{possible_city}'")
                    return possible_city

            return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения города из адреса: {e}")
            return None

    def _extract_views_count(self):
        """Извлекает количество просмотров объявления: общие и за сегодня"""
        try:
            views_data = {
                'total_views': 0,
                'today_views': 0
            }

            total_views_selectors = [
                '[data-marker="item-view/total-views"]',
                '.style-item-views-F2T5T',
                '.js-item-views',
                '.item-views',
                '[class*="views"]'
            ]

            today_views_selector = '[data-marker="item-view/today-views"]'

            for selector in total_views_selectors:
                try:
                    views_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in views_elements:
                        views_text = elem.text.strip()
                        if views_text and any(word in views_text.lower() for word in ['просмотр', 'view']):
                            numbers = re.findall(r'\d+', views_text)
                            if numbers:
                                views_data['total_views'] = int(numbers[0])
                                self.logger.info(f"✅ Общие просмотры найдены: {views_data['total_views']}")
                                break
                    if views_data['total_views'] > 0:
                        break
                except:
                    continue

            try:
                today_elements = self.driver.find_elements(By.CSS_SELECTOR, today_views_selector)
                for elem in today_elements:
                    today_text = elem.text.strip()
                    if today_text:
                        today_match = re.search(r'\(\+(\d+)\s*сегодня\)', today_text)
                        if today_match:
                            views_data['today_views'] = int(today_match.group(1))
                        else:
                            today_match = re.search(r'\+(\d+).*сегодня', today_text)
                            if today_match:
                                views_data['today_views'] = int(today_match.group(1))
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось извлечь просмотры за сегодня: {e}")

            self.logger.info(f"👀 Просмотры - Всего: {views_data['total_views']}, Сегодня: {views_data['today_views']}")
            return views_data

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения просмотров: {e}")
            return {'total_views': 0, 'today_views': 0}

    def parse_price(self, price_text):
        """Парсит цену из текста"""
        try:
            digits = ''.join(filter(str.isdigit, price_text))
            return int(digits) if digits else 0
        except:
            return 0

    async def parse_product_item(self, item_element, query=None):
        """🔍 Парсит товар с учетом СВЕЖЕСТИ (улучшенная версия)"""
        try:
            product_data = await self.parse_item_advanced(item_element, query)

            if not product_data:
                return None

            freshness_score = await self.analyze_listing_freshness(item_element, product_data)
            product_data['freshness_score'] = freshness_score

            product_data['is_fresh_by_indicators'] = self._detect_fresh_listing_indicators(item_element)
            product_data['freshness_report'] = await self.get_freshness_analysis_report(item_element, product_data)

            product_data['priority_score'] = self._calculate_priority_score(product_data)

            self.logger.info(
                f"🎯 Товар: {product_data.get('name', '')[:50]}... | Свежесть: {freshness_score:.2f} | Приоритет: {product_data['priority_score']:.2f}")

            return product_data

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга товара: {e}")
            return None

    def _calculate_priority_score(self, product_data):
        """🎯 Расчет приоритета для сортировки"""
        try:
            base_score = product_data.get('freshness_score', 0.3)

            if product_data.get('is_fresh_by_indicators', False):
                base_score += 0.2

            if product_data.get('time_listed', 24) <= 2:
                base_score += 0.15

            if product_data.get('seller_rating', 0) > 4.5:
                base_score += 0.1

            return min(max(base_score, 0.0), 1.0)

        except Exception as e:
            self.logger.debug(f"⚠️ Ошибка расчета приоритета: {e}")
            return 0.5

    async def parse_item(self, item, category):
        """🔍 Парсит товар - реализация абстрактного метода BaseSiteParser"""
        try:
            self.logger.info(f"🔍 AvitoParser.parse_item вызван с category: {category}")

            product_data = await self.parse_item_advanced(item, category)

            if not product_data:
                return None

            freshness_score = await self.analyze_listing_freshness(item, product_data)
            product_data['freshness_score'] = freshness_score

            product_data['is_fresh_by_indicators'] = self._detect_fresh_listing_indicators(item)
            product_data['freshness_report'] = await self.get_freshness_analysis_report(item, product_data)

            product_data['priority_score'] = self._calculate_priority_score(product_data)

            self.logger.info(
                f"🎯 Товар: {product_data.get('name', '')[:50]}... | Свежесть: {freshness_score:.2f} | Приоритет: {product_data['priority_score']:.2f}")

            return product_data

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга товара в parse_item: {e}")
            return None

    # 🔥 🔥 🔥 НОВЫЕ МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ СО СТАРОЙ ЛОГИКОЙ

    async def _extract_seller_info_with_avatar(self):
        """🔥 Извлекает информацию о продавце включая аватарку и ссылку на профиль"""
        try:
            seller_info = {
                'seller_name': 'Не указан',
                'seller_type': 'Не указан',
                'seller_avatar': None,
                'seller_profile_url': None
            }

            seller_selectors = [
                '[data-marker="seller-info"]',
                '.seller-info',
                '.style__seller-info-prop___XzY4OG',
                '.styles.module__root___ZjgyNT',
                '[class*="seller-info"]',
                '[class*="sellerInfo"]'
            ]

            seller_element = None
            for selector in seller_selectors:
                try:
                    seller_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"✅ Найден блок продавца: {selector}")
                    break
                except:
                    continue

            if not seller_element:
                self.logger.warning("❌ Не найден блок продавца")
                return seller_info

            avatar_url = await self._extract_seller_avatar(seller_element)
            if avatar_url:
                seller_info['seller_avatar'] = avatar_url

            seller_name = await self._extract_seller_name_from_block(seller_element)
            if seller_name:
                seller_info['seller_name'] = seller_name

            seller_profile_url = await self._extract_seller_profile_url(seller_element)
            if seller_profile_url:
                seller_info['seller_profile_url'] = seller_profile_url

            seller_type = await self._extract_seller_type_from_block(seller_element)
            if seller_type:
                seller_info['seller_type'] = seller_type

            self.logger.info(f"👤 Информация о продавце: {seller_info}")
            return seller_info

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения информации о продавце: {e}")
            return {
                'seller_name': 'Не указан',
                'seller_type': 'Не указан',
                'seller_avatar': None,
                'seller_profile_url': None
            }

    async def _extract_seller_avatar(self, seller_element):
        """🔥 СТРОГИЙ поиск аватарки - ТОЛЬКО точные селекторы"""
        try:
            self.logger.info("🔍 СТРОГИЙ поиск аватарки - только точные селекторы...")

            exact_avatar_selectors = [
                '.style__seller-info-shop-img___XzY4OG',
                '.style__sellerInfoShopImgRedesign___XzY4OG',
                '.style__seller-info-avatar-image___XzY4OG',
                '.style__sellerInfoAvatarImageRedesign___XzY4OG',
                '[data-marker="seller-info/avatar-link"]'
            ]

            for selector in exact_avatar_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    self.logger.info(f"🔍 Проверяем точный селектор '{selector}': найдено {len(elements)}")

                    for element in elements:
                        try:
                            avatar_url = await self._extract_from_exact_element(element, selector)
                            if avatar_url:
                                self.logger.info(f"👤 ✅ Найдена реальная аватарка: {avatar_url}")
                                return avatar_url
                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка извлечения: {e}")
                            continue
                except Exception as e:
                    self.logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            self.logger.info("ℹ️ Аватарки нет (не найдено точных селекторов)")
            return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска аватарки: {e}")
            return None

    async def _extract_from_exact_element(self, element, selector):
        """Извлекает аватарку только из точных селекторов"""
        try:
            if 'shop-img' in selector or 'ShopImg' in selector:
                avatar_url = element.get_attribute('src')
                if avatar_url and self._is_valid_avatar_url(avatar_url):
                    return self._normalize_avatar_url(avatar_url)

            else:
                style_attr = element.get_attribute('style')
                if style_attr and 'background-image' in style_attr:
                    url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style_attr)
                    if url_match:
                        avatar_url = url_match.group(1)
                        if self._is_valid_avatar_url(avatar_url):
                            return self._normalize_avatar_url(avatar_url)

                try:
                    bg_image = self.driver.execute_script(
                        "return window.getComputedStyle(arguments[0]).getPropertyValue('background-image');",
                        element
                    )
                    if bg_image and bg_image != 'none':
                        url_match = re.search(r'url\(["\']?(.*?)["\']?\)', bg_image)
                        if url_match:
                            avatar_url = url_match.group(1)
                            if self._is_valid_avatar_url(avatar_url):
                                return self._normalize_avatar_url(avatar_url)
                except:
                    pass

            return None

        except Exception as e:
            self.logger.debug(f"❌ Ошибка извлечения из точного элемента: {e}")
            return None

    def _is_valid_avatar_url(self, url):
        """СТРОГАЯ проверка URL аватарки"""
        if not url:
            return False

        valid_patterns = [
            'avito.st/image/1/1.',
            'stub_avatars',
        ]

        return any(pattern in url for pattern in valid_patterns)

    def _normalize_avatar_url(self, url):
        """Нормализует URL аватарки"""
        if not url:
            return None

        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return 'https://www.avito.ru' + url
        return url

    async def _extract_seller_name_from_block(self, seller_element):
        """Извлекает имя продавца из блока"""
        try:
            name_selectors = [
                '[data-marker="seller-info/name"]',
                '.style__seller-info-name___XzY4OG',
                '.js-seller-info-name',
                '[data-marker="seller-link/link"]',
                '.styles.module__root___XzUyYW a',
                'h3 a',
                '.seller-info-name'
            ]

            for selector in name_selectors:
                try:
                    name_elements = seller_element.find_elements(By.CSS_SELECTOR, selector)
                    for name_element in name_elements:
                        name_text = name_element.text.strip()
                        if name_text and name_text not in ['', 'Частное лицо']:
                            self.logger.info(f"✅ Имя продавца найдено: {name_text}")
                            return name_text
                except:
                    continue

            return "Не указан"

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения имени продавца: {e}")
            return "Не указан"

    async def _extract_seller_type_from_block(self, seller_element):
        """Определяет тип продавца из блока"""
        try:
            seller_text = seller_element.text.lower()

            if 'частное лицо' in seller_text:
                return "Частное лицо"
            elif any(word in seller_text for word in ['компания', 'фирма', 'организация', 'бизнес']):
                return "Компания"
            elif any(word in seller_text for word in ['салон', 'дилер', 'автоцентр']):
                return "Автосалон"

            return "Не указан"

        except Exception as e:
            self.logger.error(f"❌ Ошибка определения типа продавца: {e}")
            return "Не указан"

    async def _extract_seller_profile_url(self, seller_element):
        """Извлекает ссылку на профиль продавца"""
        try:
            self.logger.info("🔗 Поиск ссылки на профиль продавца...")

            profile_selectors = [
                '[data-marker="seller-link/link"]',
                '.styles.module__root___XzVhMW[href*="/brands/"]',
                'a[href*="/brands/"][title*="профиль"]',
                'a[data-marker="seller-link/link"]',
                '//a[contains(@href, "/brands/")]',
                '//a[contains(@title, "профиль")]'
            ]

            for selector in profile_selectors:
                try:
                    if selector.startswith('//'):
                        profile_links = self.driver.find_elements(By.XPATH, selector)
                    else:
                        profile_links = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for link in profile_links:
                        profile_url = link.get_attribute('href')
                        if profile_url and '/brands/' in profile_url:
                            self.logger.info(f"✅ Ссылка на профиль продавца найдена: {profile_url}")
                            return profile_url

                except Exception as e:
                    self.logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            self.logger.info("ℹ️ Ссылка на профиль продавца не найдена")
            return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска ссылки на профиль: {e}")
            return None