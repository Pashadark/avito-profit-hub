# sites/auto_ru_parser.py
import re
import time
import logging
from urllib.parse import quote, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from typing import Dict, Any, List
from .base_site_parser import BaseSiteParser
from ..utils.product_validator import ProductValidator
from ..utils.image_processor import ImageProcessor
from ..utils.moscow_metro import MOSCOW_METRO_DATABASE

logger = logging.getLogger('parser.auto_ru')


class AutoRuParser(BaseSiteParser):
    """Парсер для Auto.ru с полным извлечением данных и фото"""

    def __init__(self, driver):
        super().__init__(driver)
        self.base_url = "https://auto.ru"
        self.name = "auto.ru"
        self.validator = ProductValidator()
        self.image_processor = ImageProcessor(driver)

        # 🔥 ДОБАВЛЯЕМ БАЗУ МЕТРО КАК В AVITO ПАРСЕРЕ
        self.metro_database = MOSCOW_METRO_DATABASE

        # 🔥 ДОБАВЛЯЕМ ССЫЛКУ НА ОСНОВНОЙ ПАРСЕР
        self._main_parser = None

        # 🔥 Флаг капчи
        self._captcha_notification_sent = False

        logger.info("🚗 AutoRuParser инициализирован с полным функционалом")

    def set_main_parser(self, main_parser):
        """🔥 Устанавливает ссылку на основной парсер для передачи данных"""
        self._main_parser = main_parser
        logger.info("✅ AutoRuParser: установлена связь с основным парсером")

    async def parse_search_results(self, query):
        """Парсит результаты поиска на Auto.ru с приоритетом по точному соответствию"""
        try:
            # 🔥 СБРАСЫВАЕМ ФЛАГ КАПЧИ
            self._captcha_notification_sent = False

            clean_query = self._clean_query_for_auto_ru(query)
            search_url = self._build_search_url(clean_query)

            logger.info(f"🌐 Загружаем страницу поиска Auto.ru: {search_url}")
            self.driver.get(search_url)

            # 🔥 ПРОВЕРКА КАПЧИ
            time.sleep(2)
            if self._check_real_captcha_block():
                await self._handle_captcha_situation()
                return []

            await self._wait_for_page_load()
            await self._scroll_page()

            items = await self._find_all_car_items()

            if not items:
                logger.warning("❌ Не найдено машин на странице Auto.ru")
                return []

            logger.info(f"🔍 Анализируем {len(items)} машин по запросу: '{query}'")

            # Разделяем запрос на ключевые слова
            search_keywords = self._parse_search_query(query)
            logger.info(f"📝 Ключевые слова для поиска: {search_keywords}")

            products = []
            exact_match_products = []  # Точное соответствие
            partial_match_products = []  # Частичное соответствие
            other_products = []  # Остальные машины

            for item in items[:15]:  # Ограничиваем для производительности
                try:
                    product = await self.parse_item_advanced(item, query)
                    if product:
                        # Проверяем релевантность
                        relevance_type = self._check_relevance(product, search_keywords, query)

                        if relevance_type == "exact":
                            exact_match_products.append(product)
                            logger.info(f"🎯 ТОЧНОЕ СООТВЕТСТВИЕ: {product['name']}")
                        elif relevance_type == "partial":
                            partial_match_products.append(product)
                            logger.info(f"✅ Частичное соответствие: {product['name']}")
                        else:
                            other_products.append(product)

                except Exception as e:
                    logger.error(f"❌ Ошибка парсинга элемента: {e}")
                    continue

            # 🔥 СОБИРАЕМ ВСЕ ТОВАРЫ
            final_products = []

            if exact_match_products:
                final_products.extend(exact_match_products)
                logger.info(f"✅ Добавлено {len(exact_match_products)} машин с точным соответствием")

            if partial_match_products:
                final_products.extend(partial_match_products)
                logger.info(f"✅ Добавлено {len(partial_match_products)} машин с частичным соответствием")

            if other_products:
                final_products.extend(other_products)
                logger.info(f"✅ Добавлено {len(other_products)} других машин")

            # 🔥 ПЕРЕХОДИМ В КАРТОЧКИ ДЛЯ ПОЛУЧЕНИЯ ПОЛНЫХ ДАННЫХ
            detailed_products = []
            for product in final_products[:10]:  # Ограничиваем для производительности
                try:
                    detailed_product = await self.get_product_details(product)
                    if detailed_product and self.validator.is_good_deal(detailed_product):
                        detailed_products.append(detailed_product)
                        logger.info(f"✅ Детальная информация получена: {detailed_product['name']}")
                    else:
                        logger.info(f"❌ Отфильтрована машина: {product['name']}")
                except Exception as e:
                    logger.error(f"❌ Ошибка получения деталей: {e}")
                    continue

            logger.info(f"🎯 Итоговый результат: {len(detailed_products)} хороших машин")
            return detailed_products

        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга Auto.ru: {e}")
            return []

    def _check_real_captcha_block(self):
        """Проверяет реальные случаи блокировки"""
        try:
            page_title = self.driver.title.lower()
            page_url = self.driver.current_url

            logger.info(f"🔍 Проверка на реальную блокировку. Заголовок: {page_title}")

            # 🔥 ТОЛЬКО ЯВНЫЕ ПРИЗНАКИ БЛОКИРОВКИ
            blocking_indicators = [
                "подозрительная активность",
                "проблемы с ip",
                "доступ ограничен",
                "автоматические запросы",
                "вы робот",
                "подтвердите что вы не робот",
                "капча"
            ]

            for indicator in blocking_indicators:
                if indicator in page_title:
                    logger.warning(f"🚨 РЕАЛЬНАЯ блокировка: '{indicator}'")
                    return True

            if "blocked" in page_url or "robot" in page_url:
                logger.warning(f"🚨 URL указывает на блокировку: {page_url}")
                return True

            # 🔥 Проверяем наличие ВИДИМОЙ формы капчи
            try:
                visible_captcha_elements = [
                    'div[class*="captcha"][style*="visible"]',
                    '.captcha-form',
                    '#captcha-container',
                    'form[action*="captcha"]'
                ]

                for selector in visible_captcha_elements:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.size['height'] > 50:
                            logger.warning(f"🚨 Обнаружена ВИДИМАЯ капча: {selector}")
                            return True
            except:
                pass

            # 🔥 Если страница содержит нормальный контент Auto.ru - блокировки нет
            if any(indicator in page_title for indicator in ["auto.ru", "авто.ру", "автомобили", "купить", "продать"]):
                logger.debug("✅ Страница нормальная, блокировки нет")
                return False

            logger.info("⚠️ Неясная ситуация, но продолжаем работу")
            return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки блокировки: {e}")
            return False

    async def _handle_captcha_situation(self):
        """Обрабатывает ситуацию с капчей"""
        try:
            if hasattr(self, '_captcha_notification_sent') and self._captcha_notification_sent:
                logger.info("⚠️ Уведомление о капче уже отправлено, пропускаем")
                return True

            logger.error("🚨 ПАРСЕР ОСТАНОВЛЕН! ОБНАРУЖЕНА КАПЧА НА AUTO.RU!")

            # 🔥 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ В ТЕЛЕГРАМ
            await self._send_captcha_notification()

            self._captcha_notification_sent = True
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обработки капчи: {e}")
            return False

    async def _send_captcha_notification(self):
        """Отправляет уведомление о капче в Telegram"""
        try:
            from telegram import Bot
            from shared.utils.config import get_bot_token, get_chat_id

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                logger.error("❌ Не удалось отправить уведомление о капче: нет токена или chat_id")
                return False

            bot = Bot(token=token)

            message = (
                "🚨 <b>ПАРСЕР AUTO.RU ОСТАНОВЛЕН!</b>\n\n"
                "Обнаружена капча или блокировка по IP!\n\n"
                "📝 <b>Что произошло:</b>\n"
                "• Auto.ru заподозрил автоматические запросы\n"
                "• Требуется подтверждение, что вы не робот\n"
                "• Парсер временно приостановлен\n\n"
                "⚡ <b>Что делать:</b>\n"
                "1. Откройте браузер с Auto.ru\n"
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

            logger.info("✅ Уведомление о капче отправлено в Telegram")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о капче: {e}")
            return False

    async def _find_all_car_items(self):
        """Находит все элементы с машинами"""
        selectors = [
            '.ListingCars__universalSnippetWrapper',
            '.ListingItem',
            '.ListingItemUniversal',
            '[data-ftid="bulls-list_bull"]',
            '.ListingItemVAS',
        ]

        items = []
        for selector in selectors:
            try:
                found = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if found:
                    items = found
                    logger.info(f"✅ Найдено элементов с '{selector}': {len(items)}")
                    break
            except Exception as e:
                logger.debug(f"❌ Не найдено элементов с '{selector}': {e}")
                continue

        if not items:
            logger.warning("❌ Не найдено ни одного элемента машины")
            return []

        # Фильтрация уникальных URL
        unique_items = []
        seen_urls = set()

        for item in items:
            try:
                url = await self._extract_item_url(item)
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_items.append(item)
                    logger.debug(f"🔗 Уникальный URL: {url}")
            except Exception as e:
                logger.debug(f"❌ Ошибка извлечения URL: {e}")
                continue

        logger.info(f"🔍 После фильтрации: {len(unique_items)} уникальных машин")
        return unique_items

    async def parse_item_advanced(self, item, category):
        """Парсит машину с улучшенной проверкой данных"""
        try:
            logger.debug("🔍 Извлекаем базовые данные машины...")

            title = await self._extract_title(item)
            price = await self._extract_price_basic(item)
            url = await self._extract_item_url(item)

            logger.debug(f"📝 Название: {title} | 💰 Цена: {price} | 🔗 URL: {url}")

            if not title or not url:
                logger.warning("❌ Отсутствует название или URL")
                return None

            if price <= 0:
                logger.warning("❌ Некорректная цена")
                return None

            # Базовые данные из списка
            year = await self._extract_year(item)
            mileage = await self._extract_mileage(item)
            engine_info = await self._extract_engine_info(item)
            location = await self._extract_location(item)
            photo_url = await self._extract_photo_url(item)

            target_price = self._calculate_target_price(price)

            product_data = {
                'name': title[:200],
                'price': price,
                'target_price': target_price,
                'url': url,
                'category': 'Автомобили',
                'description': self._build_basic_description(year, mileage, engine_info),
                'year': year,
                'mileage': mileage,
                'engine': engine_info,
                'location': location,
                'photo_url': photo_url,
                'posted_date': '',
                'seller_name': 'Auto.ru',
                'seller_rating': None,
                'reviews_count': 0,
                'views_count': 0,
                'site': 'auto.ru',
                'condition': 'Отличное',
                'address': location,
                'city': 'Москва',
                'avito_category': 'Автомобили',
                'image_url': photo_url,
                'image_urls': [photo_url] if photo_url else [],
                'price_status': '',
                'discount_price': 0,
                'product_id': '',
            }

            logger.debug(f"✅ Собраны базовые данные: {len(product_data)} полей")
            return product_data

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга базовых данных: {e}")
            return None

    async def get_product_details(self, product):
        """Основной метод получения детальной информации о машине"""
        try:
            if not product.get('url'):
                return product

            logger.info(f"🔍 Получаем детали машины: {product['url']}")
            self.driver.get(product['url'])

            # 🔥 ПРОВЕРКА КАПЧИ
            if self._check_real_captcha_block():
                await self._handle_captcha_situation()
                return product

            try:
                self.wait_for_element('.CardHead, .CardOfferBody', timeout=10)
                logger.info("✅ Страница машины загружена")
            except:
                logger.warning("⚠️ Не дождались полной загрузки страницы машины")

            # 🔥 ПОЛУЧАЕМ ВСЕ ДАННЫЕ ИЗ КАРТОЧКИ
            detailed_data = await self._parse_detailed_page()

            # 🔥 ОБНОВЛЯЕМ ПРОДУКТ
            product.update(detailed_data)

            # 🔥 ПОЛУЧАЕМ ВСЕ ФОТО
            all_photos = self.image_processor.get_images('auto.ru')
            if all_photos:
                product['image_urls'] = all_photos
                product['image_url'] = all_photos[0] if all_photos else product.get('image_url', '')

            # 🔥 ПОДГОТАВЛИВАЕМ ИЗОБРАЖЕНИЕ ДЛЯ TELEGRAM
            image_data = None
            if product.get('image_url'):
                try:
                    image_data = self.image_processor.download_image_to_base64(product['image_url'])
                    logger.info("✅ Изображение подготовлено для Telegram")
                except Exception as e:
                    logger.error(f"❌ Ошибка подготовки изображения: {e}")

            product['image_data'] = image_data

            # 🔥 СОХРАНЯЕМ КРАСИВЫЙ ФОРМАТ ВЫВОДА С ├──
            logger.info(f"✅ Детали машины получены!:")
            logger.info(f"├──🚗 Модель: {product.get('name')}")
            logger.info(f"├──💰 Цена: {product.get('price')}₽")
            logger.info(f"├──🏷️ Статус: {product.get('price_status', '')}")
            logger.info(f"├──🆔 ID: {product.get('product_id', '')}")
            logger.info(f"├──⭐ Рейтинг: {product.get('seller_rating', '')}")
            logger.info(f"├──📊 Отзывов: {product.get('reviews_count', 0)}")
            logger.info(f"├──👁️ Просмотры: {product.get('views_count', 0)}")
            logger.info(f"├──📅 Дата: {product.get('posted_date', '')}")
            logger.info(f"├──🖼️ Фото: {len(product.get('image_urls', []))}")
            logger.info(f"└──📝 Описание: {len(product.get('description', ''))} симв.")

            # 🔥 КРИТИЧЕСКИЙ МОМЕНТ: ПЕРЕДАЧА ДАННЫХ В ОСНОВНОЙ ПАРСЕР
            await self._transfer_to_main_parser(product)

            return product

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки страницы машины: {e}")
            return product

    async def _transfer_to_main_parser(self, product):
        """🔥 ПЕРЕДАЧА ДАННЫХ В ОСНОВНОЙ ПАРСЕР ДЛЯ СОХРАНЕНИЯ И УВЕДОМЛЕНИЙ"""
        try:
            if not self._main_parser:
                logger.warning("⚠️ AutoRuParser: _main_parser не установлен, пропускаем передачу")
                return False

            logger.info(f"🚀 AutoRuParser: ПЕРЕДАЧА ДАННЫХ В ОСНОВНОЙ ПАРСЕР: {product.get('name', 'No name')}")

            # 🔥 ПРОВЕРЯЕМ ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
            required_fields = ['name', 'price', 'url']
            for field in required_fields:
                if field not in product:
                    logger.error(f"❌ AutoRuParser: Отсутствует обязательное поле: {field}")
                    return False

            # 🔥 ПОДГОТАВЛИВАЕМ ДАННЫЕ ДЛЯ VALIDATOR - ИСПРАВЛЕНИЕ!
            if not hasattr(self._main_parser, 'product_validator'):
                logger.error("❌ AutoRuParser: product_validator не доступен")
                return False

            # 🔥 ИСПРАВЛЕНИЕ: используем правильный метод is_good_deal вместо validate_product
            validator = self._main_parser.product_validator
            is_valid = validator.is_good_deal(product)  # 🔥 ПРАВИЛЬНЫЙ МЕТОД!

            if not is_valid:
                logger.info(f"❌ AutoRuParser: Товар не прошел валидацию: {product.get('name')}")
                return False

            logger.info(f"✅ AutoRuParser: Товар прошел валидацию: {product.get('name')}")

            # 🔥 ПЕРЕДАЕМ В NOTIFICATION_SENDER
            if not hasattr(self._main_parser, 'notification_sender'):
                logger.error("❌ AutoRuParser: notification_sender не доступен")
                return False

            # 🔥 РАСЧЕТ ЭКОНОМИИ
            economy = product.get('economy', 0)
            economy_percent = product.get('economy_percent', 0)

            logger.info(f"🚀 AutoRuParser: ВЫЗОВ NotificationSender.process_and_notify для: {product.get('name')}")

            # 🔥 ВЫЗЫВАЕМ ОСНОВНОЙ МЕТОД СОХРАНЕНИЯ И УВЕДОМЛЕНИЙ
            success = await self._main_parser.notification_sender.process_and_notify(
                product, economy, economy_percent
            )

            if success:
                logger.info(f"🎉 AutoRuParser: Товар успешно сохранен и отправлен: {product.get('name')}")
            else:
                logger.error(f"❌ AutoRuParser: Ошибка сохранения/отправки товара: {product.get('name')}")

            return success

        except Exception as e:
            logger.error(f"❌ AutoRuParser: Критическая ошибка передачи данных: {e}")
            return False

    async def _parse_detailed_page(self):
        """Парсит все данные с детальной страницы включая характеристики"""
        detailed_data = {}

        try:
            # 🔥 ID ОБЪЯВЛЕНИЯ
            product_id = await self._extract_product_id()
            if product_id:
                detailed_data['product_id'] = product_id

            # 🔥 ЦЕНА И СТАТУС
            price_data = await self._extract_price_detailed()
            if price_data:
                detailed_data.update(price_data)

            # 🔥 ПОЛНОЕ ОПИСАНИЕ
            description = await self._extract_full_description()
            if description:
                detailed_data['description'] = description

            # 🔥 ДАТА РАЗМЕЩЕНИЯ
            posted_date = await self._extract_posted_date()
            if posted_date:
                detailed_data['posted_date'] = posted_date

            # 🔥 ПРОСМОТРЫ
            views_data = await self._extract_views_data()
            if views_data:
                detailed_data.update(views_data)

            # 🔥 ИНФОРМАЦИЯ О ПРОДАВЦЕ И РЕЙТИНГ
            seller_info = await self._extract_seller_info()
            if seller_info:
                detailed_data.update(seller_info)

            # 🔥 КЛЮЧЕВОЕ: ХАРАКТЕРИСТИКИ АВТОМОБИЛЯ
            car_specs = await self._extract_car_specifications()
            if car_specs:
                detailed_data.update(car_specs)

            # 🔥 ДОБАВЛЯЕМ: ИНФОРМАЦИЯ О ЛОКАЦИИ (АДРЕС И МЕТРО)
            location_data = await self._extract_location_details_auto_ru()
            if location_data:
                detailed_data.update(location_data)

            logger.info(f"✅ Извлечено {len(detailed_data)} полей с детальной страницы")

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга детальной страницы: {e}")

        return detailed_data

    async def _extract_location_details_auto_ru(self):
        """🔥 ПРАВИЛЬНЫЙ парсинг адреса и метро - ИСПОЛЬЗУЕМ HTML СТРУКТУРУ"""
        try:
            location_data = {
                'address': 'Москва',
                'metro_stations': [],
                'full_location': 'Москва'
            }

            logger.info("🔍 Поиск блока продавца для извлечения адреса и метро...")

            # 🔥 ПОИСК БЛОКА ПРОДАВЦА
            seller_selectors = [
                '.CardSellerNamePlace2',
                '.CardOwner__ownerInfo',
                '[class*="CardSeller"]',
                '[class*="CardOwner"]'
            ]

            seller_element = None
            for selector in seller_selectors:
                try:
                    seller_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Найден блок продавца: {selector}")
                    break
                except:
                    continue

            if not seller_element:
                logger.warning("❌ Не найден блок продавца")
                return location_data

            # 🔥 ИЗВЛЕКАЕМ ДАННЫЕ ПО СТРУКТУРЕ HTML
            await self._extract_metro_from_structure(seller_element, location_data)
            await self._extract_city_from_structure(seller_element, location_data)
            await self._extract_address_from_structure(seller_element, location_data)

            # 🔥 ФОРМИРУЕМ ПОЛНОЕ МЕСТОПОЖЕНИЕ
            location_data['full_location'] = self._build_full_location_auto_ru(location_data)

            logger.info(f"🗺️ Итоговые данные локации: {location_data}")
            return location_data

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения локации Auto.ru: {e}")
            return {
                'address': 'Москва',
                'metro_stations': [],
                'full_location': 'Москва'
            }

    async def _extract_metro_from_structure(self, seller_element, location_data):
        """🔥 Извлекает станции метро из структуры HTML"""
        try:
            # 🔥 ИЩЕМ ВСЕ СТАНЦИИ МЕТРО
            station_selectors = [
                '.MetroList__stationFirstName',
                '.MetroList__stationContent',
                '[class*="MetroList__station"]'
            ]

            for selector in station_selectors:
                try:
                    station_elements = seller_element.find_elements(By.CSS_SELECTOR, selector)
                    for station_element in station_elements:
                        station_name = station_element.text.strip()
                        if station_name and self._is_valid_metro_station(station_name):
                            # 🔥 ПОЛУЧАЕМ ДАННЫЕ СТАНЦИИ ИЗ БАЗЫ МЕТРО
                            metro_data = self._get_metro_data_by_station(station_name)
                            station_data = {
                                'name': station_name,
                                'color': metro_data['color'],
                                'line_number': metro_data['line_number'],
                                'line_name': metro_data['line_name'],
                                'circle_color': metro_data['circle_color']
                            }

                            # 🔥 ДОБАВЛЯЕМ ТОЛЬКО УНИКАЛЬНЫЕ СТАНЦИИ
                            if not any(s['name'] == station_name for s in location_data['metro_stations']):
                                location_data['metro_stations'].append(station_data)
                                logger.info(f"🚇 Найдена станция метро: {station_name} ({metro_data['line_name']})")

                    if location_data['metro_stations']:
                        break

                except Exception as e:
                    logger.debug(f"❌ Селектор станций '{selector}' не сработал: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения метро: {e}")

    async def _extract_city_from_structure(self, seller_element, location_data):
        """🔥 Извлекает город из структуры HTML"""
        try:
            city_selectors = [
                '.MetroListPlace__regionName',
                '[class*="regionName"]',
                '.CardSellerNamePlace2__region'
            ]

            for selector in city_selectors:
                try:
                    city_element = seller_element.find_element(By.CSS_SELECTOR, selector)
                    city = city_element.text.strip()
                    if city:
                        location_data['city'] = city
                        logger.info(f"🏙️ Найден город: {city}")
                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор города '{selector}' не сработал: {e}")
                    continue
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения города: {e}")

    async def _extract_address_from_structure(self, seller_element, location_data):
        """🔥 Извлекает адрес из структуры HTML"""
        try:
            address_selectors = [
                '.MetroListPlace__address',
                '[class*="address"]',
                '.CardSellerNamePlace2__address'
            ]

            for selector in address_selectors:
                try:
                    address_element = seller_element.find_element(By.CSS_SELECTOR, selector)
                    address = address_element.text.strip()
                    if address:
                        # 🔥 ФОРМАТИРУЕМ АДРЕС С ГОРОДОМ
                        city = location_data.get('city', 'Москва')
                        formatted_address = self._format_structured_address(address, city)
                        location_data['address'] = formatted_address
                        logger.info(f"📍 Найден адрес: {formatted_address}")
                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор адреса '{selector}' не сработал: {e}")
                    continue
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения адреса: {e}")

    def _format_structured_address(self, address, city):
        """🔥 Форматирует адрес с городом"""
        try:
            # 🔥 ЕСЛИ АДРЕС УЖЕ СОДЕРЖИТ ГОРОД, НЕ ДОБАВЛЯЕМ ЕГО СНОВА
            if city and city != 'Москва' and city not in address:
                return f"{city}, {address}"
            elif city == 'Москва' and 'Москва' not in address:
                return f"Москва, {address}"
            else:
                return address
        except:
            return address

    def _is_valid_metro_station(self, station_name):
        """🔥 Проверяет, является ли текст валидной станцией метро"""
        if not station_name or len(station_name) < 3:
            return False

        # 🔥 ПРОВЕРЯЕМ В БАЗЕ МЕТРО
        if station_name in self.metro_database:
            return True

        # 🔥 ПРОВЕРЯЕМ ПО ШАБЛОНУ (станции обычно не содержат цифр и специальных символов)
        if re.match(r'^[А-Яа-яёЁ\s\-]+$', station_name):
            return len(station_name) <= 30  # Ограничение по длине

        return False

    def _build_full_location_auto_ru(self, location_data):
        """🔥 Формирует полное местоположение для Auto.ru"""
        try:
            location_parts = []

            # 🔥 ДОБАВЛЯЕМ СТАНЦИИ МЕТРО
            if location_data['metro_stations']:
                metro_names = [station['name'] for station in location_data['metro_stations']]
                location_parts.extend(metro_names)

            # 🔥 ДОБАВЛЯЕМ АДРЕС
            if location_data['address'] and location_data['address'] != 'Москва':
                location_parts.append(location_data['address'])

            # 🔥 ФОРМИРУЕМ ИТОГОВУЮ СТРОКУ
            if location_parts:
                full_location = ' | '.join(location_parts)
                logger.info(f"📍 Полное местоположение: {full_location}")
                return full_location
            else:
                return "Москва"

        except Exception as e:
            logger.error(f"❌ Ошибка формирования местоположения: {e}")
            return "Москва"

    def _get_metro_data_by_station(self, station_name):
        """🔥 Возвращает данные станции метро из базы (как в Avito)"""
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
        """🔥 Определяет цвет кружка (белый или черный) в зависимости от цвета линии"""
        dark_lines = {'1', '2', '3', '5', '7', '8', '9', '10', '11', '12'}
        return '#000000' if line_number in dark_lines else '#ffffff'

    async def _extract_car_specifications(self):
        """🔥 Извлекает ВСЕ характеристики автомобиля из блока CardInfoSummary"""
        try:
            specs = {}

            # 🔥 ИЩЕМ ОСНОВНОЙ БЛОК С ХАРАКТЕРИСТИКАМИ
            spec_selectors = [
                '.CardInfoSummary',
                '[data-testid="cardInfoSummary"]',
                '.CardInfoRow',
                '.CardSpecifications'
            ]

            spec_element = None
            for selector in spec_selectors:
                try:
                    spec_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Найден блок характеристик: {selector}")
                    break
                except:
                    continue

            if not spec_element:
                logger.warning("❌ Не найден блок характеристик")
                return {}

            # 🔥 ИЗВЛЕКАЕМ ВСЕ ХАРАКТЕРИСТИКИ
            car_specs = {}

            # 🔥 ВЛАДЕНИЕ (год, пробег, владельцы и т.д.)
            ownership_specs = await self._extract_ownership_specs(spec_element)
            if ownership_specs:
                car_specs.update(ownership_specs)

            # 🔥 ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ
            technical_specs = await self._extract_technical_specs(spec_element)
            if technical_specs:
                car_specs.update(technical_specs)

            # 🔥 ДОПОЛНИТЕЛЬНЫЕ ХАРАКТЕРИСТИКИ
            additional_specs = await self._extract_additional_specs(spec_element)
            if additional_specs:
                car_specs.update(additional_specs)

            logger.info(f"🎯 Извлечено характеристик автомобиля: {len(car_specs)}")
            return car_specs

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения характеристик: {e}")
            return {}

    async def _extract_ownership_specs(self, spec_element):
        """🔥 Извлекает данные о владении"""
        try:
            ownership_data = {}

            # 🔥 ГОД ВЫПУСКА
            year_selectors = [
                '.CardInfoSummarySimpleRow:contains("Год выпуска") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("Год выпуска") [class*="content"]',
                '//div[contains(text(), "Год выпуска")]/following-sibling::div//a'  # XPath
            ]

            found_ownership = []

            for selector in year_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    year_text = element.text.strip()
                    if year_text and year_text.isdigit():
                        ownership_data['year'] = int(year_text)
                        found_ownership.append(f"📅 Год: {year_text}")
                        break
                except:
                    continue

            # 🔥 ПРОБЕГ
            mileage_selectors = [
                '.CardInfoSummarySimpleRow:contains("Пробег") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("Пробег") [class*="content"]',
                '//div[contains(text(), "Пробег")]/following-sibling::div'
            ]

            for selector in mileage_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    mileage_text = element.text.strip()
                    if mileage_text and 'км' in mileage_text:
                        # Очищаем текст пробега
                        clean_mileage = mileage_text.replace('&nbsp;', ' ').replace(' ', '')
                        mileage_match = re.search(r'(\d+)км', clean_mileage)
                        if mileage_match:
                            ownership_data['mileage'] = f"{mileage_match.group(1)} км"
                            found_ownership.append(f"🛣️ Пробег: {ownership_data['mileage']}")
                        break
                except:
                    continue

            # 🔥 ВЛАДЕЛЬЦЫ
            owners_selectors = [
                '.CardInfoSummarySimpleRow:contains("Владельцы") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("Владельцы") [class*="content"]',
                '//div[contains(text(), "Владельцы")]/following-sibling::div'
            ]

            for selector in owners_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    owners_text = element.text.strip()
                    if owners_text:
                        ownership_data['owners'] = owners_text
                        found_ownership.append(f"👥 Владельцы: {owners_text}")
                        break
                except:
                    continue

            # 🔥 СОСТОЯНИЕ
            condition_selectors = [
                '.CardInfoSummarySimpleRow:contains("Состояние") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("Состояние") [class*="content"]',
                '//div[contains(text(), "Состояние")]/following-sibling::div'
            ]

            for selector in condition_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    condition_text = element.text.strip()
                    if condition_text:
                        ownership_data['condition'] = condition_text
                        found_ownership.append(f"🔧 Состояние: {condition_text}")
                        break
                except:
                    continue

            # 🔥 ПТС
            pts_selectors = [
                '.CardInfoSummarySimpleRow:contains("ПТС") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("ПТС") [class*="content"]',
                '//div[contains(text(), "ПТС")]/following-sibling::div'
            ]

            for selector in pts_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    pts_text = element.text.strip()
                    if pts_text:
                        ownership_data['pts'] = pts_text
                        found_ownership.append(f"📄 ПТС: {pts_text}")
                        break
                except:
                    continue

            # 🔥 ОДИН ЛОГ ВМЕСТО НЕСКОЛЬКИХ
            if found_ownership:
                logger.info(" | ".join(found_ownership))

            return ownership_data

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения данных владения: {e}")
            return {}

    async def _extract_technical_specs(self, spec_element):
        """🔥 Извлекает технические характеристики"""
        try:
            technical_data = {}
            found_specs = []

            # 🔥 ДВИГАТЕЛЬ
            engine_selectors = [
                '.CardInfoSummaryComplexRow:contains("Двигатель") .CardInfoSummaryComplexRow__cellValue',
                '[class*="CardInfoSummaryComplexRow"]:contains("Двигатель") [class*="cellValue"]',
                '//div[contains(text(), "Двигатель")]/following-sibling::div'
            ]

            for selector in engine_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    engine_text = element.text.strip()
                    if engine_text:
                        technical_data['engine'] = engine_text
                        found_specs.append(f"⚙️ Двигатель: {engine_text}")
                        break
                except:
                    continue

            # 🔥 КОРОБКА ПЕРЕДАЧ
            transmission_selectors = [
                '.CardInfoSummaryComplexRow:contains("Коробка") .CardInfoSummaryComplexRow__cellValue',
                '[class*="CardInfoSummaryComplexRow"]:contains("Коробка") [class*="cellValue"]',
                '//div[contains(text(), "Коробка")]/following-sibling::div'
            ]

            for selector in transmission_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    transmission_text = element.text.strip()
                    if transmission_text:
                        technical_data['transmission'] = transmission_text
                        found_specs.append(f"🔧 Коробка: {transmission_text}")
                        break
                except:
                    continue

            # 🔥 ПРИВОД
            drive_selectors = [
                '.CardInfoSummaryComplexRow:contains("Привод") .CardInfoSummaryComplexRow__cellValue',
                '[class*="CardInfoSummaryComplexRow"]:contains("Привод") [class*="cellValue"]',
                '//div[contains(text(), "Привод")]/following-sibling::div'
            ]

            for selector in drive_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    drive_text = element.text.strip()
                    if drive_text:
                        technical_data['drive'] = drive_text
                        found_specs.append(f"🚗 Привод: {drive_text}")
                        break
                except:
                    continue

            # 🔥 РУЛЬ
            steering_selectors = [
                '.CardInfoSummaryComplexRow:contains("Руль") .CardInfoSummaryComplexRow__cellValue',
                '[class*="CardInfoSummaryComplexRow"]:contains("Руль") [class*="cellValue"]',
                '//div[contains(text(), "Руль")]/following-sibling::div'
            ]

            for selector in steering_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    steering_text = element.text.strip()
                    if steering_text:
                        technical_data['steering'] = steering_text
                        found_specs.append(f"🎯 Руль: {steering_text}")
                        break
                except:
                    continue

            # 🔥 КУЗОВ
            body_selectors = [
                '.CardInfoSummaryComplexRow:contains("Кузов") .CardInfoSummaryComplexRow__cellValue',
                '[class*="CardInfoSummaryComplexRow"]:contains("Кузов") [class*="cellValue"]',
                '//div[contains(text(), "Кузов")]/following-sibling::div//a'
            ]

            for selector in body_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    body_text = element.text.strip()
                    if body_text:
                        technical_data['body'] = body_text
                        found_specs.append(f"🚙 Кузов: {body_text}")
                        break
                except:
                    continue

            # 🔥 ЦВЕТ
            color_selectors = [
                '.CardInfoSummaryComplexRow:contains("Цвет") .CardInfoSummaryComplexRow__cellValue',
                '[class*="CardInfoSummaryComplexRow"]:contains("Цвет") [class*="cellValue"]',
                '//div[contains(text(), "Цвет")]/following-sibling::div//a'
            ]

            for selector in color_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    color_text = element.text.strip()
                    if color_text:
                        technical_data['color'] = color_text
                        found_specs.append(f"🎨 Цвет: {color_text}")
                        break
                except:
                    continue

            # 🔥 ЦВЕТ - ДОПОЛНИТЕЛЬНЫЙ ПОИСК
            color = await self._extract_color_comprehensive(spec_element)
            if color and 'color' not in technical_data:
                technical_data['color'] = color
                found_specs.append(f"🎨 Цвет: {color}")

            # 🔥 ОДИН ЛОГ ВМЕСТО НЕСКОЛЬКИХ
            if found_specs:
                logger.info(" | ".join(found_specs))

            return technical_data

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения технических характеристик: {e}")
            return {}

    async def _extract_additional_specs(self, spec_element):
        """🔥 Извлекает дополнительные характеристики"""
        try:
            additional_data = {}
            found_specs = []

            # 🔥 ДОБАВЛЯЕМ КОМПЛЕКТАЦИЮ И КУЗОВ ИЗ НОВОГО МЕТОДА
            complectation_body_data = await self._extract_complectation_and_body(spec_element)
            if complectation_body_data:
                additional_data.update(complectation_body_data)
                if complectation_body_data.get('package'):
                    found_specs.append(f"📦 Комплектация: {complectation_body_data['package']}")
                if complectation_body_data.get('body'):
                    found_specs.append(f"🚙 Кузов: {complectation_body_data['body']}")

            # 🔥 НАЛОГ
            tax_selectors = [
                '.CardInfoSummarySimpleRow:contains("Налог") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("Налог") [class*="content"]',
                '//div[contains(text(), "Налог")]/following-sibling::div'
            ]

            for selector in tax_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    tax_text = element.text.strip()
                    if tax_text and '₽' in tax_text:
                        additional_data['tax'] = tax_text
                        found_specs.append(f"💰 Налог: {tax_text}")
                        break
                except:
                    continue

            # 🔥 ТАМОЖНЯ
            customs_selectors = [
                '.CardInfoSummarySimpleRow:contains("Таможня") .CardInfoSummarySimpleRow__content',
                '[class*="CardInfoSummarySimpleRow"]:contains("Таможня") [class*="content"]',
                '//div[contains(text(), "Таможня")]/following-sibling::div'
            ]

            for selector in customs_selectors:
                try:
                    if selector.startswith('//'):
                        element = spec_element.find_element(By.XPATH, selector)
                    else:
                        element = spec_element.find_element(By.CSS_SELECTOR, selector)
                    customs_text = element.text.strip()
                    if customs_text:
                        additional_data['customs'] = customs_text
                        found_specs.append(f"🛃 Таможня: {customs_text}")
                        break
                except:
                    continue

            # 🔥 ОДИН ЛОГ ВМЕСТО НЕСКОЛЬКИХ
            if found_specs:
                logger.info(" | ".join(found_specs))

            return additional_data

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения дополнительных характеристик: {e}")
            return {}

    async def _extract_color_comprehensive(self, spec_element):
        """🔥 УЛУЧШЕННЫЙ поиск цвета автомобиля"""
        try:
            # 🔥 СПОСОБ 1: Поиск в блоке ColorIcon (как в вашем HTML)
            color_selectors = [
                # Основной селектор для блока цвета
                '.ColorIcon-zVfh9 + .CardInfoSummaryComplexRow__cellLabel-i9fmL .CardInfoSummaryComplexRow__cellValue-Hka8p',
                '.ColorIcon-zVfh9 ~ .CardInfoSummaryComplexRow__cellLabel-i9fmL .CardInfoSummaryComplexRow__cellValue-Hka8p',

                # Альтернативные селекторы
                '.CardInfoSummaryComplexRow:has(.ColorIcon-zVfh9) .CardInfoSummaryComplexRow__cellValue-Hka8p',
                'li:has(.ColorIcon-zVfh9) .CardInfoSummaryComplexRow__cellValue-Hka8p',

                # XPath селекторы
                '//li[.//div[contains(@class, "ColorIcon")]]//a[contains(@class, "CardInfoSummaryComplexRow__cellValue")]',
                '//div[contains(@class, "ColorIcon")]/following-sibling::div//a',
            ]

            for selector in color_selectors:
                try:
                    if selector.startswith('//'):
                        elements = spec_element.find_elements(By.XPATH, selector)
                    else:
                        elements = spec_element.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        color_text = element.text.strip()
                        if color_text and self._is_valid_color(color_text):
                            logger.info(f"🎨 Найден цвет через '{selector}': {color_text}")
                            return color_text
                except Exception as e:
                    logger.debug(f"❌ Селектор цвета '{selector}' не сработал: {e}")
                    continue

            # 🔥 СПОСОБ 2: Поиск по тексту "Цвет" в соседних элементах
            text_selectors = [
                '//div[contains(text(), "Цвет")]/following-sibling::div//a',
                '//div[contains(@class, "cellTitle") and contains(text(), "Цвет")]/../div[contains(@class, "cellValue")]//a',
                '.CardInfoSummaryComplexRow__cellTitle-S_R1k:contains("Цвет") ~ .CardInfoSummaryComplexRow__cellValue-Hka8p',
            ]

            for selector in text_selectors:
                try:
                    if selector.startswith('//'):
                        elements = spec_element.find_elements(By.XPATH, selector)
                    else:
                        elements = spec_element.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        color_text = element.text.strip()
                        if color_text and self._is_valid_color(color_text):
                            logger.info(f"🎨 Найден цвет через текст '{selector}': {color_text}")
                            return color_text
                except Exception as e:
                    logger.debug(f"❌ Текстовый селектор цвета '{selector}' не сработал: {e}")
                    continue

            # 🔥 СПОСОБ 3: Поиск по всем ссылкам в блоке характеристик
            try:
                all_links = spec_element.find_elements(By.CSS_SELECTOR, 'a.CardInfoSummaryComplexRow__cellValue-Hka8p')
                for link in all_links:
                    href = link.get_attribute('href') or ''
                    if 'color-' in href:
                        color_text = link.text.strip()
                        if color_text and self._is_valid_color(color_text):
                            logger.info(f"🎨 Найден цвет по ссылке: {color_text}")
                            return color_text
            except Exception as e:
                logger.debug(f"❌ Поиск по ссылкам не сработал: {e}")

            # 🔥 СПОСОБ 4: Поиск в описании
            description_color = await self._extract_color_from_description()
            if description_color:
                return description_color

            logger.warning("⚠️ Цвет автомобиля не найден")
            return ""

        except Exception as e:
            logger.error(f"❌ Ошибка поиска цвета: {e}")
            return ""

    def _is_valid_color(self, color_text):
        """Проверяет, является ли текст валидным цветом"""
        valid_colors = [
            'белый', 'черный', 'чёрный', 'серый', 'синий', 'красный', 'зеленый', 'зелёный',
            'желтый', 'жёлтый', 'оранжевый', 'фиолетовый', 'коричневый', 'бежевый',
            'серебристый', 'золотой', 'бордовый', 'голубой', 'бирюзовый', 'розовый',
            'сиреневый', 'хаки', 'графитовый', 'металлик', 'перламутр'
        ]

        color_lower = color_text.lower()

        # Проверяем полное совпадение
        if color_lower in valid_colors:
            return True

        # Проверяем частичное совпадение
        for valid_color in valid_colors:
            if valid_color in color_lower:
                return True

        # Проверяем длину (короткие тексты вряд ли являются цветами)
        if len(color_text) < 3 or len(color_text) > 20:
            return False

        # Если текст содержит только буквы и выглядит как цвет
        if re.match(r'^[а-яё\s-]+$', color_lower, re.IGNORECASE):
            return True

        return False

    async def _extract_color_from_description(self):
        """Извлекает цвет из описания автомобиля"""
        try:
            description = await self._extract_full_description()
            if not description:
                return ""

            # Ищем упоминания цвета в описании
            color_patterns = [
                r'цвет[:\s]*([а-яё]+)',
                r'окрашен[а]?[в\s]*([а-яё]+)',
                r'([а-яё]+)\s*цвет',
                r'кузов[:\s]*([а-яё]+)',
            ]

            for pattern in color_patterns:
                matches = re.findall(pattern, description.lower())
                for match in matches:
                    if self._is_valid_color(match):
                        logger.info(f"🎨 Цвет найден в описании: {match}")
                        return match

            return ""
        except Exception as e:
            logger.debug(f"❌ Ошибка поиска цвета в описании: {e}")
            return ""

    async def _extract_price_detailed(self):
        """Извлекает цену и статус из детальной карточки"""
        try:
            price_data = {}

            # 🔥 ОСНОВНАЯ ЦЕНА
            price_selectors = [
                '.CardHead__price .OfferPriceCaption__price',
                '.PriceUsedOfferNew__price .OfferPriceCaption__price',
                '.OfferPriceCaption__price',
                '[class*="Price"] [class*="price"]',
                '.CardHead__topRowRightColumn .OfferPriceCaption__price',  # Твой селектор
            ]

            for selector in price_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = element.text.strip()
                    logger.debug(f"💰 Текст цены: {price_text}")
                    price = self._parse_price_text_detailed(price_text)
                    if price > 0:
                        price_data['price'] = price
                        logger.info(f"💰 Найдена цена в карточке: {price}₽")
                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор цены '{selector}' не сработал: {e}")
                    continue

            # 🔥 СТАТУС ЦЕНЫ (Справедливая цена и т.д.)
            status_selectors = [
                '.OfferPriceBadgeNew__green',
                '.OfferPriceBadgeNew',
                '[class*="Badge"]',
                '[class*="status"]',
                '.OfferPriceBadgeNew-cQWc5',  # Твой селектор
            ]

            for selector in status_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    status_text = element.text.strip()
                    if status_text:
                        price_data['price_status'] = status_text
                        logger.info(f"🏷️ Статус цены: {status_text}")
                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор статуса '{selector}' не сработал: {e}")
                    continue

            # 🔥 ЦЕНА СО СКИДКАМИ
            discount_selectors = [
                '.PriceUsedOfferNew__maxDiscount',
                '[class*="discount"]',
                '[class*="maxDiscount"]',
                '.PriceUsedOfferNew__additionalInfo',  # Твой селектор
            ]

            for selector in discount_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    discount_text = element.text.strip()
                    logger.debug(f"🎯 Текст скидки: {discount_text}")
                    discount_price = self._parse_price_text_detailed(discount_text)
                    if discount_price > 0:
                        price_data['discount_price'] = discount_price
                        logger.info(f"🎯 Цена со скидкой: {discount_price}₽")
                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор скидки '{selector}' не сработал: {e}")
                    continue

            return price_data

        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь цену из карточки: {e}")
            return {}

    def _parse_price_text_detailed(self, price_text):
        """Парсит текст цены из детальной карточки"""
        try:
            # Убираем все кроме цифр (включая &nbsp;)
            clean_text = price_text.replace('&nbsp;', ' ').replace(' ', '')
            digits = re.sub(r'[^\d]', '', clean_text)
            if digits:
                price = int(digits)
                # Проверяем разумность цены
                if 1000 <= price <= 50000000:
                    return price
            return 0
        except Exception as e:
            logger.debug(f"❌ Ошибка парсинга цены '{price_text}': {e}")
            return 0

    async def _extract_product_id(self):
        """Извлекает ID объявления из карточки"""
        try:
            selectors = [
                '.CardHead__id',
                '[class*="id"]',
                '[title*="Идентификатор"]',
                '.OfferId',
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    id_text = element.text.strip()
                    logger.debug(f"🆔 Текст ID: {id_text}")
                    # Ищем номер в формате "№ 1128997882"
                    id_match = re.search(r'№\s*(\d+)', id_text)
                    if id_match:
                        product_id = id_match.group(1)
                        logger.info(f"🆔 Найден ID объявления: {product_id}")
                        return product_id
                except Exception as e:
                    logger.debug(f"❌ Селектор ID '{selector}' не сработал: {e}")
                    continue

            # Если не нашли в специальном блоке, пробуем из URL
            current_url = self.driver.current_url
            url_id_match = re.search(r'/(\d+)-[a-f0-9]+', current_url)
            if url_id_match:
                product_id = url_id_match.group(1)
                logger.info(f"🆔 ID из URL: {product_id}")
                return product_id

            return ""
        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь ID объявления: {e}")
            return ""

    async def _extract_seller_avatar(self, seller_element):
        """🔥 Извлекает аватарку продавца и анализирует её тип"""
        try:
            avatar_selectors = [
                '.CardSellerNamePlace2__avatar img',
                '.CardOwner__avatar img',
                '.CardSellerNamePlace2__avatar-icon',
                'img[src*="avatars.mds.yandex.net"]',
                '.CardSellerNamePlace2__avatar-icon'
            ]

            for selector in avatar_selectors:
                try:
                    avatar_element = seller_element.find_element(By.CSS_SELECTOR, selector)
                    avatar_url = avatar_element.get_attribute('src')
                    if avatar_url:
                        # 🔥 ПРЕОБРАЗУЕМ ОТНОСИТЕЛЬНЫЙ URL В АБСОЛЮТНЫЙ
                        if avatar_url.startswith('//'):
                            avatar_url = 'https:' + avatar_url

                        logger.info(f"👤 Найдена аватарка продавца: {avatar_url}")

                        # 🔥 АНАЛИЗИРУЕМ ТИП АВАТАРКИ
                        avatar_type = self._analyze_avatar_type(avatar_url)
                        logger.info(f"🔍 Тип аватарки: {avatar_type}")

                        return avatar_url
                except Exception as e:
                    logger.debug(f"❌ Селектор аватарки '{selector}' не сработал: {e}")
                    continue

            logger.info("ℹ️ Аватарка продавца не найдена")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения аватарки продавца: {e}")
            return None

    def _analyze_avatar_type(self, avatar_url):
        """Анализирует тип аватарки"""
        try:
            if not avatar_url:
                return "not_found"

            avatar_lower = avatar_url.lower()

            # 🔥 ЧАСТНЫЕ ЛИЦА - пользовательские аватарки
            if 'get-autoru-users' in avatar_lower:
                return "private_user"

            # 🔥 ДИЛЕРЫ - логотипы и стандартные аватарки
            elif 'get-autoru-dealers' in avatar_lower:
                return "dealer_logo"
            elif 'default_avatar' in avatar_lower:
                return "default_avatar"
            elif 'logo' in avatar_lower:
                return "company_logo"

            # 🔔 ИКОНКИ-ШЕВРОНЫ (уже проверяются отдельно)
            elif 'shield' in avatar_lower:
                return "shield_icon"

            else:
                return "unknown"

        except Exception as e:
            logger.error(f"❌ Ошибка анализа типа аватарки: {e}")
            return "error"

    async def _extract_seller_info(self):
        """Извлекает информацию о продавце и рейтинг модели"""
        try:
            seller_info = {}

            # 🔥 НАХОДИМ БЛОК ПРОДАВЦА ДЛЯ ИЗВЛЕЧЕНИЯ АВАТАРКИ
            seller_selectors = [
                '.CardSellerNamePlace2',
                '.CardOwner__ownerInfo',
                '[class*="CardSeller"]',
                '[class*="CardOwner"]'
            ]

            seller_element = None
            for selector in seller_selectors:
                try:
                    seller_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"✅ Найден блок продавца: {selector}")
                    break
                except:
                    continue

            # 🔥 ИЗВЛЕКАЕМ АВАТАРКУ ПРОДАВЦА И ОПРЕДЕЛЯЕМ ТИП ПО АВАТАРКЕ
            avatar_url = None
            has_avatar = False
            has_shield_icon = False
            has_iks_pill = False  # 🔥 НОВЫЙ ПРИЗНАК - ИКОНКА С РЕЙТИНГОМ

            if seller_element:
                avatar_url = await self._extract_seller_avatar(seller_element)
                if avatar_url:
                    seller_info['seller_avatar'] = avatar_url
                    has_avatar = True
                    logger.info(f"🖼️ Найдена аватарка: {avatar_url}")

                # 🔥 ПРОВЕРЯЕМ НАЛИЧИЕ ИКОНКИ-ШЕВРОНА (ПРИЗНАК ДИЛЕРА)
                shield_selectors = [
                    'svg[class*="SvgShieldMFilled"]',
                    'svg[class*="Shield"]',
                    '[class*="dealer-badge"]',
                    '[class*="official-dealer"]',
                    '.CardSellerNamePlace2__official-dealer-sign'
                ]

                for selector in shield_selectors:
                    try:
                        elements = seller_element.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.size['height'] > 0:
                                has_shield_icon = True
                                logger.info(f"🛡️ Найден признак дилера: {selector}")
                                break
                        if has_shield_icon:
                            break
                    except:
                        continue

                # 🔥 ПРОВЕРЯЕМ НАЛИЧИЕ ИКОНКИ С РЕЙТИНГОМ (IksPill) - ПРИЗНАК КОМПАНИИ
                iks_pill_selectors = [
                    '.CardSellerNamePlace2__iksPill',
                    '.IksPill',
                    '[class*="iksPill"]',
                    '[class*="IksPill"]'
                ]

                for selector in iks_pill_selectors:
                    try:
                        elements = seller_element.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.size['height'] > 0:
                                has_iks_pill = True
                                logger.info(f"⭐ Найден IksPill с рейтингом: {selector}")

                                # 🔥 ПЫТАЕМСЯ ИЗВЛЕЧЬ РЕЙТИНГ ИЗ IKS PILL
                                try:
                                    rating_text = elem.text.strip()
                                    rating_match = re.search(r'(\d+\.\d+)', rating_text)
                                    if rating_match:
                                        seller_info['seller_rating'] = float(rating_match.group(1))
                                        logger.info(f"📊 Рейтинг из IksPill: {seller_info['seller_rating']}")
                                except:
                                    pass
                                break
                        if has_iks_pill:
                            break
                    except:
                        continue

            # 🔥 ОПРЕДЕЛЯЕМ ТИП ПРОДАВЦА ПО КОМБИНАЦИИ ПРИЗНАКОВ
            seller_type = "Частное лицо"  # по умолчанию

            # 🔥 ПРИЗНАКИ ЧАСТНОГО ЛИЦА:
            # 1. Есть аватарка с паттерном get-autoru-users
            # 2. Нет иконки-шеврона
            # 3. Нет IksPill с рейтингом
            # 4. В названии есть "частное лицо"

            # 🔥 ПРИЗНАКИ ДИЛЕРА/КОМПАНИИ:
            # 1. Есть иконка-шеврон
            # 2. Есть IksPill с рейтингом
            # 3. В названии есть ключевые слова дилеров
            # 4. Нет аватарки с пользовательским фото

            # 🔥 ПРОВЕРЯЕМ ТЕКСТ ИМЕНИ ПРОДАВЦА
            name_selectors = [
                '.CardSellerName__name',
                '.SellerName',
                '.CardSellerNamePlace2__name',
                '[class*="seller"] [class*="name"]',
            ]

            seller_name = "Auto.ru"
            seller_full_text = ""

            for selector in name_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name:
                        seller_full_text = name
                        logger.info(f"👤 Полный текст продавца: {name}")

                        # 🔥 РАЗДЕЛЯЕМ НАЗВАНИЕ, РЕЙТИНГ И ОТЗЫВЫ
                        lines = name.split('\n')
                        clean_name = lines[0].strip()  # Первая строка - название

                        # 🔥 ТОЧНОЕ ОПРЕДЕЛЕНИЕ ТИПА ПРОДАВЦА
                        if "частное лицо" in clean_name.lower():
                            seller_type = "Частное лицо"
                            seller_name = "Частное лицо"
                            logger.info("👤 Определен как частное лицо по тексту")
                        else:
                            seller_name = clean_name

                            # 🔥 КЛЮЧЕВОЙ МОМЕНТ: определяем тип по комбинации признаков
                            dealer_keywords = ['автосалон', 'дилер', 'автоцентр', 'авторусь', 'автомир', 'автомобил',
                                               'motors', 'автохаус', 'center', 'авто ']
                            is_dealer_by_name = any(keyword in clean_name.lower() for keyword in dealer_keywords)

                            # 🔥 ЕСЛИ ЕСТЬ ИКОНКА-ШЕВРОН ИЛИ IKS PILL - ТОЧНО ДИЛЕР
                            if has_shield_icon or has_iks_pill:
                                seller_type = "Компания"
                                logger.info(f"🏢 Определен как компания по иконкам: {clean_name}")
                            # 🔥 ЕСЛИ НЕТ АВАТАРКИ С ПОЛЬЗОВАТЕЛЬСКИМ ФОТО - ВЕРОЯТНО ДИЛЕР
                            elif not has_avatar and is_dealer_by_name:
                                seller_type = "Компания"
                                logger.info(f"🏢 Определен как компания по названию и отсутствию аватарки: {clean_name}")
                            # 🔥 ЕСЛИ ЕСТЬ АВАТАРКА С ПОЛЬЗОВАТЕЛЬСКИМ ФОТО - ВЕРОЯТНО ЧАСТНИК
                            elif has_avatar and not is_dealer_by_name:
                                seller_type = "Частное лицо"
                                logger.info(f"👤 Определен как частное лицо по аватарке: {clean_name}")
                            # 🔥 ЕСЛИ СЛОЖНЫЙ СЛУЧАЙ - ПРОВЕРЯЕМ ДОПОЛНИТЕЛЬНО
                            else:
                                # 🔥 АНАЛИЗИРУЕМ URL АВАТАРКИ
                                if avatar_url and self._is_private_seller_avatar(avatar_url):
                                    seller_type = "Частное лицо"
                                    logger.info(f"👤 Определен как частное лицо по паттерну аватарки: {clean_name}")
                                else:
                                    seller_type = "Компания" if is_dealer_by_name else "Частное лицо"
                                    logger.info(f"🔍 Определен как {seller_type} по комбинации признаков: {clean_name}")

                        # 🔥 ИЗВЛЕКАЕМ РЕЙТИНГ ИЗ ТЕКСТА
                        if 'seller_rating' not in seller_info:
                            rating_match = re.search(r'(\d+\.\d+)', name)
                            if rating_match:
                                try:
                                    seller_info['seller_rating'] = float(rating_match.group(1))
                                    logger.info(f"⭐ Рейтинг продавца: {seller_info['seller_rating']}")
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"⚠️ Некорректное значение рейтинга: {e}")
                                    seller_info['seller_rating'] = 0.0

                        # 🔥 ИЗВЛЕКАЕМ КОЛИЧЕСТВО ОТЗЫВОВ ИЗ ТЕКСТА
                        reviews_match = re.search(r'(\d+)\s*отзыв', name)
                        if not reviews_match:
                            reviews_match = re.search(r'(\d+)\s*review', name)

                        if reviews_match:
                            try:
                                seller_info['reviews_count'] = int(reviews_match.group(1))
                                logger.info(f"📊 Отзывов продавца: {seller_info['reviews_count']}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"⚠️ Некорректное значение отзывов: {e}")
                                seller_info['reviews_count'] = 0

                        break
                except Exception as e:
                    logger.debug(f"❌ Селектор имени '{selector}' не сработал: {e}")
                    continue

            seller_info['seller_name'] = seller_name
            seller_info['seller_type'] = seller_type

            logger.info(f"👤 Итоговый тип продавца: {seller_type}, Имя: {seller_name}")

            # 🔥 ЕСЛИ НЕ НАШЛИ РЕЙТИНГ В ТЕКСТЕ ПРОДАВЦА, ИЩЕМ ОТДЕЛЬНО
            if 'seller_rating' not in seller_info:
                rating_selectors = [
                    '.CardHead__rating .StarRate2__rating',
                    '.StarRate2__rating',
                    '[class*="rating"]',
                ]

                for selector in rating_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        rating_text = element.text.strip()
                        logger.debug(f"⭐ Текст рейтинга: {rating_text}")
                        rating_match = re.search(r'(\d+\.\d+)', rating_text)
                        if rating_match:
                            try:
                                seller_info['seller_rating'] = float(rating_match.group(1))
                                logger.info(f"⭐ Рейтинг модели: {seller_info['seller_rating']}")
                                break
                            except (ValueError, TypeError) as e:
                                logger.warning(f"⚠️ Некорректное значение рейтинга: {e}")
                                seller_info['seller_rating'] = 0.0
                    except Exception as e:
                        logger.debug(f"❌ Селектор рейтинга '{selector}' не сработал: {e}")
                        continue

            # 🔥 ЕСЛИ НЕ НАШЛИ ОТЗЫВЫ В ТЕКСТЕ ПРОДАВЦА, ИЩЕМ ОТДЕЛЬНО
            if 'reviews_count' not in seller_info:
                reviews_selectors = [
                    '.ReviewRatingShortInfo__count',
                    '[class*="review"] [class*="count"]',
                ]

                for selector in reviews_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        reviews_text = element.text.strip()
                        logger.debug(f"📊 Текст отзывов: {reviews_text}")
                        reviews_match = re.search(r'\((\d+)\)', reviews_text)
                        if reviews_match:
                            try:
                                seller_info['reviews_count'] = int(reviews_match.group(1))
                                logger.info(f"📊 Количество отзывов: {seller_info['reviews_count']}")
                                break
                            except (ValueError, TypeError) as e:
                                logger.warning(f"⚠️ Некорректное значение отзывов: {e}")
                                seller_info['reviews_count'] = 0
                    except Exception as e:
                        logger.debug(f"❌ Селектор отзывов '{selector}' не сработал: {e}")
                        continue

            logger.info(f"👤 Информация о продавце: {len(seller_info)} полей")
            return seller_info

        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь информацию о продавце: {e}")
            return {'seller_name': 'Auto.ru', 'seller_type': 'Частное лицо'}

    def _is_private_seller_avatar(self, avatar_url):
        """Проверяет, является ли аватарка признаком частного лица"""
        try:
            # 🔥 ПАТТЕРНЫ АВАТАРОК ЧАСТНЫХ ЛИЦ
            private_avatar_patterns = [
                'get-autoru-users',
                'avatars.mds.yandex.net/get-autoru-users'
            ]

            # 🔥 ПАТТЕРНЫ АВАТАРОК ДИЛЕРОВ/КОМПАНИЙ
            dealer_avatar_patterns = [
                'get-autoru-dealers',
                'default_avatar',
                'logo',
                'shield'
            ]

            avatar_lower = avatar_url.lower()

            # Если URL содержит паттерн частных лиц и НЕ содержит паттерн дилеров
            has_private_pattern = any(pattern in avatar_lower for pattern in private_avatar_patterns)
            has_dealer_pattern = any(pattern in avatar_lower for pattern in dealer_avatar_patterns)

            if has_private_pattern and not has_dealer_pattern:
                logger.info(f"👤 Аватарка определена как частное лицо: {avatar_url}")
                return True
            elif has_dealer_pattern:
                logger.info(f"🏢 Аватарка определена как компания: {avatar_url}")
                return False
            else:
                # Если не можем определить - считаем частным лицом (более безопасно)
                logger.info(f"🔍 Неясный тип аватарки, считаем частным лицом: {avatar_url}")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка анализа аватарки: {e}")
            return True  # В случае ошибки считаем частным лицом

    async def _extract_views_data(self):
        """Извлекает данные о просмотрах"""
        try:
            views_data = {}
            selectors = [
                '.CardHead__views',
                '[class*="views"]',
                '.OfferStats__views',
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    views_text = element.text.strip()
                    logger.debug(f"👁️ Текст просмотров: {views_text}")

                    # Пример: "343 (52 сегодня)"
                    total_match = re.search(r'(\d+)', views_text)
                    today_match = re.search(r'(\d+)\s*сегодня', views_text)

                    if total_match:
                        views_data['views_count'] = int(total_match.group(1))

                    if today_match:
                        views_data['views_today'] = int(today_match.group(1))

                    if views_data:
                        logger.info(f"👁️ Просмотры: {views_data}")
                        return views_data

                except Exception as e:
                    logger.debug(f"❌ Селектор просмотров '{selector}' не сработал: {e}")
                    continue

            return {}
        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь данные о просмотрах: {e}")
            return {}

    async def _extract_posted_date(self):
        """Извлекает дату размещения"""
        try:
            selectors = [
                '.CardHead__creationDate',
                '[class*="creationDate"]',
                '[class*="posted"]',
                '.OfferStats__item',
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    date_text = element.text.strip()
                    logger.debug(f"📅 Текст даты: {date_text}")
                    if date_text and any(word in date_text.lower() for word in
                                         ['нояб', 'дек', 'янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен',
                                          'окт']):
                        logger.info(f"📅 Найдена дата: {date_text}")
                        return date_text
                except Exception as e:
                    logger.debug(f"❌ Селектор даты '{selector}' не сработал: {e}")
                    continue

            return ""
        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь дату: {e}")
            return ""

    async def _extract_full_description(self):
        """🔥 Извлекает ПОЛНОЕ описание автомобиля с нажатием кнопки 'Читать дальше'"""
        try:
            logger.info("🔍 Начинаем поиск полного описания...")

            # 🔥 ПЕРВЫЙ ПРИОРИТЕТ: Прямое извлечение из CardDescriptionHTML (самый надежный)
            description = await self._extract_direct_description()
            if description and len(description) > 50:
                logger.info(f"✅ Прямое описание: {len(description)} символов")
                return description[:4000]

            # 🔥 ВТОРОЙ ПРИОРИТЕТ: Нажатие кнопки "Читать дальше"
            description = await self._click_read_more_and_get_text()
            if description and len(description) > 50:
                logger.info(f"✅ Описание после клика: {len(description)} символов")
                return description[:4000]

            # 🔥 ТРЕТИЙ ПРИОРИТЕТ: Поиск в скрытых элементах
            description = await self._extract_hidden_description()
            if description and len(description) > 10:
                logger.info(f"✅ Скрытое описание: {len(description)} символов")
                return description[:4000]

            logger.warning("❌ Не удалось извлечь описание")
            return ""

        except Exception as e:
            logger.error(f"⚠️ Ошибка извлечения описания: {e}")
            return ""

    async def _extract_direct_description(self):
        """🔥 Прямое извлечение описания из CardDescriptionHTML"""
        try:
            selectors = [
                '.CardDescriptionHTML',  # Основной HTML контейнер
                '.CardDescription__text',  # Текстовый блок
                '.CardDescription__textInner',  # Внутренний текст
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    clean_text = self._clean_description_text(text)

                    if clean_text and len(clean_text) > 20:
                        logger.info(f"📝 Найдено через '{selector}': {len(clean_text)} символов")
                        return clean_text

                except Exception as e:
                    logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            return ""
        except Exception as e:
            logger.error(f"❌ Ошибка прямого извлечения: {e}")
            return ""

    async def _click_read_more_and_get_text(self):
        """🔥 Нажатие кнопки 'Читать дальше' и получение полного текста"""
        try:
            # 🔥 ТОЧНЫЕ СЕЛЕКТОРЫ КНОПКИ ИЗ АНАЛИЗА F12
            button_selectors = [
                '.CardDescription__cutLink',  # Основной селектор
                'button.Button[class*="CardDescription"]',
            ]

            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"🔍 Найдено кнопок с '{selector}': {len(buttons)}")

                    for i, button in enumerate(buttons):
                        try:
                            if button.is_displayed() and button.is_enabled():
                                logger.info(f"🎯 Найдена активная кнопка #{i + 1}: {button.text}")

                                # 🔥 НАЖИМАЕМ ЧЕРЕЗ JAVASCRIPT
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", button)

                                logger.info("✅ Кнопка 'Читать дальше' успешно нажата!")
                                time.sleep(3)

                                # 🔥 ПОЛУЧАЕМ ТЕКСТ ПОСЛЕ КЛИКА
                                full_text = await self._get_full_description_text()
                                if full_text and len(full_text) > 50:
                                    logger.info(f"📖 Полное описание после клика: {len(full_text)} символов")
                                    return full_text

                                break

                        except Exception as e:
                            logger.debug(f"❌ Ошибка с кнопкой #{i + 1}: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"❌ Селектор кнопки '{selector}' не сработал: {e}")
                    continue

            return ""
        except Exception as e:
            logger.error(f"⚠️ Ошибка при нажатии кнопки: {e}")
            return ""

    async def _get_full_description_text(self):
        """🔥 Получает полный текст описания после нажатия кнопки"""
        try:
            description_selectors = [
                '.CardDescriptionHTML',
                '.CardDescription__text',
                '.CardDescription__textInner',
                '.CardDescription',
            ]

            max_text = ""

            for selector in description_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        clean_text = self._clean_description_text(text)
                        if clean_text and len(clean_text) > len(max_text):
                            max_text = clean_text
                            logger.info(f"🔍 Найден текст через '{selector}': {len(clean_text)} символов")
                except:
                    continue

            return max_text

        except Exception as e:
            logger.error(f"❌ Ошибка получения текста описания: {e}")
            return ""

    async def _extract_hidden_description(self):
        """🔥 Извлекает описание из скрытых элементов"""
        try:
            hidden_selectors = [
                '.CardDescription__textInner',  # Часто имеет overflow: hidden
                '.Cut',  # Блок обрезки текста
            ]

            for selector in hidden_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        clean_text = self._clean_description_text(text)
                        if clean_text and len(clean_text) > 20:
                            logger.info(f"🔓 Скрытый текст через '{selector}': {len(clean_text)} символов")
                            return clean_text
                except Exception as e:
                    logger.debug(f"❌ Селектор скрытого текста '{selector}' не сработал: {e}")
                    continue

            return ""
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения скрытого описания: {e}")
            return ""

    def _clean_description_text(self, text):
        """🔥 Очищает текст описания от лишних элементов"""
        if not text:
            return ""

        # 🔥 УБИРАЕМ НЕНУЖНЫЕ ТЕКСТЫ
        unwanted_patterns = [
            r'Читать дальше\s*$',
            r'Комментарий продавца\s*',
            r'^\s*$'
        ]

        clean_text = text

        for pattern in unwanted_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)

        # 🔥 УБИРАЕМ ПУСТЫЕ СТРОКИ И ЛИШНИЕ ПРОБЕЛЫ
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)

        # 🔥 УБИРАЕМ ЛИШНИЕ ПРОБЕЛЫ
        clean_text = re.sub(r'\s+', ' ', clean_text)

        return clean_text.strip()

    async def _extract_all_photos_detailed(self):
        """Извлекает все фото из детальной карточки"""
        try:
            photo_urls = []

            # 🔥 ИЩЕМ ОСНОВНЫЕ ФОТО В ГАЛЕРЕЕ
            selectors = [
                '.ImageGalleryDesktop__thumb',
                '.ImageGallery__thumb',
                '.PhotoGallery__thumb',
                'img[data-zone-name="gallery-image"]',
                '.ImageGalleryDesktop__image img',
                '.ImageGalleryDesktop img',
                '.Gallery__image img',
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"🖼️ Найдено элементов с '{selector}': {len(elements)}")

                    for element in elements:
                        for attr in ['src', 'data-src', 'data-url', 'data-original']:
                            try:
                                url = element.get_attribute(attr)
                                if url and 'http' in url and ('avatars.mds.yandex.net' in url or 'auto.ru' in url):
                                    # 🔥 ПРЕОБРАЗУЕМ URL МИНИАТЮРЫ В URL ПОЛНОРАЗМЕРНОГО ИЗОБРАЖЕНИЯ
                                    full_url = self._convert_to_full_size_url(url)
                                    if full_url and full_url not in photo_urls:
                                        photo_urls.append(full_url)
                                        logger.debug(f"🖼️ Найдено фото: {full_url}")
                            except Exception as e:
                                logger.debug(f"❌ Ошибка получения атрибута {attr}: {e}")
                                continue

                    if photo_urls:  # Если нашли фото, выходим
                        break

                except Exception as e:
                    logger.debug(f"❌ Селектор фото '{selector}' не сработал: {e}")
                    continue

            # 🔥 ЕСЛИ ФОТО НЕ НАЙДЕНЫ, ПРОБУЕМ КЛИКНУТЬ ПО ГАЛЕРЕЕ
            if not photo_urls:
                photo_urls = await self._extract_photos_by_clicking_gallery()

            # Ограничиваем количество фото
            photo_urls = photo_urls[:10]
            logger.info(f"🖼️ Итого найдено фото: {len(photo_urls)}")
            return photo_urls

        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь фото: {e}")
            return []

    async def _extract_complectation_and_body(self, spec_element):
        """🔥 Извлекает комплектацию и тип кузова из блока характеристик"""
        try:
            complectation_data = {}

            # 🔥 СПОСОБ 1: Поиск по иконкам (приоритетный)
            complectation_data = await self._extract_by_icons(spec_element)

            # 🔥 СПОСОБ 2: Если не нашли по иконкам, ищем по тексту
            if not complectation_data.get('package') or not complectation_data.get('body'):
                text_data = await self._extract_complectation_and_body_by_text(spec_element)
                if text_data:
                    complectation_data.update(text_data)

            # 🔥 ДЕБАГ: Если все еще не нашли, используем отладочный метод
            if not complectation_data.get('package') and not complectation_data.get('body'):
                logger.warning("⚠️ Комплектация и кузов не найдены стандартными методами, пробуем дебаг...")
                debug_data = await self.debug_complectation_parsing(spec_element)
                if debug_data:
                    complectation_data.update(debug_data)

            logger.info(f"🎯 Итоговые данные комплектации и кузова: {complectation_data}")
            return complectation_data

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения комплектации и кузова: {e}")
            return {}

    async def _extract_by_icons(self, spec_element):
        """🔥 Извлекает по иконкам (расширенная версия)"""
        complectation_data = {}

        # 🔥 КОМПЛЕКТАЦИЯ - ищем блоки с текстом "Комплектация"
        complectation_selectors = [
            '//li[contains(@class, "CardInfoSummaryComplexRow")]//div[contains(text(), "Комплектация")]',
            '.CardInfoSummaryComplexRow-CngDv:has(div:contains("Комплектация"))',
            '//div[contains(@class, "CardInfoSummaryComplexRow")]//div[contains(text(), "Комплектация")]',
        ]

        found_data = []

        for selector in complectation_selectors:
            try:
                if selector.startswith('//'):
                    elements = spec_element.find_elements(By.XPATH, selector)
                else:
                    elements = spec_element.find_elements(By.CSS_SELECTOR, selector)

                for element in elements:
                    # Находим родительский блок и ищем значение внутри него
                    parent_row = element.find_element(By.XPATH,
                                                      "./ancestor::li[contains(@class, 'CardInfoSummaryComplexRow')]")
                    if parent_row:
                        # Ищем значение комплектации
                        value_selectors = [
                            './/span[contains(@class, "cellValue")]',
                            './/a[contains(@class, "cellValue")]',
                            './/div[contains(@class, "cellValue")]',
                            './/span[contains(@class, "CardInfoSummaryComplexRow__cellValue")]',
                        ]

                        for value_selector in value_selectors:
                            try:
                                value_elem = parent_row.find_element(By.XPATH, value_selector)
                                package_text = value_elem.text.strip()
                                if package_text and package_text != "Комплектация":
                                    complectation_data['package'] = package_text
                                    found_data.append(f"📦 Комплектация: {package_text}")
                                    break
                            except:
                                continue

                    if complectation_data.get('package'):
                        break

                if complectation_data.get('package'):
                    break

            except Exception as e:
                logger.debug(f"❌ Селектор комплектации '{selector}' не сработал: {e}")
                continue

        # 🔥 КУЗОВ - ищем блоки с текстом "Кузов"
        body_selectors = [
            '//li[contains(@class, "CardInfoSummaryComplexRow")]//div[contains(text(), "Кузов")]',
            '.CardInfoSummaryComplexRow-CngDv:has(div:contains("Кузов"))',
            '//div[contains(@class, "CardInfoSummaryComplexRow")]//div[contains(text(), "Кузов")]',
        ]

        for selector in body_selectors:
            try:
                if selector.startswith('//'):
                    elements = spec_element.find_elements(By.XPATH, selector)
                else:
                    elements = spec_element.find_elements(By.CSS_SELECTOR, selector)

                for element in elements:
                    # Находим родительский блок и ищем значение внутри него
                    parent_row = element.find_element(By.XPATH,
                                                      "./ancestor::li[contains(@class, 'CardInfoSummaryComplexRow')]")
                    if parent_row:
                        # Ищем значение кузова
                        value_selectors = [
                            './/a[contains(@class, "cellValue")]',  # Кузов обычно ссылка
                            './/span[contains(@class, "cellValue")]',
                            './/div[contains(@class, "cellValue")]',
                            './/a[contains(@class, "CardInfoSummaryComplexRow__cellValue")]',
                        ]

                        for value_selector in value_selectors:
                            try:
                                value_elem = parent_row.find_element(By.XPATH, value_selector)
                                body_text = value_elem.text.strip()
                                if body_text and body_text != "Кузов":
                                    complectation_data['body'] = body_text
                                    found_data.append(f"🚙 Кузов: {body_text}")
                                    break
                            except:
                                continue

                    if complectation_data.get('body'):
                        break

                if complectation_data.get('body'):
                    break

            except Exception as e:
                logger.debug(f"❌ Селектор кузова '{selector}' не сработал: {e}")
                continue

        # 🔥 ОДИН ЛОГ ВМЕСТО НЕСКОЛЬКИХ
        if found_data:
            logger.info(" | ".join(found_data))

        return complectation_data

    async def _extract_complectation_and_body_by_text(self, spec_element):
        """🔥 Альтернативный метод извлечения комплектации и кузова по тексту"""
        try:
            complectation_data = {}

            # 🔥 ПОИСК ВСЕХ БЛОКОВ CardInfoSummaryComplexRow
            all_rows = spec_element.find_elements(By.CSS_SELECTOR, '.CardInfoSummaryComplexRow-CngDv')
            logger.info(f"🔍 Найдено блоков характеристик: {len(all_rows)}")

            for i, row in enumerate(all_rows):
                try:
                    row_text = row.text.strip()

                    # Ищем комплектацию
                    package_found = None
                    if 'Комплектация' in row_text:
                        value_selectors = [
                            '.CardInfoSummaryComplexRow__cellValue-Hka8p',
                            'span.CardInfoSummaryComplexRow__cellValue-Hka8p',
                            'a.CardInfoSummaryComplexRow__cellValue-Hka8p',
                        ]

                        for selector in value_selectors:
                            try:
                                value_elem = row.find_element(By.CSS_SELECTOR, selector)
                                package_text = value_elem.text.strip()
                                if package_text and package_text != "Комплектация":
                                    package_found = package_text
                                    complectation_data['package'] = package_text
                                    break
                            except:
                                continue

                    # Ищем кузов
                    body_found = None
                    if 'Кузов' in row_text:
                        value_selectors = [
                            'a.CardInfoSummaryComplexRow__cellValue-Hka8p',
                            'span.CardInfoSummaryComplexRow__cellValue-Hka8p',
                            '.CardInfoSummaryComplexRow__cellValue-Hka8p',
                        ]

                        for selector in value_selectors:
                            try:
                                value_elem = row.find_element(By.CSS_SELECTOR, selector)
                                body_text = value_elem.text.strip()
                                if body_text and body_text != "Кузов":
                                    body_found = body_text
                                    complectation_data['body'] = body_text
                                    break
                            except:
                                continue

                    # 🔥 ИСПРАВЛЕНИЕ: ОДНА строка лога вместо нескольких
                    log_parts = [f"📋 Блок {i + 1}: {row_text}"]
                    if package_found:
                        log_parts.append(f"📦 Комплектация: {package_found}")
                    if body_found:
                        log_parts.append(f"🚙 Кузов: {body_found}")

                    if len(log_parts) > 1:  # Если есть что-то кроме базовой информации
                        logger.info(" | ".join(log_parts))

                except Exception as e:
                    logger.debug(f"❌ Ошибка анализа блока {i + 1}: {e}")
                    continue

            return complectation_data

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения комплектации и кузова по тексту: {e}")
            return {}

    async def debug_complectation_parsing(self, spec_element):
        """🔥 Метод для отладки парсинга комплектации и кузова"""
        try:
            logger.info("🔍 ДЕБАГ: Начинаем парсинг комплектации и кузова...")

            # Получаем весь HTML блока для отладки
            html_content = spec_element.get_attribute('innerHTML')
            logger.info(f"📋 HTML блока характеристик (первые 1000 символов): {html_content[:1000]}")

            # Пробуем разные методы
            result_by_icons = await self._extract_by_icons(spec_element)
            logger.info(f"🎯 Результат по иконкам: {result_by_icons}")

            result_by_text = await self._extract_complectation_and_body_by_text(spec_element)
            logger.info(f"🎯 Результат по тексту: {result_by_text}")

            return {**result_by_icons, **result_by_text}

        except Exception as e:
            logger.error(f"❌ Ошибка в дебаг-методе: {e}")
            return {}

    def _convert_to_full_size_url(self, url):
        """Преобразует URL миниатюры в URL полноразмерного изображения"""
        try:
            # 🔥 ПРЕОБРАЗОВАНИЕ ДЛЯ AUTO.RU
            if 'avatars.mds.yandex.net' in url:
                # Заменяем размеры на максимальные
                full_url = url.replace('small', 'large').replace('thumb', 'orig').replace('_1', '_0')
                # Убираем параметры размера если есть
                full_url = re.sub(r'-\d+x\d+', '', full_url)
                return full_url
            elif 'auto.ru' in url:
                # Для прямых ссылок auto.ru
                return url.split('?')[0]  # Убираем параметры если есть
            return url
        except:
            return url

    async def _extract_photos_by_clicking_gallery(self):
        """Извлекает фото путем клика по галерее"""
        try:
            photo_urls = []

            # 🔥 ИЩЕМ КНОПКУ ГАЛЕРЕИ И КЛИКАЕМ
            gallery_selectors = [
                '.ImageGalleryDesktop__thumb',
                '.ImageGalleryDesktop__image',
                '.Gallery__thumb',
                '[class*="gallery"] img',
            ]

            for selector in gallery_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Кликаем по первому элементу галереи
                        elements[0].click()
                        time.sleep(2)

                        # 🔥 ТЕПЕРЬ ИЩЕМ ФОТО В РАСКРЫТОЙ ГАЛЕРЕЕ
                        expanded_selectors = [
                            '.ImageGalleryPopup__image img',
                            '.GalleryPopup img',
                            '.Popup img[src*="avatars.mds.yandex.net"]',
                        ]

                        for exp_selector in expanded_selectors:
                            try:
                                exp_elements = self.driver.find_elements(By.CSS_SELECTOR, exp_selector)
                                for elem in exp_elements:
                                    for attr in ['src', 'data-src']:
                                        try:
                                            url = elem.get_attribute(attr)
                                            if url and 'http' in url and 'avatars.mds.yandex.net' in url:
                                                full_url = self._convert_to_full_size_url(url)
                                                if full_url not in photo_urls:
                                                    photo_urls.append(full_url)
                                                    logger.debug(f"🖼️ Фото из галереи: {full_url}")
                                        except:
                                            continue
                            except:
                                continue

                        # Закрываем галерею
                        try:
                            close_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                                      '.Popup__close, [class*="close"]')
                            for btn in close_buttons:
                                if btn.is_displayed():
                                    btn.click()
                                    time.sleep(1)
                                    break
                        except:
                            pass

                        if photo_urls:
                            break

                except Exception as e:
                    logger.debug(f"❌ Ошибка клика по галерее: {e}")
                    continue

            return photo_urls

        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения фото через галерею: {e}")
            return []

    async def _extract_specifications(self):
        """Извлекает дополнительные характеристики"""
        try:
            specs = {}

            # Ищем блок с характеристиками
            spec_selectors = [
                '.CardInfoRow',
                '.CardSpecifications',
                '.CardComplectation',
                '.CardInfo',
            ]

            for selector in spec_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if ':' in text:
                                key, value = text.split(':', 1)
                                specs[key.strip()] = value.strip()
                        except:
                            continue
                except:
                    continue

            logger.info(f"🔧 Извлечено характеристик: {len(specs)}")
            return specs

        except Exception as e:
            logger.warning(f"⚠️ Не удалось извлечь характеристики: {e}")
            return {}

    # 🔥 БАЗОВЫЕ МЕТОДЫ ИЗВЛЕЧЕНИЯ ИЗ СПИСКА

    async def _extract_title(self, item):
        """Извлекает название машины"""
        selectors = [
            'a[data-ftid="bull_title"]',
            '.ListingItemTitle__link',
            '.ListingItemTitle a',
            'h3 a',
            '[class*="title"] a',
        ]

        for selector in selectors:
            try:
                element = item.find_element(By.CSS_SELECTOR, selector)
                title = element.text.strip()
                if title and len(title) > 3:
                    logger.debug(f"📝 Название найдено: {title}")
                    return title
            except Exception as e:
                continue

        # Fallback: ищем любой текст в элементе
        try:
            text = item.text
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10 and any(word in line.lower() for word in
                                          ['nissan', 'mazda', 'toyota', 'honda', 'bmw', 'audi', 'kia', 'hyundai']):
                    logger.debug(f"📝 Название из текста: {line}")
                    return line
        except:
            pass

        logger.warning("❌ Не удалось извлечь название")
        return None

    async def _extract_price_basic(self, item):
        """Извлекает цену из списка объявлений"""
        selectors = [
            '.ListingItemPrice__content',
            '[data-ftid="bull_price"]',
            '.ListingItemPrice',
            '.Price',
            '[class*="price"]',
        ]

        for selector in selectors:
            try:
                element = item.find_element(By.CSS_SELECTOR, selector)
                price_text = element.text.strip()
                logger.debug(f"💰 Текст цены: {price_text}")
                price = self._parse_price_text_basic(price_text)
                if price > 0 and price < 100000000:
                    logger.debug(f"✅ Цена извлечена: {price}")
                    return price
            except Exception as e:
                continue

        # Fallback: ищем цену в тексте элемента
        try:
            text = item.text
            price_patterns = [
                r'(\d{1,3}(?:\s\d{3})*)\s*₽',
                r'(\d+)\s*руб',
                r'цена[\s:]*(\d+)',
            ]

            for pattern in price_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    clean_match = match.replace(' ', '')
                    if clean_match.isdigit():
                        price = int(clean_match)
                        if 1000 <= price <= 50000000:
                            logger.debug(f"✅ Цена из текста: {price}")
                            return price
        except Exception as e:
            logger.debug(f"❌ Ошибка поиска цены в тексте: {e}")

        logger.warning("❌ Не удалось извлечь цену")
        return 0

    def _parse_price_text_basic(self, price_text):
        """Парсит текст цены из списка"""
        try:
            # Убираем все пробелы и нецифровые символы
            clean_text = price_text.replace('&nbsp;', ' ').replace(' ', '')
            digits = re.sub(r'[^\d]', '', clean_text)
            if digits:
                price = int(digits)
                if 1000 <= price <= 50000000:
                    return price
            return 0
        except Exception as e:
            logger.debug(f"❌ Ошибка парсинга цены '{price_text}': {e}")
            return 0

    async def _extract_item_url(self, item):
        """Извлекает URL объявления"""
        selectors = [
            'a[data-ftid="bull_title"]',
            '.ListingItemTitle__link',
            'a[href*="/cars/used/"]',
            'a[href*="/cars/new/"]',
            'a[href*="auto.ru/cars/"]',
        ]

        for selector in selectors:
            try:
                element = item.find_element(By.CSS_SELECTOR, selector)
                url = element.get_attribute('href')
                if url and 'auto.ru' in url:
                    logger.debug(f"🔗 URL найден: {url}")
                    return url
            except Exception as e:
                continue

        logger.warning("❌ Не удалось извлечь URL")
        return None

    async def _extract_year(self, item):
        """Извлекает год выпуска"""
        try:
            # Ищем год в названии
            title = await self._extract_title(item)
            if title:
                year_match = re.search(r'(19[89][0-9]|20[0-2][0-9])', title)
                if year_match:
                    return year_match.group(1)

            # Ищем год в описании
            selectors = [
                '.ListingItem__year',
                '[data-ftid="bull_description"]',
                '.ListingItemTechSummary',
            ]

            for selector in selectors:
                try:
                    element = item.find_element(By.CSS_SELECTOR, selector)
                    text = element.text
                    year_match = re.search(r'(19[89][0-9]|20[0-2][0-9])', text)
                    if year_match:
                        return year_match.group(1)
                except:
                    continue

            return ""
        except:
            return ""

    async def _extract_mileage(self, item):
        """Извлекает пробег"""
        selectors = [
            '.ListingItem__kmAge',
            '[data-ftid="bull_description"]',
            '.ListingItemKmAge',
        ]

        for selector in selectors:
            try:
                element = item.find_element(By.CSS_SELECTOR, selector)
                text = element.text
                mileage_match = re.search(r'(\d[\d\s]*)\s*км', text)
                if mileage_match:
                    mileage = mileage_match.group(1).replace(' ', '')
                    return f"{mileage} км"
            except:
                continue
        return ""

    async def _extract_engine_info(self, item):
        """Извлекает информацию о двигателе"""
        selectors = [
            '[data-ftid="bull_description"]',
            '.ListingItemTechSummary',
            '.ListingItem__summary',
        ]

        for selector in selectors:
            try:
                element = item.find_element(By.CSS_SELECTOR, selector)
                text = element.text
                # Ищем паттерны двигателя
                engine_match = re.search(r'(\d+\.\d+ л\.?|\d+ л\.?|[бд]изель|бензин|электро)', text, re.IGNORECASE)
                if engine_match:
                    return engine_match.group(1)
                # Если не нашли конкретный паттерн, возвращаем весь текст
                if text and len(text) < 100:
                    return text.strip()
            except:
                continue
        return ""

    async def _extract_location(self, item):
        """Извлекает местоположение"""
        selectors = [
            '.ListingItem__location',
            '.MetroListPlace__region',
            '[data-ftid="bull_location"]',
        ]

        for selector in selectors:
            try:
                element = item.find_element(By.CSS_SELECTOR, selector)
                location = element.text.strip()
                if location:
                    return location
            except:
                continue
        return "Москва"

    async def _extract_photo_url(self, item):
        """Извлекает URL фото"""
        selectors = [
            'img[src*="avatars.mds.yandex.net"]',
            'img[data-src*="avatars.mds.yandex.net"]',
            '.ListingItemGallery__image img',
            'img[src*="auto.ru"]',
        ]

        for selector in selectors:
            try:
                elements = item.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    for attr in ['src', 'data-src', 'data-url']:
                        try:
                            url = element.get_attribute(attr)
                            if url and 'http' in url and ('avatars.mds.yandex.net' in url or 'auto.ru' in url):
                                logger.debug(f"🖼️ Фото найдено: {url}")
                                return url
                        except:
                            continue
            except:
                continue
        return ""

    # 🔥 ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ

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
        """Проверяет релевантность машины поисковому запросу"""
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

    def _calculate_target_price(self, price):
        """Простой расчет целевой цены"""
        return price

    def _build_basic_description(self, year, mileage, engine):
        """Строит базовое описание"""
        parts = []
        if year:
            parts.append(f"Год: {year}")
        if mileage:
            parts.append(f"Пробег: {mileage}")
        if engine:
            parts.append(f"Двигатель: {engine}")
        return " | ".join(parts) if parts else "Автомобиль с Auto.ru"

    def _clean_query_for_auto_ru(self, query):
        """Очищает запрос для Auto.ru"""
        temporal_words = ['свежий', 'сегодня', 'утро', 'утренняя', 'только', 'что', 'новый', 'новые']
        words = query.lower().split()
        clean_words = [word for word in words if word not in temporal_words]
        return " ".join(clean_words) if clean_words else "nissan"

    def _build_search_url(self, query):
        """Строит URL для поиска"""
        if 'mazda' in query.lower() or 'мазда' in query.lower():
            return f"{self.base_url}/moskva/cars/mazda/all/"
        elif 'nissan' in query.lower() or 'ниссан' in query.lower():
            return f"{self.base_url}/moskva/cars/nissan/all/"
        else:
            encoded_query = quote(query)
            return f"{self.base_url}/moskva/cars/all/?query={encoded_query}"

    async def _wait_for_page_load(self):
        """Ожидает загрузку страницы поиска"""
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.ListingCars, .ListingItem, [data-ftid="bulls-list_bull"]'))
            )
            logger.info("✅ Страница поиска Auto.ru загружена")
            time.sleep(3)  # Даем больше времени для загрузки
        except Exception as e:
            logger.warning(f"⚠️ Не дождались полной загрузки страницы: {e}")

    async def _scroll_page(self):
        """Прокручивает страницу"""
        try:
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Увеличиваем время между прокрутками
            logger.info("✅ Страница прокручена")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка прокрутки: {e}")

    # Реализация абстрактных методов BaseSiteParser

    async def parse_item(self, item, category):
        """🔍 Парсит машину - реализация абстрактного метода BaseSiteParser"""
        return await self.parse_item_advanced(item, category)

    def wait_for_element(self, selector, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )