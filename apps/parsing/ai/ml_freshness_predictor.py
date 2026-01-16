import logging
import numpy as np
import re
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import joblib
import asyncio

logger = logging.getLogger('parser.ai.freshness')


class MLFreshnessPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_count = 10
        self.model_version = "v1.0"

        logger.info(f"🧠 Инициализирован ML анализатор свежести {self.model_version}")

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
        """📂 Загрузка модели"""
        try:
            model_data = joblib.load('freshness_model.joblib')
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_count = model_data.get('feature_count', 10)
            self.is_trained = True
            logger.info("📂 Модель свежести загружена")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить модель: {e}")
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