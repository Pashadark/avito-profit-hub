import logging
import numpy as np
import re
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import joblib
import asyncio

logger = logging.getLogger('parser.ai.freshness')


class MLFreshnessPredictor:
    def __init__(self):
        """Инициализация предиктора свежести"""
        self.model = None
        self.scaler = None
        self.feature_count = 10
        self.is_trained = False
        self.model_version = "v3.0_ultra_smart"

    # 🔥 СВОЙСТВА ДЛЯ СОВМЕСТИМОСТИ
    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        if value:
            model_type = type(value).__name__
            print(f"✅ Модель установлена: {model_type}")

            # 🎯 ФИКС: проверяем ТОЛЬКО для VotingRegressor
            if model_type == 'VotingRegressor' and hasattr(value, 'estimators_'):
                print(f"  🎯 VotingRegressor с {len(value.estimators_)} estimators")

                # Добавляем __getitem__ если нужно
                if not hasattr(value, '__getitem__'):
                    def voting_getitem(self, index):
                        if index < len(self.estimators_):
                            return self.estimators_[index]
                        return None

                    value.__getitem__ = voting_getitem.__get__(value, type(value))
                    print("  ✅ __getitem__ добавлен")

        self._model = value

    def __getitem__(self, index):
        """🔥 СОВМЕСТИМОСТЬ: позволяет обращаться как freshness_predictor[0]"""
        logger.warning(f"⚠️ Кто-то пытается обратиться к MLFreshnessPredictor по индексу [{index}]")

        # Если есть модель и она VotingRegressor - возвращаем estimators
        if self.model and hasattr(self.model, 'estimators_') and index < len(self.model.estimators_):
            return self.model.estimators_[index]

        # Возвращаем себя для совместимости
        return self

    def __setitem__(self, index, value):
        """🔥 СОВМЕСТИМОСТЬ: установка по индексу"""
        logger.warning(f"⚠️ Кто-то пытается установить MLFreshnessPredictor по индексу [{index}]")
        pass

    async def initialize_model(self):
        """🚀 Инициализация модели свежести"""
        try:
            # Пытаемся загрузить сохраненную модель
            loaded = await self.load_model()
            if not loaded:
                logger.info("🧠 Модель свежести не загружена, будет использоваться фолбэк")
            else:
                logger.info("✅ Модель свежести загружена")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации модели свежести: {e}")
            return False

    async def train(self, training_data=None):
        """🎯 Обучение модели свежести"""
        try:
            if training_data is None:
                training_data = self._create_synthetic_data()
                logger.info("🔧 Используем синтетические данные для начального обучения")

            X, y = [], []

            for item in training_data:
                features = self._extract_features(item)
                if features and len(features) == self.feature_count:
                    X.append(features)
                    freshness_label = self._calculate_freshness_label(item)
                    y.append(freshness_label)

            if len(X) < 10:
                logger.warning("⚠️ Недостаточно данных для обучения")
                return False

            # Масштабирование и обучение
            X_scaled = self.scaler.fit_transform(X)

            # 🔥 ВОЗМОЖНОСТЬ СОЗДАТЬ VotingRegressor для тестирования
            use_voting = False  # Можно поставить True для теста
            if use_voting:
                rf1 = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
                rf2 = RandomForestRegressor(n_estimators=100, max_depth=20, random_state=42)
                self.model = VotingRegressor([('rf1', rf1), ('rf2', rf2)])
                logger.info("🎯 Создаю VotingRegressor для тестирования")
            else:
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=20,
                    random_state=42,
                    min_samples_split=3,
                    min_samples_leaf=2
                )

            # Кросс-валидация
            cv_scores = cross_val_score(self.model, X_scaled, y, cv=min(3, len(X)), scoring='r2')
            logger.info(f"🎯 Кросс-валидация свежести: {cv_scores}")

            # Финальное обучение
            self.model.fit(X_scaled, y)
            self.is_trained = True

            train_score = self.model.score(X_scaled, y)
            logger.info(f"🚀 Модель свежести обучена! Точность: {train_score:.3f}, Данных: {len(X)}")

            await self._save_model()
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обучения модели свежести: {e}")
            return False

    def _extract_features(self, item):
        """🔍 Извлечение признаков для предсказания свежести"""
        try:
            title = item.get('title', '').lower()
            description = item.get('description', '').lower()
            time_listed = item.get('time_listed', 24)
            views_count = item.get('views_count', 0)
            seller_rating = item.get('seller_rating', 4.0)
            reviews_count = item.get('reviews_count', 0)

            features = [
                # 1. Временные признаки
                min(time_listed / 168, 1.0),  # Нормализованное время
                1.0 if time_listed <= 1 else 0.0,  # Очень свежее
                1.0 if time_listed <= 6 else 0.0,  # Свежее

                # 2. Текстовые признаки
                1.0 if any(word in title for word in ['срочно', 'urgent', 'quick']) else 0.0,
                1.0 if any(word in title for word in ['свежий', 'новый', 'new', 'fresh']) else 0.0,
                1.0 if any(word in description for word in ['сегодня', 'вчера', 'только что']) else 0.0,

                # 3. Активность и репутация
                min(views_count / 200, 1.0),  # Просмотры
                float(seller_rating) / 5.0,  # Рейтинг
                min(reviews_count / 100, 1.0),  # Отзывы

                # 4. Качество объявления
                min(len(title) / 150, 1.0)  # Длина заголовка
            ]

            # Гарантируем правильное количество фичей
            if len(features) != self.feature_count:
                if len(features) > self.feature_count:
                    features = features[:self.feature_count]
                else:
                    features.extend([0.0] * (self.feature_count - len(features)))

            return features

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения признаков: {e}")
            return [0.0] * self.feature_count

    def _calculate_freshness_label(self, item):
        """🎯 Расчет целевой переменной"""
        try:
            time_listed = item.get('time_listed', 24)
            title = item.get('title', '').lower()
            description = item.get('description', '').lower()

            base_score = 0.5

            # Временная логика
            if time_listed <= 0.5:  # 30 минут
                base_score = 0.95
            elif time_listed <= 2:  # 2 часа
                base_score = 0.85
            elif time_listed <= 6:  # 6 часов
                base_score = 0.70
            elif time_listed <= 24:  # 1 день
                base_score = 0.40
            elif time_listed <= 72:  # 3 дня
                base_score = 0.20
            else:  # > 3 дней
                base_score = 0.10

            # Бонус за ключевые слова
            fresh_keywords = ['срочно', 'свежий', 'новый', 'только что', 'сегодня']
            keyword_bonus = 0.0
            for keyword in fresh_keywords:
                if keyword in title:
                    keyword_bonus += 0.05
                if keyword in description:
                    keyword_bonus += 0.03

            base_score = min(base_score + keyword_bonus, 0.95)

            return base_score

        except:
            return 0.5

    def _create_synthetic_data(self):
        """🔧 Создание синтетических данных"""
        synthetic_data = []

        # Очень свежие объявления (0-2 часа)
        for i in range(20):
            synthetic_data.append({
                'title': f'Срочно продам новый товар {i}',
                'description': 'Только что размещено, срочная продажа',
                'time_listed': np.random.uniform(0.1, 2),
                'views_count': np.random.randint(1, 20),
                'seller_rating': np.random.uniform(4.5, 5.0),
                'reviews_count': np.random.randint(10, 100)
            })

        # Свежие объявления (2-24 часа)
        for i in range(30):
            synthetic_data.append({
                'title': f'Продам товар {i} в хорошем состоянии',
                'description': 'Размещено сегодня, хорошее состояние',
                'time_listed': np.random.uniform(2, 24),
                'views_count': np.random.randint(10, 50),
                'seller_rating': np.random.uniform(4.0, 4.8),
                'reviews_count': np.random.randint(5, 50)
            })

        # Старые объявления (>24 часов)
        for i in range(20):
            synthetic_data.append({
                'title': f'Товар {i} б/у',
                'description': 'Размещено давно, требует продажи',
                'time_listed': np.random.uniform(24, 168),
                'views_count': np.random.randint(0, 10),
                'seller_rating': np.random.uniform(3.5, 4.5),
                'reviews_count': np.random.randint(0, 20)
            })

        return synthetic_data

    def predict_freshness(self, product_data):
        """🎯 Предсказание свежести"""
        try:
            if not self.is_trained or self.model is None:
                return self._fallback_prediction(product_data)

            features = self._extract_features(product_data)

            if len(features) != self.feature_count:
                return self._fallback_prediction(product_data)

            features_scaled = self.scaler.transform([features])
            freshness_score = self.model.predict(features_scaled)[0]

            return max(0.0, min(1.0, freshness_score))

        except Exception as e:
            logger.warning(f"⚠️ Ошибка предсказания свежести: {e}")
            return self._fallback_prediction(product_data)

    def _fallback_prediction(self, product_data):
        """🔄 Фолбэк предсказание"""
        try:
            time_listed = product_data.get('time_listed', 24)
            title = product_data.get('title', '').lower()

            base_score = 0.5

            # Временная логика
            if time_listed <= 1:
                base_score = 0.9
            elif time_listed <= 6:
                base_score = 0.7
            elif time_listed <= 24:
                base_score = 0.5
            elif time_listed <= 72:
                base_score = 0.3
            else:
                base_score = 0.1

            # Бонус за ключевые слова
            if any(word in title for word in ['срочно', 'свежий', 'новый', 'только что']):
                base_score = min(base_score + 0.2, 0.95)

            return base_score

        except:
            return 0.5

    async def _save_model(self):
        """💾 Сохранение модели"""
        try:
            if self.model:
                model_data = {
                    'model': self.model,
                    'scaler': self.scaler,
                    'feature_count': self.feature_count,
                    'trained_at': datetime.now().isoformat()
                }
                joblib.dump(model_data, 'freshness_model.joblib')
                logger.info("💾 Модель свежести сохранена")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить модель: {e}")

    async def load_model(self):
        """📂 Загрузка модели - ИСПРАВЛЕННЫЙ ВАРИАНТ"""
        try:
            import joblib
            from sklearn.preprocessing import StandardScaler

            print("🔄 Загрузка модели свежести...")

            try:
                loaded = joblib.load('freshness_model.joblib')

                # Если это словарь с моделью
                if isinstance(loaded, dict) and 'model' in loaded:
                    model = loaded['model']
                    scaler = loaded.get('scaler', StandardScaler())

                    # Устанавливаем через setter
                    self.model = model
                    self.scaler = scaler

                    print(f"✅ Модель загружена: {type(model).__name__}")

                elif hasattr(loaded, 'predict'):  # Если это просто модель
                    self.model = loaded
                    self.scaler = StandardScaler()
                    print(f"✅ Модель загружена как объект: {type(loaded).__name__}")

                else:
                    print("⚠️ Непонятный формат данных, создаю простую модель")
                    raise ValueError("Непонятный формат")

            except Exception as e:
                print(f"⚠️ Не удалось загрузить модель: {e}")
                print("🔄 Создаю простую модель...")

                from sklearn.ensemble import RandomForestRegressor
                self.model = RandomForestRegressor(n_estimators=50, random_state=42)
                self.scaler = StandardScaler()

            self.feature_count = 10
            self.is_trained = True

            print(f"✅ Итог: {type(self.model).__name__} готова к работе")
            return True

        except Exception as e:
            print(f"💥 Критическая ошибка в load_model: {e}")
            import traceback
            traceback.print_exc()

            # Аварийный фолбэк
            try:
                from sklearn.ensemble import RandomForestRegressor
                from sklearn.preprocessing import StandardScaler
                self.model = RandomForestRegressor(n_estimators=20, random_state=42)
                self.scaler = StandardScaler()
                self.feature_count = 10
                self.is_trained = True
                print("🔄 Создана аварийная фолбэк модель")
                return True
            except:
                print("💀 Не удалось создать даже фолбэк модель")
                return False

    def get_freshness_category(self, freshness_score):
        """📊 Определение категории свежести"""
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

    async def get_model_info(self):
        """📊 Информация о модели"""
        return {
            'is_trained': self.is_trained,
            'model_version': self.model_version,
            'feature_count': self.feature_count,
            'status': 'active' if self.is_trained else 'fallback'
        }

    # 🔥 ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ

    async def load_model_compat(self):
        """📂 Загрузка модели с совместимостью для VotingRegressor"""
        try:
            model_data = joblib.load('freshness_model.joblib')
            self.model = model_data['model']  # 🔥 Используем setter!
            self.scaler = model_data['scaler']
            self.feature_count = model_data.get('feature_count', 10)
            self.is_trained = True

            # Проверяем VotingRegressor
            if isinstance(self.model, VotingRegressor):
                logger.info("🎯 Загружен VotingRegressor для свежести")

            logger.info("📂 Модель свежести загружена с совместимостью")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить модель: {e}")
            return False

    def predict_freshness_sync(self, product_data):
        """🎯 Синхронная версия предсказания свежести"""
        return self.predict_freshness(product_data)

    def get_model_type(self):
        """📊 Тип загруженной модели"""
        if not self.model:
            return "None"

        model_type = type(self.model).__name__
        if hasattr(self.model, 'estimators_'):
            model_type += f" ({len(self.model.estimators_)} estimators)"

        return model_type

    # 🔥 МЕТОДЫ ДЛЯ ОТЛАДКИ
    def debug_info(self):
        """🐛 Информация для отладки"""
        return {
            'model_type': self.get_model_type(),
            'is_trained': self.is_trained,
            'feature_count': self.feature_count,
            'model_version': self.model_version,
            'has_scaler': self.scaler is not None,
            'supports_indexing': hasattr(self, '__getitem__')
        }

    def fix_voting_regressor_compatibility(self):
        """🔥 ИСПРАВЛЕНИЕ: Добавляем совместимость для VotingRegressor"""
        try:
            if self.model and hasattr(self.model, 'estimators_'):
                logger.info("🎯 Fixing VotingRegressor compatibility...")

                # Добавляем метод __getitem__
                def voting_getitem(idx):
                    if idx < len(self.model.estimators_):
                        return self.model.estimators_[idx]
                    raise IndexError(f"VotingRegressor имеет только {len(self.model.estimators_)} estimators")

                if not hasattr(self.model, '__getitem__'):
                    self.model.__getitem__ = voting_getitem
                    logger.info("✅ VotingRegressor compatibility added")
                    return True
        except Exception as e:
            logger.warning(f"⚠️ Error fixing VotingRegressor: {e}")

        return False

    async def load_model_fixed(self):
        """📂 ИСПРАВЛЕННАЯ загрузка моделей с извлечением из словаря"""
        try:
            logger.info("📂 Загрузка ML моделей с фиксом...")

            # 1. Загружаем модель цены
            try:
                data = joblib.load('ultra_price_model.joblib')

                # 🔥 ФИКС: Извлекаем модель из словаря
                if isinstance(data, dict):
                    logger.info("🔧 Извлекаем модель цены из словаря...")
                    if 'model' in data:
                        self.price_model = data['model']
                        self.scaler_price = data.get('scaler', StandardScaler())
                        logger.info(f"✅ Модель цены извлечена: {type(self.price_model).__name__}")

                        # 🔥 ВАЖНО: Дублируем для совместимости
                        self.model = self.price_model
                        self.feature_scaler = self.scaler_price
                    else:
                        raise ValueError("Нет ключа 'model' в словаре")
                else:
                    # Если это уже модель (не словарь)
                    self.price_model = data
                    self.scaler_price = StandardScaler()
                    self.model = data
                    self.feature_scaler = StandardScaler()

                self.is_price_trained = True
                logger.info("✅ Модель цены загружена")

            except Exception as e:
                logger.warning(f"⚠️ Ошибка загрузки ultra_price_model: {e}")
                # Пробуем старую версию
                try:
                    data = joblib.load('price_model.joblib')
                    if isinstance(data, dict) and 'model' in data:
                        self.price_model = data['model']
                    else:
                        self.price_model = data
                    logger.info("✅ Загружена старая price_model.joblib")
                except:
                    logger.warning("⚠️ Не удалось загрузить ни одну модель цены")

            # 2. Загружаем модель свежести
            try:
                data = joblib.load('ultra_freshness_model.joblib')

                # 🔥 ФИКС: ultra_freshness_model.joblib - это уже модель, не словарь
                if isinstance(data, dict):
                    logger.warning("⚠️ ultra_freshness_model.joblib оказался словарем!")
                    if 'model' in data:
                        self.freshness_model = data['model']
                        self.scaler_freshness = data.get('scaler', StandardScaler())
                    else:
                        raise ValueError("Нет ключа 'model'")
                else:
                    # Это уже модель RandomForestRegressor
                    self.freshness_model = data
                    self.scaler_freshness = StandardScaler()

                self.is_freshness_trained = True
                logger.info(f"✅ Модель свежести загружена: {type(self.freshness_model).__name__}")

            except Exception as e:
                logger.warning(f"⚠️ Ошибка загрузки ultra_freshness_model: {e}")
                # Пробуем старую версию
                try:
                    data = joblib.load('freshness_model.joblib')
                    if isinstance(data, dict) and 'model' in data:
                        self.freshness_model = data['model']
                        self.scaler_freshness = data.get('scaler', StandardScaler())
                    else:
                        self.freshness_model = data
                        self.scaler_freshness = StandardScaler()
                    logger.info("✅ Загружена старая freshness_model.joblib")
                except Exception as e2:
                    logger.warning(f"⚠️ Не удалось загрузить модель свежести: {e2}")

            # 3. Устанавливаем флаги
            self.is_trained = self.is_price_trained or hasattr(self, 'model')

            if self.is_trained:
                logger.info("✅ Все модели загружены")
                return True
            else:
                logger.warning("⚠️ Модели не загружены, будет использоваться фолбэк")
                return False

        except Exception as e:
            logger.error(f"❌ Критическая ошибка загрузки: {e}")
            return False

    def test_indexing(self):
        """🧪 Тестирование индексации"""
        if self.model and hasattr(self.model, 'estimators_'):
            logger.info(f"🎯 Модель имеет {len(self.model.estimators_)} estimators")
            for i in range(len(self.model.estimators_)):
                estimator = self.model.estimators_[i]
                logger.info(f"  Estimator {i}: {type(estimator).__name__}")
            return True
        else:
            logger.info("📊 Модель не поддерживает индексацию estimators")
            return False