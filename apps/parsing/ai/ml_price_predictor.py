import logging
import numpy as np
import pandas as pd
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger('parser.ai')


class MLPricePredictor:
    def __init__(self, db_path="ml_knowledge.db"):
        self.model_version = "v3.0_ultra_smart"
        self.db_path = db_path

        # 🔥 ОСНОВНЫЕ МОДЕЛИ
        self.price_model = None  # Для предсказания цены
        self.freshness_model = None  # Для предсказания свежести
        self.scaler_price = None
        self.scaler_freshness = None
        self.is_trained = False  # Для совместимости с парсером
        self.model = None  # Для совместимости
        self.feature_scaler = None  # Для совместимости

        # 🔥 ФЛАГИ ОБУЧЕНИЯ
        self.is_price_trained = False
        self.is_freshness_trained = False

        # 🔥 КОНФИГУРАЦИЯ
        self.config = {
            'price_features_count': 35,
            'freshness_features_count': 15,
            'min_training_samples': 50,
            'max_training_samples': 10000,
            'validation_split': 0.2,
            'model_update_frequency': 100
        }

        # 🔥 ИНИЦИАЛИЗАЦИЯ ПАТТЕРНОВ
        self._initialize_patterns()

        # 🔥 ЛОГИ
        self.training_log = []

        logger.info(f"🧠 Инициализирован Advanced ML Predictor v{self.model_version}")

    async def initialize_model(self):
        """🚀 Инициализация модели (для совместимости с парсером)"""
        try:
            logger.info("🚀 Инициализация ML модели...")
            # Используем существующий метод
            return await self.initialize_all_models()
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации модели: {e}")
            return await self.load_model()  # Фолбэк

    async def load_freshness_model(self):
        """🎯 Загрузка модели свежести (для совместимости с парсером)"""
        try:
            logger.info("🎯 Загрузка модели свежести...")
            # Используем приватный метод
            return await self._load_freshness_model()
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели свежести: {e}")
            return False

    async def predict_price(self, product_data):
        """💰 Предсказание цены (для совместимости с парсером)"""
        try:
            return await self.predict_price_ultra(product_data)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка predict_price: {e}")
            return float(product_data.get('price', 0)) * 1.2

    async def predict_freshness(self, product_data):
        """🎯 Предсказание свежести (для совместимости с парсером)"""
        try:
            return await self.predict_freshness_ultra(product_data)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка predict_freshness: {e}")
            hours_since = self._get_hours_since_publication(product_data)
            return self._calculate_time_based_freshness(hours_since)

    def _initialize_patterns(self):
        """🎯 Инициализация паттернов для анализа"""

        # 📊 БРЕНДЫ
        self.brand_patterns = {
            'apple': ['iphone', 'macbook', 'ipad', 'airpods', 'apple watch', 'imac'],
            'samsung': ['samsung', 'galaxy', 'note', 'fold', 'flip'],
            'xiaomi': ['xiaomi', 'redmi', 'poco', 'mi ', 'redmi note'],
            'huawei': ['huawei', 'honor', 'p series', 'mate'],
            'sony': ['sony', 'playstation', 'ps5', 'ps4', 'xperia'],
            'nike': ['nike', 'air force', 'air max', 'jordan'],
            'adidas': ['adidas', 'yeezy', 'ultraboost', 'stan smith']
        }

        # 📊 КЛЮЧЕВЫЕ СЛОВА СОСТОЯНИЯ (ИСПРАВЛЕННЫЙ ФОРМАТ!)
        self.condition_keywords = {
            'perfect': {
                'keywords': ['новый', 'не использовался', 'с гарантией', 'оригинал', 'заводская упаковка'],
                'weight': 1.2  # +20% к цене
            },
            'excellent': {
                'keywords': ['отличное состояние', 'как новый', 'почти не использовался', 'идеальное'],
                'weight': 1.1  # +10% к цене
            },
            'good': {
                'keywords': ['хорошее состояние', 'небольшие следы', 'мягкие потертости', 'работает идеально'],
                'weight': 1.0  # базовая цена
            },
            'satisfactory': {
                'keywords': ['удовлетворительное', 'царапины', 'потертости', 'следы использования'],
                'weight': 0.9  # -10% от цены
            },
            'bad': {
                'keywords': ['требует ремонта', 'не работает', 'сломан', 'б/у в плохом состоянии'],
                'weight': 0.7  # -30% от цены
            }
        }

        # 📊 ИНДИКАТОРЫ СВЕЖЕСТИ
        self.freshness_indicators = {
            'time_keywords': ['только что', 'сегодня', 'минут', 'час', 'свежий'],
            'urgency_keywords': ['срочно', 'быстро', 'срочная продажа'],
            'new_keywords': ['новый', 'не использовался', 'с гарантией', 'оригинал']
        }

    async def initialize_all_models(self):
        """🚀 ИНИЦИАЛИЗАЦИЯ ВСЕХ МОДЕЛЕЙ СРАЗУ"""
        try:
            logger.info("🔄 Запуск полной инициализации моделей...")

            # Пытаемся загрузить сохраненные модели
            price_loaded = await self._load_price_model()
            freshness_loaded = await self._load_freshness_model()

            # Если не загрузились - обучаем
            if not price_loaded:
                logger.info("🎯 Обучение модели цены...")
                await self.train_price_model_full()

            if not freshness_loaded:
                logger.info("🎯 Обучение модели свежести...")
                await self.train_freshness_model_full()

            logger.info("✅ Все модели готовы к работе!")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False

    async def train_price_model_full(self):
        """🎯 ПОЛНОЕ ОБУЧЕНИЕ МОДЕЛИ ЦЕНЫ НА ВСЕХ ДАННЫХ"""
        try:
            from apps.website.models import FoundItem
            from asgiref.sync import sync_to_async

            logger.info("🔍 Загрузка ВСЕХ товаров для обучения модели цены...")

            # 🔥 ЗАГРУЖАЕМ ВСЕ ТОВАРЫ БЕЗ ОГРАНИЧЕНИЙ
            items = await sync_to_async(list)(
                FoundItem.objects.filter(
                    price__isnull=False,
                    price__gt=0
                ).values(
                    'id', 'title', 'description', 'price', 'category',
                    'seller_rating', 'reviews_count', 'posted_date',
                    'found_at', 'ml_freshness_score', 'views_count',
                    'address', 'metro_stations'
                ).order_by('-found_at')[:self.config['max_training_samples']]
            )

            total_items = len(items)
            logger.info(f"📚 Загружено {total_items} товаров для обучения цены")

            if total_items < self.config['min_training_samples']:
                logger.warning(f"⚠️ Мало данных: {total_items} товаров")
                return await self._train_fallback_price_model()

            # 🔥 ПОДГОТОВКА ДАННЫХ
            X, y = [], []

            for i, item in enumerate(items, 1):
                try:
                    # Проверяем что price не None и можно преобразовать в float
                    price_str = item.get('price')
                    if price_str is None:
                        continue

                    price = float(price_str)
                    if price <= 0:
                        continue

                    features = self._extract_ultra_features(item)
                    if features and len(features) == self.config['price_features_count']:
                        X.append(features)
                        y.append(price)

                    if i % 1000 == 0:
                        logger.info(f"🔄 Обработано {i}/{total_items} товаров")

                except (ValueError, TypeError) as e:
                    # Пропускаем товары с некорректной ценой
                    continue

            valid_samples = len(X)
            logger.info(f"✅ Получено {valid_samples} валидных samples для обучения")

            if valid_samples < self.config['min_training_samples']:
                logger.warning(f"⚠️ Слишком мало валидных данных: {valid_samples}")
                return await self._train_fallback_price_model()

            # 🔥 РАЗДЕЛЕНИЕ ДАННЫХ
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config['validation_split'], random_state=42
            )

            # 🔥 ПРЕПРОЦЕССИНГ
            self.scaler_price = RobustScaler()
            X_train_scaled = self.scaler_price.fit_transform(X_train)
            X_test_scaled = self.scaler_price.transform(X_test)

            # 🔥 ОБУЧЕНИЕ УЛЬТРА-МОДЕЛИ
            rf_model = RandomForestRegressor(
                n_estimators=200,
                max_depth=30,
                min_samples_split=3,
                min_samples_leaf=1,
                max_features='sqrt',
                bootstrap=True,
                random_state=42,
                n_jobs=-1
            )

            gb_model = GradientBoostingRegressor(
                n_estimators=150,
                max_depth=15,
                learning_rate=0.1,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )

            # 🔥 АНСАМБЛЬ
            self.price_model = VotingRegressor([
                ('rf', rf_model),
                ('gb', gb_model)
            ])

            # Кросс-валидация
            cv_scores = cross_val_score(
                self.price_model, X_train_scaled, y_train,
                cv=min(3, len(X_train) // 100),
                scoring='r2',
                n_jobs=-1
            )

            # Финальное обучение
            self.price_model.fit(X_train_scaled, y_train)

            # 🔥 ВАЛИДАЦИЯ
            y_pred = self.price_model.predict(X_test_scaled)

            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred),
                'mape': np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100
            }

            # 🔥 ДЕТАЛЬНЫЙ ЛОГ
            self.training_log.append({
                'model': 'price',
                'timestamp': datetime.now().isoformat(),
                'samples': valid_samples,
                'metrics': metrics,
                'cv_scores': cv_scores.tolist()
            })

            logger.info(f"🚀 МОДЕЛЬ ЦЕНЫ ОБУЧЕНА НА {valid_samples} ТОВАРАХ!")
            logger.info(f"📊 Метрики модели:")
            logger.info(f"   • MAE: {metrics['mae']:.0f} руб")
            logger.info(f"   • RMSE: {metrics['rmse']:.0f} руб")
            logger.info(f"   • R²: {metrics['r2']:.4f}")
            logger.info(f"   • MAPE: {metrics['mape']:.1f}%")
            logger.info(f"   • CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

            # 🔥 АНАЛИЗ ВАЖНОСТИ ФИЧЕЙ
            if hasattr(rf_model, 'feature_importances_'):
                importances = rf_model.feature_importances_
                top_indices = np.argsort(importances)[-5:][::-1]
                logger.info(f"🎯 Топ-5 важных фичей:")
                for idx in top_indices:
                    logger.info(f"   • Фича {idx}: {importances[idx]:.4f}")

            # 🔥 СОХРАНЕНИЕ
            await self._save_price_model()
            self.is_price_trained = True

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обучения модели цены: {e}")
            import traceback
            traceback.print_exc()
            return await self._train_fallback_price_model()

    async def train_freshness_model_full(self):
        """🎯 ПОЛНОЕ ОБУЧЕНИЕ МОДЕЛИ СВЕЖЕСТИ"""
        try:
            from apps.website.models import FoundItem
            from asgiref.sync import sync_to_async

            logger.info("🔍 Загрузка ВСЕХ товаров для обучения свежести...")

            # 🔥 БЕРЕМ ВСЕ ТОВАРЫ С ОЦЕНКОЙ СВЕЖЕСТИ
            items = await sync_to_async(list)(
                FoundItem.objects.filter(
                    ml_freshness_score__isnull=False
                ).values(
                    'id', 'title', 'description', 'category',
                    'seller_rating', 'reviews_count', 'posted_date',
                    'found_at', 'ml_freshness_score', 'views_count',
                    'price'
                ).order_by('-found_at')[:self.config['max_training_samples']]
            )

            total_items = len(items)
            logger.info(f"📚 Загружено {total_items} товаров для обучения свежести")

            if total_items < self.config['min_training_samples']:
                logger.warning("⚠️ Мало данных для обучения свежести")
                return await self._train_fallback_freshness_model()

            # 🔥 ПОДГОТОВКА ДАННЫХ
            X, y = [], []

            for item in items:
                features = self._extract_freshness_features(item)
                freshness_score = float(item.get('ml_freshness_score', 0.5))

                if features and len(features) == self.config['freshness_features_count']:
                    X.append(features)
                    y.append(freshness_score)

            valid_samples = len(X)
            logger.info(f"✅ Получено {valid_samples} валидных samples для свежести")

            if valid_samples < self.config['min_training_samples']:
                return await self._train_fallback_freshness_model()

            # 🔥 РАЗДЕЛЕНИЕ
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config['validation_split'], random_state=42
            )

            # 🔥 ПРЕПРОЦЕССИНГ
            self.scaler_freshness = StandardScaler()
            X_train_scaled = self.scaler_freshness.fit_transform(X_train)
            X_test_scaled = self.scaler_freshness.transform(X_test)

            # 🔥 ОБУЧЕНИЕ МОДЕЛИ СВЕЖЕСТИ
            self.freshness_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )

            # Кросс-валидация
            cv_scores = cross_val_score(
                self.freshness_model, X_train_scaled, y_train,
                cv=min(3, len(X_train) // 100),
                scoring='r2'
            )

            # Финальное обучение
            self.freshness_model.fit(X_train_scaled, y_train)

            # 🔥 ВАЛИДАЦИЯ
            y_pred = self.freshness_model.predict(X_test_scaled)

            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred)
            }

            # 🔥 ЛОГ
            self.training_log.append({
                'model': 'freshness',
                'timestamp': datetime.now().isoformat(),
                'samples': valid_samples,
                'metrics': metrics,
                'cv_scores': cv_scores.tolist()
            })

            logger.info(f"🎯 МОДЕЛЬ СВЕЖЕСТИ ОБУЧЕНА НА {valid_samples} ТОВАРАХ!")
            logger.info(f"📊 Метрики свежести:")
            logger.info(f"   • MAE: {metrics['mae']:.4f}")
            logger.info(f"   • RMSE: {metrics['rmse']:.4f}")
            logger.info(f"   • R²: {metrics['r2']:.4f}")
            logger.info(f"   • CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

            # 🔥 СОХРАНЕНИЕ
            await self._save_freshness_model()
            self.is_freshness_trained = True

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обучения свежести: {e}")
            return await self._train_fallback_freshness_model()

    def _extract_ultra_features(self, item):
        """🔮 ИЗВЛЕЧЕНИЕ УЛЬТРА-ФИЧ ДЛЯ ЦЕНЫ"""
        try:
            title = str(item.get('title', '')).lower()
            description = str(item.get('description', '')).lower()
            category = str(item.get('category', ''))

            features = []

            # 🔥 ТЕКСТОВЫЕ ФИЧИ (10 фич)
            text_features = self._extract_text_features(title, description)
            features.extend(text_features)

            # 🔥 БРЕНДОВЫЕ ФИЧИ (5 фич)
            brand_features = self._extract_brand_features(title)
            features.extend(brand_features)

            # 🔥 ФИЧИ СОСТОЯНИЯ (5 фич)
            condition_features = self._extract_condition_features(title, description)
            features.extend(condition_features)

            # 🔥 ФИЧИ ПРОДАВЦА (5 фич)
            seller_features = self._extract_seller_features(item)
            features.extend(seller_features)

            # 🔥 ВРЕМЕННЫЕ ФИЧИ (5 фич)
            time_features = self._extract_time_features(item)
            features.extend(time_features)

            # 🔥 ДОПОЛНИТЕЛЬНЫЕ ФИЧИ (5 фич)
            extra_features = self._extract_extra_features(item)
            features.extend(extra_features)

            # 🔥 ГАРАНТИЯ РАЗМЕРА
            if len(features) < self.config['price_features_count']:
                features.extend([0.0] * (self.config['price_features_count'] - len(features)))
            elif len(features) > self.config['price_features_count']:
                features = features[:self.config['price_features_count']]

            return features

        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения фич: {e}")
            return [0.0] * self.config['price_features_count']

    def _extract_freshness_features(self, item):
        """🔍 ИЗВЛЕЧЕНИЕ ФИЧ ДЛЯ СВЕЖЕСТИ"""
        try:
            title = str(item.get('title', '')).lower()
            description = str(item.get('description', '')).lower()

            features = []

            # 🔥 ВРЕМЯ ПУБЛИКАЦИИ
            hours_since = self._get_hours_since_publication(item)
            features.append(min(hours_since / 168, 1.0))  # Нормализация до недели

            # 🔥 ТЕКСТОВЫЕ ИНДИКАТОРЫ
            text = f"{title} {description}"

            # Индикаторы срочности
            urgency_score = 0.0
            for word in self.freshness_indicators['urgency_keywords']:
                if word in text:
                    urgency_score += 0.2
            features.append(min(urgency_score, 1.0))

            # Индикаторы новизны
            new_score = 0.0
            for word in self.freshness_indicators['new_keywords']:
                if word in text:
                    new_score += 0.25
            features.append(min(new_score, 1.0))

            # Индикаторы времени
            time_score = 0.0
            for word in self.freshness_indicators['time_keywords']:
                if word in text:
                    time_score += 0.3
            features.append(min(time_score, 1.0))

            # 🔥 ПРОДАВЕЦ
            seller_rating = float(item.get('seller_rating', 0))
            reviews_count = float(item.get('reviews_count', 0))

            features.append(seller_rating / 5.0)  # Нормализация
            features.append(min(reviews_count / 1000, 1.0))  # Нормализация

            # 🔥 АКТИВНОСТЬ
            views_count = float(item.get('views_count', 0))
            features.append(min(views_count / 500, 1.0))

            # 🔥 КАЧЕСТВО ОПИСАНИЯ
            features.append(min(len(title) / 100, 1.0))
            features.append(min(len(description) / 500, 1.0))

            # 🔥 ЦЕНА (дорогие товары могут быть свежее)
            price = float(item.get('price', 0))
            features.append(min(price / 100000, 1.0) if price > 0 else 0.0)

            # 🔥 ДОПОЛНИТЕЛЬНЫЕ
            category = str(item.get('category', ''))
            features.append(1.0 if 'iphone' in category.lower() else 0.0)
            features.append(1.0 if 'apple' in title else 0.0)

            # 🔥 ГАРАНТИЯ РАЗМЕРА
            if len(features) < self.config['freshness_features_count']:
                features.extend([0.0] * (self.config['freshness_features_count'] - len(features)))

            return features[:self.config['freshness_features_count']]

        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения фич свежести: {e}")
            return [0.0] * self.config['freshness_features_count']

    def _extract_text_features(self, title, description):
        """📝 Текстовые фичи"""
        text = f"{title} {description}"

        return [
            min(len(title) / 100, 1.0),  # Длина заголовка
            min(len(description) / 500, 1.0),  # Длина описания
            min(title.count(' ') / 20, 1.0),  # Количество слов в заголовке
            min(description.count(' ') / 50, 1.0),  # Количество слов в описании
            1.0 if 'iphone' in title else 0.0,  # Содержит iPhone
            1.0 if 'про' in title else 0.0,  # Содержит "про"
            1.0 if 'max' in title else 0.0,  # Содержит "max"
            1.0 if 'gb' in title or 'гб' in title else 0.0,  # Указана память
            1.0 if '202' in title else 0.0,  # Указан год
            min(text.count('!') / 5, 1.0)  # Восклицательные знаки
        ]

    def _extract_brand_features(self, title):
        """🏷️ Брендовые фичи"""
        brand_score = 0.0
        premium_brand = 0.0

        for brand, patterns in self.brand_patterns.items():
            for pattern in patterns:
                if pattern in title:
                    brand_score = 1.0
                    if brand in ['apple', 'samsung', 'sony']:
                        premium_brand = 1.0
                    break

        return [
            brand_score,
            premium_brand,
            1.0 if 'pro' in title else 0.0,
            1.0 if 'ultra' in title else 0.0,
            1.0 if 'plus' in title else 0.0
        ]

    def _extract_condition_features(self, title, description):
        """🔍 Фичи состояния"""
        text = f"{title} {description}"

        condition_scores = [0.0] * 5

        for i, (condition, data) in enumerate(self.condition_keywords.items()):
            for keyword in data['keywords']:
                if keyword in text:
                    condition_scores[i] = data['weight']
                    break

        return condition_scores

    def _extract_seller_features(self, item):
        """👤 Фичи продавца"""
        seller_rating = float(item.get('seller_rating', 0))
        reviews_count = float(item.get('reviews_count', 0))

        return [
            seller_rating / 5.0,  # Нормализованный рейтинг
            min(reviews_count / 1000, 1.0),  # Нормализованные отзывы
            1.0 if seller_rating > 4.5 else 0.0,  # Высокий рейтинг
            1.0 if reviews_count > 100 else 0.0,  # Много отзывов
            1.0 if seller_rating > 4.8 and reviews_count > 50 else 0.0  # Топ продавец
        ]

    def _extract_time_features(self, item):
        """⏰ Временные фичи"""
        try:
            found_at = item.get('found_at')
            if found_at:
                if isinstance(found_at, str):
                    found_at = datetime.fromisoformat(found_at.replace('Z', '+00:00'))

                now = datetime.now().replace(tzinfo=found_at.tzinfo) if found_at.tzinfo else datetime.now()
                hours_ago = (now - found_at).total_seconds() / 3600

                return [
                    min(hours_ago / 168, 1.0),  # Нормализация до недели
                    1.0 if hours_ago < 1 else 0.0,  # Очень свежее
                    1.0 if hours_ago < 24 else 0.0,  # Сегодняшнее
                    1.0 if hours_ago > 168 else 0.0,  # Больше 1 недели
                    min(hours_ago / 24, 1.0)  # Нормализация до дней
                ]
        except:
            pass

        return [0.5, 0.0, 0.0, 0.0, 0.5]

    def _extract_extra_features(self, item):
        """➕ Дополнительные фичи"""
        views_count = float(item.get('views_count', 0))
        price = float(item.get('price', 0))

        return [
            min(views_count / 1000, 1.0),  # Просмотры
            min(price / 200000, 1.0) if price > 0 else 0.0,  # Цена
            1.0 if len(item.get('metro_stations', [])) > 0 else 0.0,  # Метро
            1.0 if item.get('address') else 0.0,  # Адрес
            min(len(item.get('images', [])) / 10, 1.0)  # Фотографии
        ]

    def _get_hours_since_publication(self, item):
        """⏰ Расчет часов с публикации"""
        try:
            posted_date = item.get('posted_date')
            if posted_date:
                if isinstance(posted_date, str):
                    posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))

                now = datetime.now()
                hours_ago = (now - posted_date).total_seconds() / 3600
                return hours_ago

            found_at = item.get('found_at')
            if found_at:
                if isinstance(found_at, str):
                    found_at = datetime.fromisoformat(found_at.replace('Z', '+00:00'))

                now = datetime.now().replace(tzinfo=found_at.tzinfo) if found_at.tzinfo else datetime.now()
                hours_ago = (now - found_at).total_seconds() / 3600
                return hours_ago
        except:
            pass

        return 24.0  # По умолчанию

    async def predict_price_ultra(self, product_data):
        """🎯 УЛЬТРА-ПРЕДСКАЗАНИЕ ЦЕНЫ"""
        try:
            if not self.is_price_trained or not self.price_model or not self.scaler_price:
                await self.train_price_model_full()

            features = self._extract_ultra_features(product_data)

            # Проверяем размерность
            if len(features) != self.config['price_features_count']:
                logger.warning(f"⚠️ Неправильное количество фичей: {len(features)}")
                features = [0.0] * self.config['price_features_count']

            features_scaled = self.scaler_price.transform([features])
            predicted_price = self.price_model.predict(features_scaled)[0]

            # 🔥 ПОСТ-ОБРАБОТКА
            original_price = float(product_data.get('price', 0))

            if original_price > 0:
                # Умная коррекция
                correction_factor = self._calculate_price_correction(product_data)
                final_price = predicted_price * correction_factor

                # Защита от аномалий
                if abs(final_price - original_price) / original_price > 2.0:
                    final_price = original_price * 1.3  # Безопасная коррекция
            else:
                final_price = predicted_price

            logger.info(f"🎯 Предсказана цена: {final_price:.0f} руб (оригинал: {original_price:.0f} руб)")

            return max(1000, final_price)  # Минимум 1000 руб

        except Exception as e:
            logger.warning(f"⚠️ Ошибка предсказания цены: {e}")
            return float(product_data.get('price', 0)) * 1.2

    async def predict_freshness_ultra(self, product_data):
        """🎯 УЛЬТРА-ПРЕДСКАЗАНИЕ СВЕЖЕСТИ"""
        try:
            if not self.is_freshness_trained or not self.freshness_model or not self.scaler_freshness:
                await self.train_freshness_model_full()

            features = self._extract_freshness_features(product_data)

            # Проверяем размерность
            if len(features) != self.config['freshness_features_count']:
                features = [0.0] * self.config['freshness_features_count']

            features_scaled = self.scaler_freshness.transform([features])
            freshness_score = self.freshness_model.predict(features_scaled)[0]

            # 🔥 ДОПОЛНИТЕЛЬНАЯ КОРРЕКЦИЯ ПО ВРЕМЕНИ
            hours_since = self._get_hours_since_publication(product_data)
            time_based_freshness = self._calculate_time_based_freshness(hours_since)

            # Комбинируем модели
            final_freshness = freshness_score * 0.7 + time_based_freshness * 0.3

            # Ограничиваем
            final_freshness = max(0.0, min(1.0, final_freshness))

            logger.info(f"🎯 Предсказана свежесть: {final_freshness:.3f} (часов: {hours_since:.1f})")

            return final_freshness

        except Exception as e:
            logger.warning(f"⚠️ Ошибка предсказания свежести: {e}")
            hours_since = self._get_hours_since_publication(product_data)
            return self._calculate_time_based_freshness(hours_since)

    def _calculate_price_correction(self, product_data):
        """🔧 Расчет коррекции цены"""
        correction = 1.0

        title = str(product_data.get('title', '')).lower()
        description = str(product_data.get('description', '')).lower()
        text = f"{title} {description}"

        # Состояние
        for condition, data in self.condition_keywords.items():
            for keyword in data['keywords']:
                if keyword in text:
                    correction *= data['weight']
                    break

        # Продавец
        seller_rating = float(product_data.get('seller_rating', 0))
        if seller_rating > 4.8:
            correction *= 1.05
        elif seller_rating < 3.5:
            correction *= 0.95

        # Свежесть
        freshness = float(product_data.get('ml_freshness_score', 0.5))
        if freshness > 0.8:
            correction *= 1.08
        elif freshness < 0.3:
            correction *= 0.9

        return max(0.5, min(2.0, correction))  # Ограничения

    def _calculate_time_based_freshness(self, hours_since):
        """⏰ Расчет свежести на основе времени"""
        if hours_since < 0.5:  # 30 минут
            return 0.95
        elif hours_since < 1:  # 1 час
            return 0.92
        elif hours_since < 3:  # 3 часа
            return 0.88
        elif hours_since < 6:  # 6 часов
            return 0.80
        elif hours_since < 12:  # 12 часов
            return 0.70
        elif hours_since < 24:  # 1 день
            return 0.55
        elif hours_since < 48:  # 2 дня
            return 0.40
        elif hours_since < 72:  # 3 дня
            return 0.25
        elif hours_since < 96:  # 4 дня
            return 0.15
        elif hours_since < 120:  # 5 дней
            return 0.10
        elif hours_since < 144:  # 6 дней
            return 0.07
        elif hours_since < 168:  # 1 неделя
            return 0.05
        else:  # > 1 недели
            return 0.03

    async def _train_fallback_price_model(self):
        """🔄 Фолбэк модель цены"""
        try:
            from sklearn.linear_model import LinearRegression

            # Синтетические данные
            X = [[i * 0.1 for _ in range(self.config['price_features_count'])]
                 for i in range(100)]
            y = [10000 + i * 500 for i in range(100)]

            self.scaler_price = StandardScaler()
            X_scaled = self.scaler_price.fit_transform(X)

            self.price_model = LinearRegression()
            self.price_model.fit(X_scaled, y)
            self.is_price_trained = True

            logger.info("🔄 Фолбэк модель цены обучена")
            return True
        except:
            return False

    async def _train_fallback_freshness_model(self):
        """🔄 Фолбэк модель свежести"""
        try:
            # Простая модель
            X = [[i * 0.1 for _ in range(self.config['freshness_features_count'])]
                 for i in range(50)]
            y = [0.9 - i * 0.02 for i in range(50)]

            self.scaler_freshness = StandardScaler()
            X_scaled = self.scaler_freshness.fit_transform(X)

            self.freshness_model = RandomForestRegressor(n_estimators=10, random_state=42)
            self.freshness_model.fit(X_scaled, y)
            self.is_freshness_trained = True

            logger.info("🔄 Фолбэк модель свежести обучена")
            return True
        except:
            return False

    async def _save_price_model(self):
        """💾 Сохранение модели цены"""
        try:
            if self.price_model and self.scaler_price:
                joblib.dump(self.price_model, 'ultra_price_model.joblib')
                joblib.dump(self.scaler_price, 'ultra_price_scaler.joblib')

                model_info = {
                    'version': self.model_version,
                    'saved_at': datetime.now().isoformat(),
                    'feature_count': self.config['price_features_count'],
                    'training_log': self.training_log[-5:]  # 5 последних логов
                }

                with open('ultra_price_model_info.json', 'w', encoding='utf-8') as f:
                    json.dump(model_info, f, ensure_ascii=False, indent=2)

                logger.info("💾 Ультра-модель цены сохранена")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить модель цены: {e}")

    async def _save_freshness_model(self):
        """💾 Сохранение модели свежести"""
        try:
            if self.freshness_model and self.scaler_freshness:
                joblib.dump(self.freshness_model, 'ultra_freshness_model.joblib')
                joblib.dump(self.scaler_freshness, 'ultra_freshness_scaler.joblib')

                freshness_info = {
                    'version': self.model_version,
                    'saved_at': datetime.now().isoformat(),
                    'feature_count': self.config['freshness_features_count'],
                    'training_log': self.training_log[-5:]
                }

                with open('ultra_freshness_model_info.json', 'w', encoding='utf-8') as f:
                    json.dump(freshness_info, f, ensure_ascii=False, indent=2)

                logger.info("💾 Ультра-модель свежести сохранена")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить модель свежести: {e}")

    async def _load_price_model(self):
        """📂 Загрузка модели цены"""
        try:
            # 🔥 ФИКС: ultra_price_model.joblib - это СЛОВАРЬ!
            model_data = joblib.load('ultra_price_model.joblib')

            # Извлекаем модель из словаря
            if isinstance(model_data, dict) and 'model' in model_data:
                self.price_model = model_data['model']
                self.scaler_price = model_data.get('scaler', StandardScaler())
                logger.info(f"✅ Модель цены извлечена из словаря: {type(self.price_model).__name__}")
            else:
                self.price_model = model_data
                self.scaler_price = joblib.load('ultra_price_scaler.joblib')

            self.is_price_trained = True
            logger.info("📂 Ультра-модель цены загружена")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить модель цены: {e}")
            return False

    async def _load_freshness_model(self):
        """📂 Загрузка модели свежести"""
        try:
            self.freshness_model = joblib.load('ultra_freshness_model.joblib')
            self.scaler_freshness = joblib.load('ultra_freshness_scaler.joblib')
            self.is_freshness_trained = True

            logger.info("📂 Ультра-модель свежести загружена")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить модель свежести: {e}")
            return False

    async def get_model_stats(self):
        """📊 Статистика моделей"""
        try:
            stats = {
                'model_version': self.model_version,
                'price_model_trained': self.is_price_trained,
                'freshness_model_trained': self.is_freshness_trained,
                'price_feature_count': self.config['price_features_count'],
                'freshness_feature_count': self.config['freshness_features_count'],
                'last_training': None,
                'training_log_count': len(self.training_log)
            }

            if self.training_log:
                last_training = self.training_log[-1]
                stats['last_training'] = last_training.get('timestamp')
                stats['last_training_samples'] = last_training.get('samples', 0)

                if 'metrics' in last_training:
                    stats['last_price_r2'] = last_training['metrics'].get('r2', 0)
                    stats['last_freshness_r2'] = last_training['metrics'].get('r2', 0)

            return stats

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}

    async def load_model(self):
        """📂 Загрузка всех моделей (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
        try:
            logger.info("📂 Загрузка ML моделей...")

            price_loaded = False
            freshness_loaded = False

            # 1. Загружаем модель цены
            try:
                model_data = joblib.load('ultra_price_model.joblib')

                # 🔥 ФИКС: Извлекаем из словаря
                if isinstance(model_data, dict) and 'model' in model_data:
                    self.price_model = model_data['model']
                    self.scaler_price = model_data.get('scaler', StandardScaler())
                    logger.info(f"✅ Модель цены извлечена: {type(self.price_model).__name__}")
                else:
                    # Если это уже модель (не словарь)
                    self.price_model = model_data
                    try:
                        self.scaler_price = joblib.load('ultra_price_scaler.joblib')
                    except:
                        self.scaler_price = StandardScaler()

                price_loaded = True
                logger.info("✅ Ультра-модель цены загружена")

                # 🔥 ВАЖНО: Дублируем для совместимости
                self.model = self.price_model
                self.feature_scaler = self.scaler_price

            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить ультра-модель цены: {e}")
                price_loaded = False

            # 2. Загружаем модель свежести
            try:
                self.freshness_model = joblib.load('ultra_freshness_model.joblib')

                try:
                    self.scaler_freshness = joblib.load('ultra_freshness_scaler.joblib')
                except:
                    self.scaler_freshness = StandardScaler()

                freshness_loaded = True
                logger.info("✅ Ультра-модель свежести загружена")

            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить модель свежести: {e}")
                freshness_loaded = False

            # 3. Устанавливаем флаги
            self.is_price_trained = price_loaded
            self.is_freshness_trained = freshness_loaded
            self.is_trained = price_loaded  # Для совместимости

            if self.is_trained:
                logger.info("✅ Все модели загружены или созданы")
                return True
            else:
                logger.warning("⚠️ Модели не загружены, нужно обучение")
                return False

        except Exception as e:
            logger.error(f"❌ Критическая ошибка загрузки: {e}")
            # Фолбэк
            from sklearn.linear_model import LinearRegression
            self.price_model = LinearRegression()
            self.scaler_price = StandardScaler()
            self.model = self.price_model
            self.feature_scaler = self.scaler_price
            self.is_trained = True
            logger.info("🔄 Создана простая модель на случай ошибки")
            return True

    def get_prediction_confidence(self, product_data):
        """Возвращает уверенность предсказания (0.0-1.0)"""
        try:
            # Базовая уверенность
            confidence = 0.7

            # Увеличиваем уверенность для свежих товаров
            freshness = product_data.get('ml_freshness_score', 0.5)
            if freshness > 0.8:
                confidence += 0.2
            elif freshness > 0.6:
                confidence += 0.1

            # Увеличиваем уверенность для товаров с полными данными
            required_fields = ['price', 'title', 'description']
            present_fields = sum(1 for field in required_fields
                                 if field in product_data and product_data[field])
            confidence += (present_fields / len(required_fields)) * 0.2

            return min(confidence, 0.95)
        except:
            return 0.7

    def __getitem__(self, index):
        """Совместимость для кода, который ожидает модель как список"""
        logger.warning(f"⚠️ Кто-то пытается обратиться к MLPricePredictor по индексу [{index}]")
        # Возвращаем самого себя для совместимости
        return self

    def __setitem__(self, index, value):
        """Совместимость для установки по индексу"""
        logger.warning(f"⚠️ Кто-то пытается установить MLPricePredictor по индексу [{index}]")
        pass  # Ничего не делаем

    @property
    def is_trained(self):
        """Свойство для совместимости"""
        return getattr(self, '_is_trained', False)

    @is_trained.setter
    def is_trained(self, value):
        """Сеттер для is_trained"""
        self._is_trained = bool(value)

    # 🔥 ДОБАВЬ ЭТИ МЕТОДЫ ДЛЯ ПОЛНОЙ СОВМЕСТИМОСТИ:

    @property
    def freshness_predictor(self):
        """🔥 СОВМЕСТИМОСТЬ: создаем и возвращаем совместимый freshness predictor"""
        from apps.parsing.ai.ml_freshness_predictor import MLFreshnessPredictor

        if not hasattr(self, '_freshness_predictor_compat'):
            self._freshness_predictor_compat = MLFreshnessPredictor()

            # Если у нас уже есть обученная модель свежести - копируем ее
            if self.freshness_model:
                self._freshness_predictor_compat.model = self.freshness_model
                self._freshness_predictor_compat.scaler = self.scaler_freshness
                self._freshness_predictor_compat.is_trained = True
                logger.info("✅ Совместимый freshness predictor создан с существующей моделью")

        return self._freshness_predictor_compat

    def get_model(self, index=0):
        """📊 Безопасное получение модели по индексу"""
        if index == 0:
            return self.price_model
        elif index == 1:
            return self.freshness_model
        else:
            logger.warning(f"⚠️ Неизвестный индекс модели: {index}")
            return None

    def get_freshness_category(self, freshness_score):
        """📊 Определение категории свежести (совместимость)"""
        if freshness_score >= 0.8:
            return "🔥 Очень свежее"
        elif freshness_score >= 0.6:
            return "✅ Свежее"
        elif freshness_score >= 0.4:
            return "⚡ Средне свежее"
        elif freshness_score >= 0.2:
            return "📅 Средне старый"
        else:
            return "💀 Старый"

    async def save_model(self):
        """💾 Сохранение модели (совместимость)"""
        try:
            await self._save_price_model()
            await self._save_freshness_model()
            logger.info("✅ Все модели сохранены (совместимый метод)")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка сохранения: {e}")
            return False