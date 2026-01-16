import logging
import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict, deque

logger = logging.getLogger('parser.ai.learning')


class MLLearningSystem:
    """🎯 УНИВЕРСАЛЬНАЯ СИСТЕМА ОБУЧЕНИЯ ДЛЯ ВСЕХ ML МОДЕЛЕЙ"""

    def __init__(self, db_path="ml_knowledge.db"):
        self.db_path = db_path

        # 🔥 БАЗЫ ЗНАНИЙ
        self.freshness_patterns = {}
        self.price_patterns = {}
        self.timing_optimization = {}
        self.successful_queries = {}
        self.learning_history = deque(maxlen=2000)

        # 🔥 ДОБАВЬТЕ ЭТИ АТРИБУТЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
        self.successful_patterns = []  # Для обратной связи
        self.failed_patterns = []  # Для ошибок
        self.feedback_history = []  # История фидбека

        logger.info("🧠 Универсальная система обучения инициализирована")

    async def learn_from_product(self, product_data: Dict[str, Any]):
        """🎯 Обучение на основе данных товара"""
        try:
            learning_entry = {
                'timestamp': datetime.now().isoformat(),
                'product_data': product_data,
                'freshness_score': product_data.get('ml_freshness_score', 0),
                'predicted_price': product_data.get('ai_predicted_price', 0),
                'actual_price': product_data.get('price', 0),
                'category': product_data.get('category', 'unknown')
            }

            self.learning_history.append(learning_entry)

            # 🔥 ОБУЧАЕМ РАЗНЫЕ АСПЕКТЫ
            category = product_data.get('category', 'unknown')
            found_time = datetime.now()

            await self._update_timing_patterns(category, found_time)
            await self._update_freshness_patterns(product_data, category)
            await self._update_price_patterns(product_data, category)

            # 🔥 ОБУЧАЕМСЯ НА УСПЕШНЫХ ЗАПРОСАХ
            query = product_data.get('search_query', '')
            if query:
                await self._update_successful_queries(query, category)

            logger.debug(f"📚 Обучение на товаре: {product_data.get('name', 'Unknown')}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обучения на товаре: {e}")
            return False

    async def _update_timing_patterns(self, category, found_time):
        """🕒 Обновление временных паттернов"""
        try:
            if isinstance(found_time, str):
                found_time = datetime.fromisoformat(found_time.replace('Z', '+00:00'))

            hour = found_time.hour
            day_of_week = found_time.weekday()

            if category not in self.timing_optimization:
                self.timing_optimization[category] = {
                    'hourly_pattern': [0] * 24,
                    'daily_pattern': [0] * 7,
                    'total_finds': 0
                }

            self.timing_optimization[category]['hourly_pattern'][hour] += 1
            self.timing_optimization[category]['daily_pattern'][day_of_week] += 1
            self.timing_optimization[category]['total_finds'] += 1

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления timing patterns: {e}")

    async def _update_freshness_patterns(self, product_data, category):
        """🔥 Обновление паттернов свежести"""
        try:
            if category not in self.freshness_patterns:
                self.freshness_patterns[category] = {
                    'feature_counts': defaultdict(int),
                    'total_samples': 0
                }

            # Анализ признаков свежести
            features = self._extract_freshness_features(product_data)
            for feature, value in features.items():
                if value > 0.5:
                    feature_key = f"{feature}_{value:.1f}"
                    self.freshness_patterns[category]['feature_counts'][feature_key] += 1

            self.freshness_patterns[category]['total_samples'] += 1

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления freshness patterns: {e}")

    async def _update_price_patterns(self, product_data, category):
        """💰 Обновление паттернов цен"""
        try:
            if category not in self.price_patterns:
                self.price_patterns[category] = {
                    'price_ranges': defaultdict(int),
                    'total_samples': 0,
                    'avg_price': 0
                }

            price = product_data.get('price', 0)
            if price > 0:
                price_range = f"{int(price / 1000) * 1000}-{int(price / 1000) * 1000 + 1000}"
                self.price_patterns[category]['price_ranges'][price_range] += 1
                self.price_patterns[category]['total_samples'] += 1

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления price patterns: {e}")

    async def _update_successful_queries(self, query, category):
        """🔍 Обновление успешных запросов"""
        try:
            if category not in self.successful_queries:
                self.successful_queries[category] = {}

            if query not in self.successful_queries[category]:
                self.successful_queries[category][query] = 0

            self.successful_queries[category][query] += 1

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления successful queries: {e}")

    def _extract_freshness_features(self, product_data):
        """🔍 Извлечение признаков свежести"""
        try:
            title = product_data.get('name', '').lower()
            description = product_data.get('description', '').lower()
            text = f"{title} {description}"

            features = {}

            # Ключевые слова свежести
            freshness_keywords = ['только что', 'сегодня', 'минут', 'час', 'только добавлен', 'срочно']
            for keyword in freshness_keywords:
                features[f'keyword_{keyword}'] = 1.0 if keyword in text else 0.0

            # Временные признаки
            time_listed = product_data.get('time_listed', 24)
            features['time_listed'] = min(time_listed / 24.0, 1.0)
            features['is_today'] = 1.0 if 'сегодня' in str(product_data.get('posted_date', '')).lower() else 0.0

            # Признаки активности
            features['has_images'] = 1.0 if product_data.get('images') else 0.0
            features['seller_rating'] = min(product_data.get('seller_rating', 0) / 5.0, 1.0)

            return features

        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения признаков свежести: {e}")
            return {}

    async def get_optimal_search_times(self, category):
        """🕒 Лучшее время для поиска по категории"""
        try:
            if category in self.timing_optimization:
                pattern = self.timing_optimization[category]['hourly_pattern']
                total_finds = self.timing_optimization[category]['total_finds']

                if total_finds > 10:
                    normalized_pattern = [count / total_finds for count in pattern]
                    best_hours = sorted(range(24), key=lambda h: normalized_pattern[h], reverse=True)[:3]
                    return best_hours

            return [9, 14, 19]  # Утро, день, вечер

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения оптимального времени: {e}")
            return [9, 14, 19]

    async def get_successful_queries(self, category, limit=5):
        """🔍 Самые успешные запросы для категории"""
        try:
            if category in self.successful_queries:
                queries = self.successful_queries[category]
                sorted_queries = sorted(queries.items(), key=lambda x: x[1], reverse=True)
                return [q[0] for q in sorted_queries[:limit]]
            return []

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения успешных запросов: {e}")
            return []

    async def get_learning_insights(self, category):
        """📊 Инсайты по обучению для категории"""
        try:
            insights = {
                'optimal_times': await self.get_optimal_search_times(category),
                'successful_queries': await self.get_successful_queries(category),
                'total_learned_samples': len([x for x in self.learning_history if x.get('category') == category]),
                'freshness_patterns_count': self.freshness_patterns.get(category, {}).get('total_samples', 0),
                'price_patterns_count': self.price_patterns.get(category, {}).get('total_samples', 0),
                'confidence_level': 'medium'
            }

            total_samples = insights['total_learned_samples']
            if total_samples > 100:
                insights['confidence_level'] = 'high'
            elif total_samples > 20:
                insights['confidence_level'] = 'medium'
            else:
                insights['confidence_level'] = 'low'

            return insights

        except Exception as e:
            logger.error(f"❌ Ошибка получения инсайтов: {e}")
            return {}

    async def get_learning_stats(self):
        """📈 Статистика обучения"""
        try:
            total_categories = len(self.timing_optimization)
            total_samples = len(self.learning_history)

            intelligence_level = min(total_samples / 200.0, 1.0)

            return {
                'total_categories_learned': total_categories,
                'total_samples_collected': total_samples,
                'intelligence_level': f"{intelligence_level:.1%}",
                'system_confidence': 'high' if intelligence_level > 0.7 else 'medium' if intelligence_level > 0.3 else 'low',
                'last_learning_update': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики обучения: {e}")
            return {}

    async def save_learning_state(self):
        """💾 Сохранение состояния обучения"""
        try:
            state = {
                'freshness_patterns': dict(self.freshness_patterns),
                'price_patterns': dict(self.price_patterns),
                'timing_optimization': dict(self.timing_optimization),
                'successful_queries': dict(self.successful_queries),
                'learning_history': list(self.learning_history),
                'last_saved': datetime.now().isoformat()
            }

            with open('ml_learning_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            logger.info("💾 Состояние обучения сохранено")

        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить состояние обучения: {e}")

    async def collect_feedback(self, prediction, actual_result, features, prediction_type, confidence, context):
        """📥 Сбор обратной связи для обучения (для совместимости)"""
        try:
            feedback_data = {
                'timestamp': datetime.now().isoformat(),
                'prediction_type': prediction_type,
                'prediction': prediction,
                'actual_result': actual_result,
                'features': features,
                'confidence': confidence,
                'context': context,
                'error': abs(prediction - actual_result) if actual_result is not None else 0
            }

            # 🔥 ИСПРАВЛЕНИЕ: Теперь атрибут существует
            self.successful_patterns.append(feedback_data)
            self.feedback_history.append(feedback_data)

            logger.debug(f"📥 Собрана обратная связь для {prediction_type}")

            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка сбора обратной связи: {e}")
            return False

    async def load_learning_state(self):
        """📥 Загрузка состояния обучения"""
        try:
            with open('ml_learning_state.json', 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.freshness_patterns = state.get('freshness_patterns', {})
            self.price_patterns = state.get('price_patterns', {})
            self.timing_optimization = state.get('timing_optimization', {})
            self.successful_queries = state.get('successful_queries', {})
            self.learning_history = deque(state.get('learning_history', []), maxlen=2000)

            logger.info("📥 Состояние обучения загружено")
            return True

        except FileNotFoundError:
            logger.info("📥 Файл состояния обучения не найден, начинаем с чистого листа")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки состояния обучения: {e}")
            return False