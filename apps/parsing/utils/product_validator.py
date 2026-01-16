# utils/product_validator.py
import logging
import asyncio

# ✅ Создаем логгер для валидатора товаров
logger = logging.getLogger('parser.validator')


class ProductValidator:
    """УМНЫЙ валидатор товаров с ML-оценкой свежести - ТОЛЬКО ВАЛИДАЦИЯ"""

    def __init__(self):
        self.min_price = 0
        self.max_price = 1000000000  # 1 миллиард по умолчанию
        self.use_price_filters = False  # 🔥 Флаг использования фильтров

        # 🧠 ML модель свежести (ленивая инициализация)
        self.ml_freshness_predictor = None
        self._ml_initialized = False

    async def _init_ml_freshness_predictor(self):
        """🎯 Ленивая инициализация ML модели свежести"""
        if self._ml_initialized:
            return True

        try:
            # 🔥 ДИНАМИЧЕСКИЙ ИМПОРТ чтобы избежать циклических зависимостей
            from apps.parsing.ai.ml_freshness_predictor import MLFreshnessPredictor
            self.ml_freshness_predictor = MLFreshnessPredictor()
            await self.ml_freshness_predictor.initialize_model()
            self._ml_initialized = True
            logger.info("✅ ML модель свежести инициализирована")
            return True
        except ImportError as e:
            logger.warning(f"⚠️ MLFreshnessPredictor не найден: {e}")
            self.ml_freshness_predictor = None
            self._ml_initialized = True
            return False
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации ML модели: {e}")
            self.ml_freshness_predictor = None
            self._ml_initialized = True
            return False

    def update_price_filters(self, min_price=None, max_price=None):
        """Обновляет фильтры цен из настроек Django с УМНОЙ логикой"""
        try:
            # 🔥 УМНАЯ ЛОГИКА: если цены реалистичные и разные - используем фильтры
            if (min_price is not None and max_price is not None and
                    min_price >= 0 and max_price > min_price and max_price > 1000):
                self.min_price = min_price
                self.max_price = max_price
                self.use_price_filters = True
                logger.info(f"💰 Установлены УМНЫЕ фильтры цен: {self.min_price}-{self.max_price}₽")
            else:
                # 🔥 ЕСЛИ ЦЕНЫ НЕ УСТАНОВЛЕНЫ ИЛИ НЕРЕАЛИСТИЧНЫ - ПРИНИМАЕМ ВСЕ
                self.use_price_filters = False
                self.min_price = 0
                self.max_price = 1000000000
                logger.info("💰 Фильтры цен ОТКЛЮЧЕНЫ - принимаем ВСЕ товары с ценой > 0")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления фильтров цен: {e}")
            self.use_price_filters = False

    async def is_good_deal(self, product):
        """🔥 УМНАЯ ПРОВЕРКА ТОВАРА С ML-ОЦЕНКОЙ СВЕЖЕСТИ"""
        try:
            # 1. 🧠 ИНИЦИАЛИЗИРУЕМ ML модель при первом использовании
            if not self._ml_initialized:
                await self._init_ml_freshness_predictor()

            # 2. Определяем уровень свежести (НЕ отсеиваем!)
            ProductValidator.is_fresh_product(product)

            price = product.get('price', 0)

            # 3. 🔥 БАЗОВАЯ ПРОВЕРКА - ЦЕНА ДОЛЖНА БЫТЬ ПОЛОЖИТЕЛЬНОЙ
            if price <= 0:
                logger.info(f"💰 Отфильтрован: некорректная цена {price}₽")
                return False

            # 4. 🔥 УМНАЯ ПРОВЕРКА ПО НАСТРОЙКАМ ЦЕН
            if self.use_price_filters:
                if price < self.min_price or price > self.max_price:
                    logger.info(
                        f"💰 Цена не в диапазоне настроек: {price}₽ (требуется: {self.min_price}-{self.max_price}₽)")
                    return False
                else:
                    logger.info(
                        f"🎯 Товар прошел ценовой фильтр: {price}₽ в диапазоне {self.min_price}-{self.max_price}₽")
            else:
                logger.info(f"🎯 Товар принят (фильтры отключены): {price}₽")

            # 5. 🔥 ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ КАЧЕСТВА
            if not self._check_product_quality(product):
                return False

            # 6. 🧠 РАССЧИТЫВАЕМ ML-ОЦЕНКУ СВЕЖЕСТИ И ПРИОРИТЕТ
            await self._calculate_ml_scores(product)

            logger.info(f"✅ ТОВАР ПРОШЕЛ ВСЕ ПРОВЕРКИ: {product.get('name', '')[:50]}... - {price}₽")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки сделки: {e}")
            return False

    async def _calculate_ml_scores(self, product):
        """🧠 Рассчитывает ML-оценки и приоритет для товара"""
        try:
            # 1. ML оценка свежести
            ml_freshness_score = 0.5
            ml_freshness_category = "БЕЗ ML"

            if self.ml_freshness_predictor:
                # 🔥 ПРЕДСКАЗАНИЕ ML МОДЕЛИ
                ml_freshness_score = self.ml_freshness_predictor.predict_freshness(product)
                ml_freshness_category = self.ml_freshness_predictor.get_freshness_category(ml_freshness_score)
                logger.info(f"🧠 ML свежесть: {ml_freshness_score:.2f} ({ml_freshness_category})")
            else:
                # Фолбэк расчет
                ml_freshness_score = self._calculate_fallback_freshness(product)
                logger.info(f"⚡ Фолбэк свежесть: {ml_freshness_score:.2f}")

            # 2. Рассчитываем приоритет для сортировки
            priority_score = self._calculate_priority_score(product, ml_freshness_score)

            # 3. Сохраняем в продукт
            product['ml_freshness_score'] = round(ml_freshness_score, 3)
            product['ml_freshness_category'] = ml_freshness_category
            product['priority_score'] = round(priority_score, 1)

            logger.info(f"🏆 Приоритет: {priority_score:.1f} (ML свежесть: {ml_freshness_score:.2f})")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета ML-оценок: {e}")
            # Устанавливаем значения по умолчанию
            product['ml_freshness_score'] = 0.5
            product['ml_freshness_category'] = "ОШИБКА"
            product['priority_score'] = 50.0

    def _calculate_fallback_freshness(self, product):
        """🔄 Фолбэк расчет свежести без ML"""
        try:
            time_listed = product.get('time_listed', 24)

            if time_listed <= 0.5:  # 30 минут
                return 0.95
            elif time_listed <= 2:  # 2 часа
                return 0.85
            elif time_listed <= 6:  # 6 часов
                return 0.70
            elif time_listed <= 24:  # 1 день
                return 0.40
            elif time_listed <= 72:  # 3 дня
                return 0.20
            else:  # > 3 дней
                return 0.10
        except:
            return 0.5

    def _calculate_priority_score(self, product, ml_freshness_score):
        """🏆 РАСЧЕТ ИТОГОВОГО ПРИОРИТЕТА ДЛЯ СОРТИРОВКИ"""
        try:
            # 1. ML свежесть - 60% веса
            freshness = ml_freshness_score

            # 2. Выгода (profit_percent) - 30% веса
            profit_percent = product.get('profit_percent', 0) or 0
            deal_score = min(profit_percent / 100.0, 1.0)

            # 3. Качество объявления - 10% веса
            quality = self._calculate_quality_score(product)

            # 🎯 ИТОГ: 100 баллов максимум
            priority = (
                    freshness * 60 +  # 60% свежесть
                    deal_score * 30 +  # 30% выгода
                    quality * 10  # 10% качество
            )

            return min(priority, 100.0)  # Ограничиваем 100 баллами

        except Exception as e:
            logger.error(f"❌ Ошибка расчета приоритета: {e}")
            return 50.0

    def _calculate_quality_score(self, product):
        """📊 Расчет качества объявления"""
        try:
            score = 0.5  # База

            # Бонусы
            if product.get('images') and len(product.get('images', [])) >= 3:
                score += 0.2
            if product.get('description') and len(product.get('description', '')) > 100:
                score += 0.15
            if product.get('seller_rating', 0) > 4.5:
                score += 0.1
            if product.get('metro_stations') and len(product.get('metro_stations', [])) > 0:
                score += 0.05

            return min(score, 1.0)
        except:
            return 0.5

    def _check_product_quality(self, product):
        """Дополнительные проверки качества товара"""
        try:
            name = product.get('name', '')
            url = product.get('url', '')

            # Проверяем наличие обязательных полей
            if not name or not url:
                logger.info("❌ Отфильтрован: отсутствует название или URL")
                return False

            # Проверяем минимальную длину названия
            if len(name) < 5:
                logger.info("❌ Отфильтрован: слишком короткое название")
                return False

            # Проверяем URL на валидность
            if not url.startswith(('http://', 'https://')):
                logger.info("❌ Отфильтрован: невалидный URL")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки качества: {e}")
            return False

    def is_new_product(self, product):
        """Проверяет, является ли товар новым с учетом настроек цен"""
        try:
            price = product.get('price', 0)
            name = product.get('name', '')[:60]

            logger.info(f"🔍 Проверка новизны: {name} - {price}₽")

            # 1. Базовая проверка цена
            if price <= 0:
                logger.info(f"❌ Отфильтрован: некорректная цена {price}₽")
                return False

            # 2. 🔥 ПРОВЕРКА ПО НАСТРОЙКАМ ЦЕН
            if self.use_price_filters:
                if price < self.min_price or price > self.max_price:
                    logger.info(f"❌ Цена не в диапазоне настроек: {price}₽")
                    return False

            # 3. Минимальная цена (защита от мусора)
            if price < 10:  # Минимум 10₽
                logger.info(f"❌ Отфильтрован: слишком дешевый {price}₽")
                return False

            # 4. Проверка основных полей
            if not product.get('name') or not product.get('url'):
                logger.info("❌ Отфильтрован: отсутствуют основные поля")
                return False

            logger.info(f"✅ НОВЫЙ ТОВАР ПРИНЯТ: {price}₽")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки новизны: {e}")
            return False

    async def process_product(self, product):
        """🔥 АСИНХРОННАЯ обработка товара с ML-оценками (БЕЗ СОХРАНЕНИЯ В БАЗУ)"""
        try:
            # 1. Проверяем товар (асинхронно!)
            if not await self.is_good_deal(product):
                logger.info(f"❌ Товар не прошел проверку: {product.get('name', '')[:50]}...")
                return None

            # 2. Возвращаем продукт с ML-данными
            logger.info(
                f"✅ ТОВАР ПРОШЕЛ ВСЕ ПРОВЕРКИ И ИМЕЕТ ML-ДАННЫЕ: {product.get('name', '')[:50]}... - {product.get('price', 0)}₽")

            # Логируем ML-данные
            logger.info(f"🧠 ИТОГОВЫЕ ML-ДАННЫЕ:")
            logger.info(f"  ml_freshness_score: {product.get('ml_freshness_score', 0.5)}")
            logger.info(f"  priority_score: {product.get('priority_score', 50.0)}")
            logger.info(f"  freshness_category: {product.get('ml_freshness_category', 'БЕЗ ML')}")

            return product

        except Exception as e:
            logger.error(f"❌ Ошибка обработки товара: {e}")
            return None

    # 🔥 ОСТАЛЬНЫЕ СТАТИЧЕСКИЕ МЕТОДЫ БЕЗ ИЗМЕНЕНИЙ

    @staticmethod
    def contains_exclude_keywords(text, exclude_keywords):
        """Проверяет, содержит ли текст исключаемые слова"""
        if not exclude_keywords or not text:
            return False

        text_lower = text.lower()
        for keyword in exclude_keywords:
            if keyword and keyword.lower() in text_lower:
                logger.info(f"🚫 Найдено исключаемое слово: '{keyword}'")
                return True
        return False

    @staticmethod
    def is_fresh_product(product):
        """🔥 ОПРЕДЕЛЯЕТ УРОВЕНЬ СВЕЖЕСТИ товара (НЕ ОТСЕИВАЕТ!)"""
        try:
            time_listed = product.get('time_listed', 24)
            posted_date = product.get('posted_date', '')
            name = product.get('name', '')[:50]

            freshness_level = "old"

            # 🚨 КРИТИЧЕСКИ СВЕЖИЕ (первые 30 минут)
            if time_listed <= 0.5:  # 30 минут
                freshness_level = "critical_fresh"
                logger.info(f"🚨 КРИТИЧЕСКИ СВЕЖИЙ (<30мин): {name}...")

            # 🔥 ОЧЕНЬ СВЕЖИЕ (первые 2 часа)
            elif time_listed <= 2:
                freshness_level = "very_fresh"
                logger.info(f"🔥 ОЧЕНЬ СВЕЖИЙ (<2ч): {name}...")

            # ✅ СВЕЖИЕ (первые 6 часов)
            elif time_listed <= 6:
                freshness_level = "fresh"
                logger.info(f"✅ СВЕЖИЙ (<6ч): {name}...")

            # 📦 СЕГОДНЯШНИЕ
            elif 'сегодня' in str(posted_date).lower():
                freshness_level = "today"
                logger.info(f"📦 СЕГОДНЯШНИЙ: {name}...")

            # ⏰ ВЧЕРАШНИЕ
            elif 'вчера' in str(posted_date).lower():
                freshness_level = "yesterday"
                logger.info(f"⏰ ВЧЕРАШНИЙ: {name}...")

            else:
                freshness_level = "old"
                logger.info(f"💤 СТАРЫЙ ТОВАР (>24ч): {name}...")

            # 🔥 СОХРАНЯЕМ УРОВЕНЬ СВЕЖЕСТИ ДЛЯ СОРТИРОВКИ
            product['freshness_level'] = freshness_level
            product['freshness_priority'] = ProductValidator._get_freshness_priority(freshness_level)

            # 🔥 ВСЕГДА ВОЗВРАЩАЕМ True - НЕ ОТСЕИВАЕМ ТОВАРЫ!
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки свежести: {e}")
            product['freshness_level'] = "unknown"
            product['freshness_priority'] = 5
            return True

    @staticmethod
    def _get_freshness_priority(freshness_level):
        """Возвращает числовой приоритет для сортировки"""
        priority_map = {
            "critical_fresh": 100,  # Самый высокий приоритет
            "very_fresh": 80,
            "fresh": 60,
            "today": 50,
            "yesterday": 30,
            "old": 10,
            "unknown": 5
        }
        return priority_map.get(freshness_level, 5)

    @staticmethod
    def parse_price(price_text):
        """УМНЫЙ парсинг цены"""
        try:
            if not price_text:
                return 0

            # Убираем все символы кроме цифр
            digits = ''.join(filter(str.isdigit, str(price_text)))
            price = int(digits) if digits else 0

            # Проверяем на аномально высокие цены (больше 100 млн)
            if price > 100000000:
                logger.warning(f"⚠️ Подозрительно высокая цена: {price}₽")
                return 0

            return price

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга цены '{price_text}': {e}")
            return 0

    @staticmethod
    def validate_product_filters(product, min_price=0, max_price=100000, min_rating=0, seller_type='all'):
        """Проверяет товар по фильтрам"""
        try:
            price = product.get('price', 0)

            if price < min_price or price > max_price:
                logger.info(f"💰 Цена не в диапазоне: {price}₽ (требуется: {min_price}-{max_price}₽)")
                return False

            if min_rating > 0 and product.get('seller_rating', 0) < min_rating:
                logger.info(f"⭐ Рейтинг слишком низкий: {product.get('seller_rating')}")
                return False

            if seller_type != 'all':
                is_professional = product.get('reviews_count', 0) > 150
                if seller_type == 'private' and is_professional:
                    logger.info(f"👤 Неподходящий тип продавца: профессиональный")
                    return False
                if seller_type == 'professional' and not is_professional:
                    logger.info(f"👤 Неподходящий тип продавца: частный")
                    return False

            logger.info(f"🎯 Товар прошел все фильтры: {product.get('name', '')[:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки фильтров: {e}")
            return False

    @staticmethod
    def check_price_range(price, min_price=0, max_price=100000):
        """Проверяет цену в допустимом диапазоне"""
        return min_price <= price <= max_price

    @staticmethod
    def check_seller_rating(rating, min_rating=0):
        """Проверяет рейтинг продавца"""
        return rating >= min_rating if rating else True

    @staticmethod
    def check_seller_type(product, seller_type='all'):
        """Проверяет тип продавца"""
        if seller_type == 'all':
            return True

        is_professional = product.get('reviews_count', 0) > 150 or product.get('is_professional', False)

        if seller_type == 'private' and is_professional:
            return False
        if seller_type == 'professional' and not is_professional:
            return False

        return True

    @staticmethod
    def validate_product_comprehensive(product, min_price=0, max_price=100000, min_rating=0, seller_type='all'):
        """Комплексная проверка товара со всеми фильтрами"""
        try:
            # Проверка цены
            if not ProductValidator.check_price_range(product.get('price', 0), min_price, max_price):
                logger.info(f"💰 Цена не в диапазоне: {product.get('price', 0)}₽")
                return False

            # Проверка рейтинга продавца
            if not ProductValidator.check_seller_rating(product.get('seller_rating'), min_rating):
                logger.info(f"⭐ Рейтинг слишком низкий: {product.get('seller_rating')}")
                return False

            # Проверка типа продавца
            if not ProductValidator.check_seller_type(product, seller_type):
                logger.info(f"👤 Неподходящий тип продавца")
                return False

            logger.info(f"🎯 Товар прошел все фильтры: {product.get('name', '')[:50]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка комплексной проверки: {e}")
            return False

    @staticmethod
    def calculate_profit_percentage(price, target_price):
        """Рассчитывает процент прибыли"""
        if target_price <= 0 or price <= 0:
            return 0
        return ((target_price - price) / target_price) * 100

    @staticmethod
    def is_high_profit_deal(product, min_profit_percent=20):
        """Проверяет, является ли сделка высокоприбыльной"""
        try:
            price = product.get('price', 0)
            target_price = product.get('target_price', 0)

            if target_price <= 0:
                return False

            profit_percent = ProductValidator.calculate_profit_percentage(price, target_price)

            if profit_percent >= min_profit_percent:
                logger.info(f"💰 ВЫСОКАЯ ПРИБЫЛЬ: {profit_percent:.1f}% ({price}₽ → {target_price}₽)")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка расчета прибыли: {e}")
            return False