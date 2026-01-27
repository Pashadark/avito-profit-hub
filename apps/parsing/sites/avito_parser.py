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

from .base_site_parser import BaseSiteParser
from ..utils.product_validator import ProductValidator
from ..utils.image_processor import ImageProcessor
from ..utils.moscow_metro import MOSCOW_METRO_DATABASE

logger = logging.getLogger('parser.avito')

try:
    from apps.parsing.utils.custom_user_agents import apply_user_agent_to_driver

    USER_AGENTS_AVAILABLE = True
except ImportError as e:
    USER_AGENTS_AVAILABLE = False


class AvitoParser(BaseSiteParser):
    """Оптимизированный парсер для Avito.ru с быстрыми селекторами"""

    def __init__(self, driver, city=None):
        super().__init__(driver)
        self.logger = logger
        self.validator = ProductValidator()
        self.image_processor = ImageProcessor(driver)
        self.metro_database = MOSCOW_METRO_DATABASE
        self._captcha_notification_sent = False

        # Оптимизированные селекторы свежести
        self.freshness_indicators = [
            '[data-marker*="new"]',
            '.iva-item-dateStep-__qB8a',
            '[data-marker="item-date"]',
            '.styles_remainingTime__P_aaq',
        ]

        self.city = city if city else "Москва"
        self.site_name = "avito"
        self.base_url = "https://www.avito.ru"

        self.logger.info(f"🌍 AvitoParser: город {self.city}")

        if USER_AGENTS_AVAILABLE:
            try:
                apply_user_agent_to_driver(driver, getattr(self, 'window_id', 0))
            except Exception as e:
                self.logger.debug(f"⚠️ User-Agent: {e}")

    def build_search_url(self, query, page=1, **kwargs):
        """Оптимизированное построение URL для поиска"""
        try:
            encoded_query = quote_plus(query)

            if self.city:
                try:
                    from apps.parsing.utils.city_translator import CITY_MAPPING
                    city_mapping = CITY_MAPPING
                    city_lower = self.city.strip().lower()

                    if city_lower in city_mapping:
                        city_part = city_mapping[city_lower]
                    else:
                        for rus_name, eng_name in city_mapping.items():
                            if rus_name.lower() == city_lower:
                                city_part = eng_name
                                break
                        else:
                            # Фолбэк транслитерация
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
                    local_mapping = {
                        'москва': 'moskva', 'санкт-петербург': 'sankt-peterburg',
                        'новосибирск': 'novosibirsk', 'екатеринбург': 'ekaterinburg',
                        'казань': 'kazan', 'нижний новгород': 'nizhniy_novgorod',
                        'челябинск': 'chelyabinsk', 'самара': 'samara', 'омск': 'omsk',
                        'ростов-на-дону': 'rostov-na-donu', 'уфа': 'ufa',
                        'красноярск': 'krasnoyarsk', 'пермь': 'perm', 'воронеж': 'voronezh',
                        'волгоград': 'volgograd', 'пенза': 'penza', 'сочи': 'sochi'
                    }
                    city_lower = self.city.strip().lower()
                    city_part = local_mapping.get(city_lower, 'moskva')
            else:
                city_part = 'moskva'

            # Чистим двойные дефисы
            city_part = re.sub(r'-+', '-', city_part)
            url = f"{self.base_url}/{city_part}?q={encoded_query}"

            params = ["s=104"]  # сортировка по дате

            if hasattr(self, 'min_price') and self.min_price:
                params.append(f"pmin={int(self.min_price)}")
            if hasattr(self, 'max_price') and self.max_price:
                params.append(f"pmax={int(self.max_price)}")
            if page > 1:
                params.append(f"p={page}")

            if params:
                url += "&" + "&".join(params)

            self.logger.debug(f"🔗 URL: {url}")
            return url

        except Exception as e:
            self.logger.error(f"❌ Ошибка URL: {e}")
            return f"{self.base_url}/moskva?q={quote_plus(query)}&s=104"

    async def search_items(self, query, **kwargs):
        """Оптимизированный поиск товаров С ЛИСТАНИЕМ СТРАНИЦ"""
        try:
            self.logger.info(f"🎯 Поиск: '{query}'")

            max_pages = kwargs.get('max_pages', 3)  # НОВЫЙ ПАРАМЕТР
            max_items = kwargs.get('max_items', 100)

            all_items = []

            for page in range(1, max_pages + 1):
                self.logger.info(f"📄 Страница {page}/{max_pages} для запроса '{query}'")

                url = self.build_search_url(query, page=page)  # ПЕРЕДАЕМ СТРАНИЦУ
                self.logger.debug(f"🌐 Открываем: {url[:80]}...")

                try:
                    self.driver.get(url)
                except Exception as e:
                    self.logger.error(f"❌ Ошибка загрузки страницы {page}: {e}")
                    break

                time.sleep(1.0)

                # Проверка на блокировку
                page_title = self.driver.title.lower()
                if any(word in page_title for word in ["подозрительная", "робот", "блокировка"]):
                    self.logger.warning("🚨 Обнаружена блокировка на странице {page}")
                    await self._handle_captcha_situation()
                    break

                # Парсим текущую страницу
                items = await self.parse_search_results(query)

                # Конвертация в старый формат
                converted_items = []
                for item in items:
                    if 'title' in item:
                        converted_item = item.copy()
                        converted_item['name'] = converted_item['title']
                        del converted_item['title']
                        converted_items.append(converted_item)
                    else:
                        converted_items.append(item)

                self.logger.info(f"✅ Страница {page}: найдено {len(converted_items)} товаров")
                all_items.extend(converted_items)

                # Если на этой странице мало товаров, дальше не листаем
                if len(converted_items) < 10:
                    self.logger.info(f"⚠️  На странице {page} мало товаров ({len(converted_items)}), останавливаемся")
                    break

                # Если уже собрали достаточно товаров
                if len(all_items) >= max_items:
                    self.logger.info(f"⚠️  Собрано {len(all_items)} товаров (лимит: {max_items})")
                    break

                # Небольшая пауза между страницами
                time.sleep(0.5)

            self.logger.info(f"🎯 ИТОГО для '{query}': {len(all_items)} товаров с {max_pages} страниц")
            return all_items[:max_items]  # Ограничиваем общее количество

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
            return []

    async def parse_search_results(self, query):
        """Быстрый парсинг результатов поиска"""
        try:
            self._captcha_notification_sent = False
            time.sleep(0.5)  # Уменьшено с 1 до 0.5

            # Проверка на очевидную блокировки
            if self._check_real_captcha_block():
                await self._handle_captcha_situation()
                return []

            items = await self._find_all_items()

            if not items:
                self.logger.warning("❌ Нет товаров на странице")
                return []

            self.logger.info(f"🔍 Анализируем {len(items)} товаров")

            search_keywords = self._parse_search_query(query)
            products = []
            exact_matches = []
            partial_matches = []

            for item in items[:100]:  # Ограничиваем для скорости
                try:
                    product = await self.parse_item_advanced(item, query)
                    if product:
                        relevance = self._check_relevance(product, search_keywords, query)
                        if relevance == "exact":
                            exact_matches.append(product)
                        elif relevance == "partial":
                            partial_matches.append(product)
                except:
                    continue

            # Собираем все результаты
            final_products = []
            if exact_matches:
                final_products.extend(exact_matches)
            if partial_matches:
                final_products.extend(partial_matches)

            # Берем только первые 20 для производительности
            if len(final_products) > 20:
                final_products = final_products[:20]

            # Фильтруем хорошие сделки
            good_deals = []
            for product in final_products:
                if await self.validator.is_good_deal(product):
                    good_deals.append(product)

            self.logger.info(f"🎯 Хороших сделок: {len(good_deals)}")
            return good_deals

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга: {e}")
            return []

    def _check_real_captcha_block(self):
        """Быстрая проверка на реальную блокировку"""
        try:
            page_title = self.driver.title.lower()

            # Только явные признаки
            blocking_indicators = [
                "подозрительная активность",
                "проблемы с ip",
                "доступ ограничен",
                "автоматические запросы",
                "вы робот",
                "подтвердите что вы не робот"
            ]

            for indicator in blocking_indicators:
                if indicator in page_title:
                    self.logger.warning(f"🚨 РЕАЛЬНАЯ блокировка: '{indicator}'")
                    return True

            # Проверка URL
            page_url = self.driver.current_url.lower()
            if "blocked" in page_url or "robot" in page_url:
                self.logger.warning(f"🚨 URL блокировки: {page_url}")
                return True

            return False

        except Exception as e:
            self.logger.debug(f"⚠️ Ошибка проверки блокировки: {e}")
            return False

    async def _handle_captcha_situation(self):
        """Обработка капчи - отправка уведомления один раз"""
        try:
            if hasattr(self, '_captcha_notification_sent') and self._captcha_notification_sent:
                self.logger.info("⚠️ Уведомление уже отправлено")
                return True

            self.logger.error("🚨 ОБНАРУЖЕНА КАПЧА!")
            await self._send_captcha_notification()
            self._captcha_notification_sent = True
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки капчи: {e}")
            return False

    async def _send_captcha_notification(self):
        """Отправка уведомления в Telegram"""
        try:
            from telegram import Bot
            from shared.utils.config import get_bot_token, get_chat_id

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                self.logger.error("❌ Нет токена или chat_id")
                return False

            bot = Bot(token=token)
            message = (
                "🚨 <b>ПАРСЕР ОСТАНОВЛЕН!</b>\n\n"
                "Обнаружена капча или блокировка по IP!\n\n"
                "⚡ <b>Что делать:</b>\n"
                "1. Откройте браузер с Avito\n"
                "2. Решите капчу вручную\n"
                "3. Дождитесь разблокировки\n"
                "4. Перезапустите парсер"
            )

            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            self.logger.info("✅ Уведомление отправлено")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки: {e}")
            return False

    async def _find_all_items(self):
        """Быстрый поиск товаров с основными селекторами"""
        items = []
        selectors = [
            '[data-marker="item"]',
            '.iva-item-root-_lk9K'
        ]

        for selector in selectors:
            try:
                found_items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if found_items:
                    items = found_items
                    self.logger.debug(f"✅ Найдено с '{selector}': {len(items)}")
                    break
            except:
                continue
        return items

    def _parse_search_query(self, query):
        """Парсинг запроса на ключевые слова"""
        cleaned_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = cleaned_query.split()
        stop_words = {'для', 'от', 'в', 'на', 'с', 'по', 'из', 'у', 'о', 'об', 'бу', 'б/у'}

        keywords = [word.strip() for word in words
                    if (word.strip() and word.strip() not in stop_words and len(word.strip()) > 1)]

        if not keywords:
            keywords = [word for word in words if len(word) > 1]

        return keywords

    def _check_relevance(self, product, search_keywords, original_query):
        """Быстрая проверка релевантности"""
        title = product['name'].lower()
        original_query_lower = original_query.lower()

        if original_query_lower in title:
            return "exact"

        if search_keywords:
            matched_keywords = sum(1 for keyword in search_keywords if keyword in title)
            match_percentage = matched_keywords / len(search_keywords)
            if match_percentage >= 0.5:
                return "exact"
            elif match_percentage >= 0.3:
                return "partial"

        return "other"

    async def parse_item_advanced(self, item, category):
        """Оптимизированный парсинг товара"""
        try:
            title = self._extract_title(item)
            if not title:
                return None

            price = self._extract_price(item)
            if price <= 0:
                return None

            link, item_id = self._extract_link_and_id(item)
            if not link:
                return None

            target_price = self._calculate_target_price(price)
            time_listed = self._parse_time_listed(item)

            freshness_score = await self.analyze_listing_freshness(item, {
                'name': title,
                'price': price,
                'time_listed': time_listed
            })

            return {
                'name': title[:200],
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
                'site': 'avito',
                'city': self.city
            }

        except Exception as e:
            self.logger.debug(f"❌ Ошибка парсинга товара: {e}")
            return None

    def _extract_title(self, item):
        """Извлечение заголовка"""
        title_selectors = [
            '[data-marker="item-title"]',
            '.iva-item-titleStep-_CxvN',
            'h3[itemprop="name"]'
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
        """Извлечение цены"""
        price_selectors = [
            '[data-marker="item-price"]',
            '.price-price-_P9LN',
            '[itemprop="price"]'
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
        """Извлечение ссылки и ID"""
        link_selectors = [
            '[data-marker="item-title"]',
            '.iva-item-titleStep-_CxvN a'
        ]

        for selector in link_selectors:
            try:
                link_elem = item.find_element(By.CSS_SELECTOR, selector)
                link = link_elem.get_attribute('href')
                if link and 'avito.ru' in link:
                    item_id = self._extract_item_id_from_url(link)
                    if item_id:
                        return link, item_id
            except:
                continue

        return None, None

    def _extract_item_id_from_url(self, url):
        """Извлечение ID из URL"""
        try:
            patterns = [
                r'avito\.ru/.+/(\d{9,10})(?:\?|$)',
                r'avito\.ru/.+/.+_(\d{9,10})(?:\?|$)',
                r'avito\.ru/items/(\d{9,10})(?:\?|$)',
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    item_id = match.group(1)
                    if item_id.isdigit() and 9 <= len(item_id) <= 10:
                        return int(item_id)

            return None

        except Exception as e:
            self.logger.debug(f"❌ Ошибка извлечения ID: {e}")
            return None

    def _calculate_target_price(self, price):
        """Расчет целевой цены"""
        return price

    def _detect_fresh_listing_indicators(self, item_element):
        """Обнаружение свежести"""
        try:
            for indicator in self.freshness_indicators:
                try:
                    elements = item_element.find_elements(By.CSS_SELECTOR, indicator)
                    if elements:
                        return True
                except:
                    continue

            item_text = item_element.text.lower()
            freshness_keywords = ['только что', 'сегодня', 'свежий', 'новый']

            for keyword in freshness_keywords:
                if keyword in item_text:
                    return True

            return False

        except:
            return False

    def _parse_time_listed(self, item_element):
        """Парсинг времени публикации"""
        try:
            time_selectors = [
                '[data-marker="item-date"]',
                '.iva-item-dateStep-__qB8a',
                '.styles_remainingTime__P_aaq'
            ]

            for selector in time_selectors:
                try:
                    time_elements = item_element.find_elements(By.CSS_SELECTOR, selector)
                    if time_elements:
                        time_text = time_elements[0].text.lower().strip()
                        return self._parse_time_text(time_text)
                except:
                    continue

            return 24.0

        except:
            return 24.0

    def _parse_time_text(self, time_text):
        """Парсинг текста времени"""
        try:
            if 'только что' in time_text:
                return 0.1
            elif 'минут' in time_text:
                minutes_match = re.search(r'(\d+)\s*минут', time_text)
                if minutes_match:
                    minutes = int(minutes_match.group(1))
                    return max(minutes / 60.0, 0.1)
                return 0.5
            elif 'час' in time_text:
                hours_match = re.search(r'(\d+)\s*час', time_text)
                if hours_match:
                    return float(hours_match.group(1))
                return 1.0
            elif 'сегодня' in time_text:
                return 6.0
            elif 'вчера' in time_text:
                return 24.0
            elif 'день' in time_text or 'дн' in time_text:
                days_match = re.search(r'(\d+)\s*(день|дн|дня)', time_text)
                if days_match:
                    days = int(days_match.group(1))
                    return days * 24.0
                return 24.0
            else:
                numbers_match = re.search(r'(\d+)', time_text)
                if numbers_match:
                    number = int(numbers_match.group(1))
                    if number < 24:
                        return float(number)
                    elif number < 100:
                        return number * 24.0

                return 48.0

        except:
            return 24.0

    async def analyze_listing_freshness(self, item_element, product_data):
        """Анализ свежести"""
        try:
            is_fresh_by_indicators = self._detect_fresh_listing_indicators(item_element)
            time_listed = product_data.get('time_listed', 24)

            freshness_score = self._calculate_freshness_score(time_listed, is_fresh_by_indicators)
            return freshness_score

        except:
            return 0.3

    def _calculate_freshness_score(self, time_listed, has_indicators):
        """Расчет score свежести"""
        try:
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

            if has_indicators:
                base_score += 0.15

            return min(max(base_score, 0.0), 1.0)

        except:
            return 0.5

    async def get_product_details(self, product):
        """Основной метод получения деталей товара"""
        try:
            if not product.get('url'):
                return product

            if not product.get('item_id'):
                item_id = self._extract_item_id_from_url(product['url'])
                if item_id:
                    product['item_id'] = item_id
                    product['product_id'] = item_id

            self.logger.info(f"🔍 Детали товара ID {product.get('product_id')}")
            self.driver.get(product['url'])
            time.sleep(1.5)  # Увеличил для полной загрузки страницы

            # Парсим основные данные
            condition = self._extract_condition()
            color = self._extract_color_from_details()
            location_data = self._extract_location_details_improved()
            seller_info = await self._extract_seller_info_with_avatar()

            # 🔥 🔥 🔥 ВАЖНОЕ ИСПРАВЛЕНИЕ: Добавляем парсинг КАТЕГОРИИ из старого парсера
            avito_category = self._extract_category()

            # 🔥 🔥 🔥 ВОССТАНАВЛИВАЕМ ИСПОЛЬЗОВАНИЕ ImageProcessor!
            # ОБЯЗАТЕЛЬНО используем ImageProcessor - он уже умеет собирать все фото!
            try:
                # Сначала пробуем основной метод
                self.logger.info("📸 Используем ImageProcessor для сбора ВСЕХ фото...")
                image_urls = self.image_processor.get_avito_images()

                if not image_urls or len(image_urls) == 0:
                    self.logger.warning("⚠️ Основной метод не собрал фото, пробуем альтернативный")
                    # Пробуем альтернативный метод
                    image_urls = self.image_processor.get_avito_images_fast()

                if not image_urls:
                    self.logger.error("❌ ImageProcessor не собрал ни одного фото!")
                    image_urls = []

            except Exception as e:
                self.logger.error(f"❌ Ошибка ImageProcessor: {e}")
                image_urls = []

            main_image_url = image_urls[0] if image_urls else None

            # 🔥 🔥 🔥 ВАЖНОЕ ИСПРАВЛЕНИЕ: Восстанавливаем полное извлечение описания!
            description = self._extract_description_full()

            # Извлекаем дополнительную информацию
            try:
                seller_name = seller_info.get('seller_name') or self._extract_seller_name()
                seller_rating, reviews_count = self._extract_seller_rating()
                city = self._extract_city()
                posted_date = self.extract_posted_date()
                views_data = self._extract_views_count()

                # 🔥 ОБНОВЛЯЕМ ПРОДУКТ С ПОЛНЫМ ОПИСАНИЕМ И КАТЕГОРИЕЙ
                product.update({
                    'description': description,
                    'seller_name': seller_name or 'Не указан',
                    'seller_rating': seller_rating,
                    'reviews_count': reviews_count or 0,
                    'avito_category': avito_category or product.get('category', 'Не указана'),
                    # 🔥 ДОБАВЛЕНО КАТЕГОРИЯ!
                    'city': city or self.city,
                    'image_url': main_image_url,
                    'image_urls': image_urls,
                    'posted_date': posted_date or 'Дата не указана',
                    'views_count': views_data.get('total_views', 0),
                    'views_today': views_data.get('today_views', 0),
                    'parsed_at': time.time(),
                    'metro_stations': location_data['metro_stations'],
                    'address': location_data['address'],
                    'full_location': location_data['full_location'],
                    'color': color,
                    'condition': condition,
                    'seller_avatar': seller_info.get('seller_avatar'),
                    'seller_type': seller_info.get('seller_type', 'Не указан'),
                    'seller_profile_url': seller_info.get('seller_profile_url'),
                })

                self.logger.info(
                    f"✅ Детали получены: {product.get('name', '')[:50]}... | Фото: {len(image_urls)} шт | Категория: {avito_category} | Описание: {len(description)} симв.")

            except Exception as e:
                self.logger.error(f"❌ Ошибка деталей: {e}")

            return product

        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки товара: {e}")
            return product

    def _extract_image_urls_from_element(self, element):
        """Извлекает все возможные URL изображений из элемента"""
        urls = []
        try:
            # Атрибут src
            src = element.get_attribute('src')
            if src:
                urls.append(src)

            # Data атрибуты
            for attr in ['data-src', 'data-url', 'data-original', 'data-large', 'data-image', 'data-img']:
                data_url = element.get_attribute(attr)
                if data_url:
                    urls.append(data_url)

            # Атрибут href (для ссылок)
            href = element.get_attribute('href')
            if href and self._is_avito_image_url(href):
                urls.append(href)

            # Стиль с background-image
            style = element.get_attribute('style')
            if style and 'background-image' in style:
                match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                if match:
                    urls.append(match.group(1))

            # HTML содержимое
            html = element.get_attribute('outerHTML')
            if html:
                # Ищем URL в HTML
                html_urls = re.findall(r'https?://[^"\'\s<>]*avito\.st[^"\'\s<>]*', html)
                urls.extend(html_urls)

        except Exception as e:
            self.logger.debug(f"❌ Ошибка извлечения URL из элемента: {e}")

        return [url for url in urls if url and self._is_avito_image_url(url)]

    def _is_avito_image_url(self, url):
        """Проверяет, является ли URL изображением Avito"""
        if not url:
            return False

        url_lower = url.lower()

        # Проверяем домены Avito
        avito_domains = [
            'avito.st',
            'img.avito.st',
            'avatars.mds.yandex.net',
            'stub_avatars',
            'i.mycdn.me',
            'avatars.yandex.net'
        ]

        # Проверяем расширения изображений
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

        # Проверяем по доменам
        is_avito_domain = any(domain in url_lower for domain in avito_domains)

        # Проверяем по расширениям
        is_image_extension = any(url_lower.endswith(ext) for ext in image_extensions)

        # Также проверяем на наличие типичных паттернов Avito
        has_avito_pattern = any(pattern in url_lower for pattern in ['/image/', '/images/', '/get-image/', 'image/1/'])

        return is_avito_domain or (is_image_extension and has_avito_pattern)

    def _normalize_image_url(self, url):
        """Нормализует URL изображения"""
        if not url:
            return None

        # Убираем начальные пробелы
        url = url.strip()

        # Добавляем протокол если нужно
        if url.startswith('//'):
            url = 'https:' + url

        # Убираем параметры запроса для получения чистого URL
        if '?' in url:
            url = url.split('?')[0]

        # Убираем лишние символы в конце
        url = url.rstrip('"\'')

        # Преобразуем миниатюры в полноразмерные если возможно
        if any(pattern in url for pattern in ['64x64', '80x80', '100x100']):
            url = re.sub(r'\d+x\d+', '1280x960', url)

        return url

    def _check_captcha_page(self):
        """Проверка капчи на странице товара"""
        try:
            page_title = self.driver.title.lower()
            page_url = self.driver.current_url.lower()

            critical_indicators = [
                "подозрительная активность",
                "проблемы с ip",
                "доступ ограничен",
                "автоматические запросы",
                "вы робот",
                "подтвердите что вы не робот"
            ]

            for indicator in critical_indicators:
                if indicator in page_title:
                    self.logger.warning(f"🚨 Капча в заголовке: '{indicator}'")
                    return True

            if "blocked" in page_url or "captcha" in page_url:
                self.logger.warning(f"🚨 URL капчи: {page_url}")
                return True

            return False

        except Exception as e:
            self.logger.debug(f"❌ Ошибка проверки капчи: {e}")
            return False

    def _extract_condition(self):
        """Парсит только параметр 'Состояние' из характеристик"""
        try:
            self.logger.info("🔍 Поиск параметра 'Состояние' в характеристиках...")

            params_selectors = [
                '[data-marker="item-view/item-params"]',
                '.params__paramsList__item___XzY3MG',
                '[class*="params__paramsList"]',
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

    def _extract_color_from_details(self):
        """Оптимизированный поиск цвета"""
        try:
            params_selectors = [
                '[data-marker="item-view/item-params"]',
                '.params__paramsList___XzY3MG'
            ]

            for selector in params_selectors:
                try:
                    params_blocks = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for block in params_blocks:
                        color = self._find_color_in_params_block(block)
                        if color and color != "Разноцветный":
                            return color
                except:
                    continue

            return "Разноцветный"

        except Exception as e:
            self.logger.debug(f"❌ Ошибка цвета: {e}")
            return "Разноцветный"

    def _find_color_in_params_block(self, block):
        """Поиск цвета в блоке параметров"""
        try:
            item_elements = block.find_elements(By.CSS_SELECTOR, '.params__paramsList__item___XzY3MG')

            for item in item_elements:
                item_text = item.text.strip()
                if 'Цвет' in item_text:
                    separators = [':', ' ']
                    for separator in separators:
                        if f'Цвет{separator}' in item_text:
                            parts = item_text.split(f'Цвет{separator}')
                            if len(parts) > 1:
                                value = parts[1].strip()
                                if value:
                                    return self._normalize_color_name(value)

                    if 'Цвет' in item_text and not any(sep in item_text for sep in [':', ' ']):
                        value = item_text.replace('Цвет', '').strip()
                        if value:
                            return self._normalize_color_name(value)

            return None

        except:
            return None

    def _normalize_color_name(self, color_text):
        """Нормализация названия цвета"""
        if not color_text:
            return "Разноцветный"

        color_text = color_text.strip().lower()

        color_mapping = {
            'черный': 'Черный', 'чёрный': 'Черный',
            'белый': 'Белый', 'красный': 'Красный',
            'синий': 'Синий', 'зеленый': 'Зеленый',
            'зелёный': 'Зеленый', 'желтый': 'Желтый',
            'жёлтый': 'Желтый', 'оранжевый': 'Оранжевый',
            'фиолетовый': 'Фиолетовый', 'розовый': 'Розовый',
            'коричневый': 'Коричневый', 'серый': 'Серый',
            'голубой': 'Голубой', 'бирюзовый': 'Бирюзовый',
            'бежевый': 'Бежевый', 'бордовый': 'Бордовый',
            'золотой': 'Золотой', 'серебряный': 'Серебряный',
            'серебристый': 'Серебряный'
        }

        if color_text in color_mapping:
            return color_mapping[color_text]

        for key, value in color_mapping.items():
            if key in color_text:
                return value

        if color_text and len(color_text) < 30:
            return color_text.capitalize()

        return "Разноцветный"

    def _extract_location_details_improved(self):
        """УЛУЧШЕННЫЙ метод извлечения деталей местоположения из старого парсера"""
        try:
            location_data = {
                'metro_stations': [],
                'address': None,
                'full_location': None
            }

            self._find_location_on_main_page(location_data)

            if not location_data['metro_stations'] or not location_data['address']:
                if self._expand_location_map_improved():
                    time.sleep(1.0)  # Уменьшено с 3 до 1
                    self._find_location_after_map_expansion_improved(location_data)

            if not location_data['metro_stations']:
                self._find_metro_in_expanded_card(location_data)

            self._build_final_location_improved(location_data)

            # ✅ ТОЛЬКО ИТОГОВЫЙ ЛОГ
            metro_count = len(location_data['metro_stations'])
            if metro_count > 0:
                station_names = [station['name'] for station in location_data['metro_stations']]
                self.logger.info(f"📍 Найдено метро: {', '.join(station_names[:3])}" +
                                 (f" и ещё {metro_count - 3}" if metro_count > 3 else ""))

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

            return result

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

                                try:
                                    button.click()
                                    self.logger.info("✅ Клик по кнопке выполнен")
                                    return True
                                except:
                                    try:
                                        self.driver.execute_script("arguments[0].click();", button)
                                        self.logger.info("✅ Клик по кнопке выполнен через JavaScript")
                                        return True
                                    except:
                                        try:
                                            ActionChains(self.driver).move_to_element(button).click().perform()
                                            self.logger.info("✅ Клик по кнопке выполнен через ActionChains")
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
            time.sleep(0.5)  # Уменьшено с 2 до 0.5

            address_card_selectors = [
                '[data-marker="sellerAddressInfoCard"]',
            ]

            for selector in address_card_selectors:
                try:
                    address_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for card in address_cards:
                        try:
                            card_text = card.text.strip()
                            if card_text:
                                self._parse_location_card_content_improved(card_text, location_data)
                                # Логируем результат если нашли что-то полезное
                                if location_data['address'] or location_data['metro_stations']:
                                    self.logger.info(
                                        f"📍 Найден адрес в '{selector}': {location_data['address'] or 'нет адреса'}")
                                    if location_data['metro_stations']:
                                        self.logger.info(f"🚇 Станции метро: {len(location_data['metro_stations'])}")
                                    return  # Выходим если нашли
                        except Exception as e:
                            self.logger.debug(f"❌ Ошибка анализа карточки: {e}")
                            continue

                except Exception as e:
                    self.logger.debug(f"❌ Селектор карточки '{selector}' не сработал: {e}")
                    continue

            # Если не нашли в основном селекторе, ищем альтернативно
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
                                self.logger.info(f"📍 Адрес найден альтернативно в '{selector}': '{text}'")
                                return  # Выходим если нашли адрес

                            self._extract_metro_from_text_simple(text, location_data)

                except Exception as e:
                    self.logger.debug(f"❌ Селектор после раскрытия '{selector}' не сработал: {e}")
                    continue

            if not location_data['address'] and not location_data['metro_stations']:
                self.logger.debug("📍 Адрес и метро не найдены после раскрытия карты")

        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска после раскрытия карты: {e}")

    def _find_metro_in_expanded_card(self, location_data):
        """Специализированный поиск метро в раскрытой карточке"""
        try:
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

            for line in lines:
                if 'москва,' in line.lower() and any(
                        addr_indicator in line.lower() for addr_indicator in ['ул.', 'улица', 'проспект', 'шоссе']):
                    location_data['address'] = line
                    break

            if not location_data['address']:
                for line in lines:
                    if self._is_valid_address_simple(line):
                        location_data['address'] = line
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
        try:
            parts = []

            # Добавляем метро если есть
            if location_data['metro_stations']:
                metro_names = [station['name'] for station in location_data['metro_stations']]
                metro_str = ' | '.join(metro_names[:3])  # Максимум 3 станции
                parts.append(metro_str)

            # Добавляем адрес если есть
            if location_data['address']:
                parts.append(location_data['address'])

            # Формируем итоговую строку
            if parts:
                location_data['full_location'] = ' | '.join(parts)
            else:
                location_data['full_location'] = 'Местоположение не указано'

            self.logger.info(f"📍 Итоговое местоположение: {location_data['full_location']}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка формирования местоположения: {e}")
            location_data['full_location'] = 'Местоположение не указано'

    def extract_posted_date(self):
        """УЛУЧШЕННЫЙ метод извлечения даты размещения объявления"""
        try:
            # 🔥 ШАГ 1: Основной селектор - ищем ЛЮБОЙ элемент с data-marker="item-view/item-date"
            primary_selectors = [
                '[data-marker="item-view/item-date"]',
                '*[data-marker="item-view/item-date"]',  # Все элементы с этим data-marker
            ]

            for selector in primary_selectors:
                try:
                    date_elems = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for date_elem in date_elems:
                        # 🔥 Ищем дату ВНУТРИ элемента (включая дочерние элементы)
                        date_info = self._extract_date_from_element(date_elem)
                        if date_info:
                            self.logger.info(f"✅ Дата найдена через '{selector}': '{date_info}'")
                            return date_info

                except Exception as e:
                    self.logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            # 🔥 ШАГ 2: Если не нашли, пробуем альтернативные методы
            self.logger.warning("❌ Дата не найдена в основном селекторе, ищем альтернативно")
            return 'Дата не указана'

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения даты: {e}")
            return 'Дата не указана'

    def _extract_date_from_element(self, element):
        """Извлекает дату из элемента, включая ВСЕ дочерние элементы"""
        try:
            # 🔥 Метод 1: Получаем ВЕСЬ текст элемента (включая дочерние)
            full_text = element.text.strip()
            if full_text:
                cleaned = self._clean_date_text(full_text)
                if cleaned and cleaned != 'Дата не указана':
                    return cleaned

            # 🔥 Метод 2: Проверяем ВСЕ дочерние элементы
            try:
                # Получаем ВСЕ текстовые узлы внутри элемента
                all_text_nodes = self.driver.execute_script("""
                    var texts = [];
                    var walker = document.createTreeWalker(
                        arguments[0],
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    var node;
                    while (node = walker.nextNode()) {
                        var text = node.textContent.trim();
                        if (text && text.length > 1) {
                            texts.push(text);
                        }
                    }
                    return texts;
                """, element)

                if all_text_nodes:
                    combined_text = ' '.join(all_text_nodes).strip()
                    cleaned = self._clean_date_text(combined_text)
                    if cleaned and cleaned != 'Дата не указана':
                        return cleaned
            except Exception as e:
                self.logger.debug(f"❌ Ошибка получения текстовых узлов: {e}")

            # 🔥 Метод 3: Проверяем innerHTML
            inner_html = element.get_attribute('innerHTML')
            if inner_html:
                # Убираем HTML теги, оставляем только текст
                import re
                text_only = re.sub(r'<[^>]+>', ' ', inner_html)
                text_only = ' '.join(text_only.split()).strip()

                if text_only:
                    cleaned = self._clean_date_text(text_only)
                    if cleaned and cleaned != 'Дата не указана':
                        return cleaned

            # 🔥 Метод 4: Ищем по XPath внутри элемента
            xpath_patterns = [
                ".//text()[contains(., 'сегодня') or contains(., 'вчера') or contains(., 'час') or contains(., 'минут')]",
                ".//*[contains(text(), 'сегодня') or contains(text(), 'вчера')]",
            ]

            for xpath in xpath_patterns:
                try:
                    nodes = element.find_elements(By.XPATH, xpath)
                    for node in nodes:
                        text = node.text if hasattr(node, 'text') else str(node)
                        if text:
                            cleaned = self._clean_date_text(text)
                            if cleaned and cleaned != 'Дата не указана':
                                return cleaned
                except:
                    continue

            return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения даты из элемента: {e}")
            return None

    def _clean_date_text(self, date_text):
        """Очищает текст даты от лишних символов"""
        if not date_text:
            return 'Дата не указана'

        try:
            # Убираем лишние символы в начале/конце
            cleaned = date_text.strip()

            # Убираем точки, звездочки и другие разделители в начале
            cleaned = re.sub(r'^[·•*\-–—\s]+', '', cleaned)

            # Убираем лишние пробелы
            cleaned = re.sub(r'\s+', ' ', cleaned)

            # Если начинается со слова "в" с маленькой буквы, делаем заглавной
            if cleaned.startswith('в '):
                cleaned = 'В ' + cleaned[2:]

            # Капитализируем первое слово
            if cleaned and len(cleaned) > 1:
                if cleaned[0].islower():
                    cleaned = cleaned[0].upper() + cleaned[1:]

            # Если текст слишком короткий
            if len(cleaned) < 3:
                return 'Дата не указана'

            return cleaned

        except Exception as e:
            self.logger.debug(f"❌ Ошибка очистки даты: {e}")
            return date_text.strip() if date_text else 'Дата не указана'

    def _extract_category(self):
        """🔥 🔥 🔥 ВОССТАНОВЛЕННЫЙ МЕТОД ИЗ СТАРОГО ПАРСЕРА: Извлекает категорию из навигационной цепочки"""
        try:
            self.logger.info("📊 Поиск категории товара в навигационной цепочке...")

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
                    self.logger.info(f"✅ Найден блок навигации с селектором: {selector}")
                    break
                except Exception as e:
                    self.logger.debug(f"❌ Селектор навигации '{selector}' не сработал: {e}")
                    continue

            if not navigation_element:
                self.logger.warning("⚠️ Не найден блок навигации для извлечения категории")
                return None

            try:
                links = navigation_element.find_elements(By.TAG_NAME, 'a')
                breadcrumbs = []
                for link in links:
                    try:
                        text = link.text.strip()
                        if text and text not in ['Главная', 'Avito', 'Все категории', '']:
                            breadcrumbs.append(text)
                            self.logger.debug(f"🔗 Хлебная крошка: {text}")
                    except Exception as e:
                        self.logger.debug(f"❌ Ошибка извлечения текста ссылки: {e}")
                        continue

                self.logger.info(f"📊 Найдены хлебные крошки: {breadcrumbs}")

                # Логика выбора категории:
                # 1. Если есть 3 или больше элементов, берем предпоследний (обычно это подкатегория)
                # 2. Если есть 2 элемента, берем первый (главная категория)
                # 3. Если есть 1 элемент, берем его
                if len(breadcrumbs) >= 3:
                    category = breadcrumbs[-2]  # Предпоследний элемент
                    self.logger.info(f"✅ Категория найдена (предпоследний элемент): '{category}'")
                    return category
                elif len(breadcrumbs) == 2:
                    category = breadcrumbs[0]  # Первый элемент
                    self.logger.info(f"✅ Категория найдена (первый элемент): '{category}'")
                    return category
                elif len(breadcrumbs) == 1:
                    category = breadcrumbs[0]  # Единственный элемент
                    self.logger.info(f"✅ Категория найдена (единственный элемент): '{category}'")
                    return category
                else:
                    self.logger.warning("⚠️ В хлебных крошках нет текста для извлечения категории")
                    return None

            except Exception as e:
                self.logger.error(f"❌ Ошибка парсинга навигации: {e}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения категории: {e}")
            return None

    def _extract_seller_name(self):
        """Имя продавца"""
        seller_selectors = [
            '[data-marker="seller-info/name"]',
            '.seller-info-name'
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
        """Рейтинг продавца"""
        try:
            rating = None
            reviews_count = None

            rating_selectors = [
                '.seller-info-rating span',
                '[data-marker="seller-rating/score"]'
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
                '.seller-info-rating a'
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

        except:
            return None, None

    def _extract_city(self):
        """Поиск города"""
        try:
            location_selectors = [
                '[data-marker="item-view/title-address"]',
                '.style__item-address__string___XzQ5MT'
            ]

            for selector in location_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text:
                            city = self._parse_city_from_text(text)
                            if city:
                                return city
                except:
                    continue

            return self.city

        except:
            return self.city

    def _parse_city_from_text(self, text):
        """Парсинг города"""
        try:
            if not text:
                return None

            major_cities = {
                'москва': 'Москва', 'мск': 'Москва',
                'санкт-петербург': 'Санкт-Петербург', 'спб': 'Санкт-Петербург',
                'воронеж': 'Воронеж', 'казань': 'Казань',
                'екатеринбург': 'Екатеринбург', 'новосибирск': 'Новосибирск',
                'нижний новгород': 'Нижний Новгород', 'самара': 'Самара',
                'омск': 'Омск', 'челябинск': 'Челябинск',
                'ростов-на-дону': 'Ростов-на-Дону', 'уфа': 'Уфа',
                'красноярск': 'Красноярск', 'пермь': 'Пермь',
                'волгоград': 'Волгоград', 'сочи': 'Сочи',
                'пенза': 'Пенза'
            }

            text_lower = text.lower()

            for city_pattern, city_name in major_cities.items():
                if city_pattern in text_lower:
                    return city_name

            return None

        except:
            return None

    def _extract_views_count(self):
        """Просмотры"""
        try:
            views_data = {'total_views': 0, 'today_views': 0}

            total_views_selectors = [
                '[data-marker="item-view/total-views"]',
                '.style-item-views-F2T5T'
            ]

            for selector in total_views_selectors:
                try:
                    views_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in views_elements:
                        views_text = elem.text.strip()
                        if views_text and 'просмотр' in views_text.lower():
                            numbers = re.findall(r'\d+', views_text)
                            if numbers:
                                views_data['total_views'] = int(numbers[0])
                                break
                    if views_data['total_views'] > 0:
                        break
                except:
                    continue

            return views_data

        except:
            return {'total_views': 0, 'today_views': 0}

    def parse_price(self, price_text):
        """Парсинг цены"""
        try:
            digits = ''.join(filter(str.isdigit, price_text))
            return int(digits) if digits else 0
        except:
            return 0

    async def parse_product_item(self, item_element, query=None):
        """Парсинг товара"""
        try:
            product_data = await self.parse_item_advanced(item_element, query)
            if not product_data:
                return None

            freshness_score = await self.analyze_listing_freshness(item_element, product_data)
            product_data['freshness_score'] = freshness_score
            product_data['is_fresh_by_indicators'] = self._detect_fresh_listing_indicators(item_element)

            return product_data

        except:
            return None

    async def parse_item(self, item, category):
        """Абстрактный метод"""
        return await self.parse_product_item(item, category)

    async def _extract_seller_info_with_avatar(self):
        """Извлекает информацию о продавце с аватаркой - ОПТИМИЗИРОВАННЫЙ ВАРИАНТ"""
        try:
            self.logger.info("🔍 Поиск информации о продавце...")

            seller_info = {
                'seller_name': 'Не указан',
                'seller_type': 'Не указан',
                'seller_avatar': None,
                'seller_profile_url': None
            }

            # 🔥 ПРОСТОЙ поиск аватарки
            avatar_selectors = [
                '.style__seller-info-shop-img___XzY4OG',
                '.style__seller-info-avatar-image___XzY4OG',
            ]

            for selector in avatar_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        # Способ 1: атрибут src
                        avatar_url = element.get_attribute('src')
                        if avatar_url and self._is_valid_avatar_url(avatar_url):
                            seller_info['seller_avatar'] = self._normalize_avatar_url(avatar_url)
                            self.logger.info(f"✅ Аватарка найдена через src: {seller_info['seller_avatar'][:50]}...")
                            break

                        # Способ 2: background-image в style
                        style_attr = element.get_attribute('style')
                        if style_attr and 'background-image' in style_attr:
                            match = re.search(r'url\(["\']?(.*?)["\']?\)', style_attr)
                            if match:
                                avatar_url = match.group(1)
                                if self._is_valid_avatar_url(avatar_url):
                                    seller_info['seller_avatar'] = self._normalize_avatar_url(avatar_url)
                                    self.logger.info(
                                        f"✅ Аватарка найдена через style: {seller_info['seller_avatar'][:50]}...")
                                    break

                        # Способ 3: computed style через JS
                        try:
                            bg_image = self.driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).getPropertyValue('background-image');",
                                element
                            )
                            if bg_image and bg_image != 'none':
                                match = re.search(r'url\(["\']?(.*?)["\']?\)', bg_image)
                                if match:
                                    avatar_url = match.group(1)
                                    if self._is_valid_avatar_url(avatar_url):
                                        seller_info['seller_avatar'] = self._normalize_avatar_url(avatar_url)
                                        self.logger.info(
                                            f"✅ Аватарка найдена через computed style: {seller_info['seller_avatar'][:50]}...")
                                        break
                        except:
                            pass

                    if seller_info['seller_avatar']:
                        break

                except:
                    continue

            if not seller_info['seller_avatar']:
                self.logger.info("ℹ️ Аватарка не найдена")

            # Имя продавца
            name_selectors = [
                '[data-marker="seller-info/name"]',
                '.seller-info-name',
                '.style__seller-info-name___XzY4OG',
                '[class*="seller-name"]',
                'h3[class*="seller"]'
            ]

            for selector in name_selectors:
                try:
                    name_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    seller_name = name_elem.text.strip()
                    if seller_name and seller_name != 'Частное лицо':
                        seller_info['seller_name'] = seller_name
                        self.logger.info(f"✅ Имя продавца найдено: '{seller_name}'")
                        break
                except:
                    continue

            # Тип продавца
            try:
                seller_text = self.driver.page_source.lower()
                if 'частное лицо' in seller_text:
                    seller_info['seller_type'] = "Частное лицо"
                    self.logger.info("✅ Тип продавца: Частное лицо")
                elif any(word in seller_text for word in
                         ['компания', 'фирма', 'организация', 'магазин', 'интернет-магазин']):
                    seller_info['seller_type'] = "Компания"
                    self.logger.info("✅ Тип продавца: Компания")
                else:
                    # Дополнительная проверка по наличию слов "профиль компании" или "магазин"
                    seller_text_raw = self.driver.page_source
                    if 'профиль компании' in seller_text_raw or 'магазин' in seller_text_raw.lower():
                        seller_info['seller_type'] = "Компания"
                        self.logger.info("✅ Тип продавца: Компания (по ключевым словам)")
                    else:
                        seller_info['seller_type'] = "Не определен"
                        self.logger.info("ℹ️ Тип продавца не определен")
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка определения типа продавца: {e}")
                seller_info['seller_type'] = "Не определен"

            # Ссылка на профиль продавца
            seller_profile_url = await self._extract_seller_profile_url()
            if seller_profile_url:
                seller_info['seller_profile_url'] = seller_profile_url
                self.logger.info(f"✅ Ссылка на профиль продавца найдена: {seller_profile_url[:80]}...")
            else:
                self.logger.info("ℹ️ Ссылка на профиль продавца не найдена")

            # Краткий итог
            if seller_info['seller_name'] != 'Не указан':
                self.logger.info(f"📊 Итог по продавцу: {seller_info['seller_name']} ({seller_info['seller_type']})")
            else:
                self.logger.info("📊 Информация о продавце собрана")

            return seller_info

        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка извлечения информации о продавце: {e}")
            return {
                'seller_name': 'Не указан',
                'seller_type': 'Не определен',
                'seller_avatar': None,
                'seller_profile_url': None
            }

    async def _extract_seller_profile_url(self):
        """🔥 Извлекает ссылку на профиль продавца (добавлено из старого парсера)"""
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

    def _is_valid_avatar_url(self, url):
        """Проверка аватарки"""
        if not url:
            return False
        return 'avito.st/image/1/1.' in url or 'stub_avatars' in url

    def _normalize_avatar_url(self, url):
        """Нормализация URL"""
        if not url:
            return None
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return 'https://www.avito.ru' + url
        return url

    def _extract_description_full(self):
        """Извлекает полное описание товара с минимальными логами"""
        try:
            # Попытка нажать кнопку "Читать полностью"
            read_more_selectors = [
                '//a[contains(text(), "Читать полностью")]',
                '//button[contains(text(), "Читать полностью")]',
                '[data-marker="item-description/expand"]',
            ]

            for selector in read_more_selectors:
                try:
                    if selector.startswith('//'):
                        buttons = self.driver.find_elements(By.XPATH, selector)
                    else:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for button in buttons:
                        try:
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(0.5)
                            break
                        except:
                            continue
                    break
                except:
                    continue

            # Поиск описания
            description_selectors = [
                '[data-marker="item-view/item-description"]',
                '.item-description-text',
                '[itemprop="description"]',
            ]

            description = None
            selector_used = None

            for selector in description_selectors:
                try:
                    desc_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for desc_elem in desc_elements:
                        desc_text = desc_elem.text.strip()
                        if desc_text and len(desc_text) > 10:
                            description = desc_text
                            selector_used = selector
                            break
                    if description:
                        break
                except:
                    continue

            # Если не нашли обычное описание, ищем HTML-версию
            if not description:
                html_selectors = [
                    '.style__item-description-html___XzQzYT',
                    '[data-marker="item-view/item-description-html"]',
                ]

                for selector in html_selectors:
                    try:
                        html_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for html_elem in html_elements:
                            html_content = html_elem.get_attribute('innerHTML')
                            if html_content:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html_content, 'html.parser')
                                for br in soup.find_all("br"):
                                    br.replace_with("\n")
                                text_content = soup.get_text(separator='\n', strip=False)
                                if text_content and len(text_content) > 10:
                                    description = text_content.strip()
                                    selector_used = "HTML"
                                    break
                        if description:
                            break
                    except:
                        continue

            # Если всё еще не нашли, ищем в родительских блоках
            if not description:
                parent_selectors = [
                    '#bx_item-description',
                    '.style__item-description___XzQzYT',
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
                                    selector_used = "parent_block"
                                    break
                        if description:
                            break
                    except:
                        continue

            # Логирование результата
            if description:
                if selector_used == "HTML":
                    self.logger.info(f"✅ Описание из HTML: {len(description)} символов")
                elif selector_used == "parent_block":
                    self.logger.info(f"✅ Описание из блока: {len(description)} символов")
                else:
                    self.logger.info(f"✅ Описание: {len(description)} символов")
                return description
            else:
                self.logger.info("ℹ️ Описание не найдено")
                return "Описание отсутствует"

        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка извлечения описания: {e}")
            return "Описание отсутствует"