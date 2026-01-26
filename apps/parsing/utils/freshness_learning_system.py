import logging
import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger('parser.ai')


class FreshnessLearningSystem:
    """🔥 СИСТЕМА ОБУЧЕНИЯ ДЛЯ СВЕЖЕСТИ ОБЪЯВЛЕНИЙ"""

    def __init__(self, db_path="freshness_knowledge.db"):
        self.db_path = db_path
        self.freshness_patterns = {}
        self.timing_optimization = {}
        self.category_freshness = {}
        self.successful_patterns = deque(maxlen=1000)

        # 🔥 БАЗА ЗНАНИЙ СВЕЖЕСТИ
        self.freshness_knowledge = {
            'publication_cycles': {},
            'optimal_times': {},
            'successful_queries': {},
            'category_patterns': {}
        }

        logger.info("🧠 Система обучения свежести инициализирована")

    async def learn_from_product(self, product_data: Dict[str, Any]):
        """🎯 Обучение на основе данных товара - ОСНОВНОЙ МЕТОД ДЛЯ ПАРСЕРА"""
        try:
            # Сохраняем данные для обучения
            learning_entry = {
                'timestamp': datetime.now().isoformat(),
                'product_data': product_data,
                'freshness_score': product_data.get('freshness_score', 0),
                'time_listed': product_data.get('time_listed', 24)
            }

            # Добавляем в успешные паттерны
            self.successful_patterns.append(learning_entry)

            # 🔥 ОБУЧАЕМСЯ НА ОСНОВЕ ДАННЫХ ТОВАРА
            category = product_data.get('category', 'unknown')
            found_time = datetime.now()

            # Обновляем паттерны времени
            await self._update_timing_pattern(category, found_time)

            # Обновляем паттерны свежести
            freshness_features = self._extract_freshness_features(product_data)
            await self._update_freshness_patterns(freshness_features, category)

            # Обновляем успешные запросы
            query = product_data.get('search_query', '')
            if query:
                await self._update_successful_queries(query, category)

            logger.info(f"📚 Обучение на товаре: {product_data.get('name', 'Unknown')}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обучения на товаре: {e}")
            return False

    async def learn_from_successful_finds(self, successful_items):
        """🔥 УЧИМСЯ на успешно найденных СВЕЖИХ объявлениях"""
        try:
            logger.info(f"🧠 Обучение на {len(successful_items)} свежих объявлениях...")

            for item in successful_items:
                # 🔥 УЧИМСЯ КОГДА ПОЯВЛЯЮТСЯ СВЕЖИЕ ОБЪЯВЛЕНИЯ
                found_time = item.get('found_at')
                category = item.get('category', 'unknown')

                if found_time:
                    await self._update_timing_pattern(category, found_time)

                # 🔥 УЧИМСЯ ПРИЗНАКАМ СВЕЖИХ ОБЪЯВЛЕНИЙ
                freshness_features = self._extract_freshness_features(item)
                await self._update_freshness_patterns(freshness_features, category)

                # 🔥 УЧИМСЯ УСПЕШНЫМ ЗАПРОСАМ
                query = item.get('search_query', '')
                if query:
                    await self._update_successful_queries(query, category)

            # 🔥 СОХРАНЯЕМ ОБУЧЕННЫЕ ДАННЫЕ
            await self._save_learning_state()

            logger.info("🎯 Обучение завершено!")

        except Exception as e:
            logger.error(f"❌ Ошибка обучения: {e}")

    async def _update_timing_pattern(self, category, found_time):
        """🕒 Обновляем паттерны времени появления свежих объявлений"""
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

            # ОБНОВЛЯЕМ ЧАСОВЫЕ ПАТТЕРНЫ
            self.timing_optimization[category]['hourly_pattern'][hour] += 1
            self.timing_optimization[category]['daily_pattern'][day_of_week] += 1
            self.timing_optimization[category]['total_finds'] += 1

            logger.debug(f"📊 Обновлен timing pattern для {category}: час {hour}, день {day_of_week}")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления timing pattern: {e}")

    async def _update_freshness_patterns(self, features, category):
        """🎯 Обновляем паттерны признаков свежести"""
        try:
            if category not in self.freshness_patterns:
                self.freshness_patterns[category] = {
                    'feature_counts': defaultdict(int),
                    'total_samples': 0,
                    'successful_features': []
                }

            # ОБНОВЛЯЕМ СЧЕТЧИКИ ПРИЗНАКОВ
            for feature, value in features.items():
                if value > 0.5:  # Значимый признак
                    feature_key = f"{feature}_{value:.1f}"
                    self.freshness_patterns[category]['feature_counts'][feature_key] += 1

            self.freshness_patterns[category]['total_samples'] += 1

            # СОХРАНЯЕМ УСПЕШНЫЕ ПАТТЕРНЫ
            self.successful_patterns.append({
                'category': category,
                'features': features,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления freshness patterns: {e}")

    async def _update_successful_queries(self, query, category):
        """🔍 Обновляем успешные запросы"""
        try:
            if category not in self.freshness_knowledge['successful_queries']:
                self.freshness_knowledge['successful_queries'][category] = {}

            if query not in self.freshness_knowledge['successful_queries'][category]:
                self.freshness_knowledge['successful_queries'][category][query] = 0

            self.freshness_knowledge['successful_queries'][category][query] += 1

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления successful queries: {e}")

    def _extract_freshness_features(self, item):
        """🔍 Извлечение признаков свежести для обучения"""
        try:
            title = item.get('name', '').lower()
            description = item.get('description', '').lower()
            text = f"{title} {description}"

            features = {}

            # 🔥 ТЕКСТОВЫЕ ПРИЗНАКИ СВЕЖЕСТИ
            freshness_keywords = [
                'только что', 'сегодня', 'минут', 'час', 'только добавлен',
                'срочно', 'быстро', 'срочная продажа', 'новый', 'не использовался'
            ]

            for keyword in freshness_keywords:
                features[f'keyword_{keyword}'] = 1.0 if keyword in text else 0.0

            # 🔥 ВРЕМЕННЫЕ ПРИЗНАКИ
            time_listed = item.get('time_listed', 24)
            features['time_listed'] = min(time_listed / 24.0, 1.0)
            features['is_today'] = 1.0 if 'сегодня' in str(item.get('posted_date', '')).lower() else 0.0
            features['is_yesterday'] = 1.0 if 'вчера' in str(item.get('posted_date', '')).lower() else 0.0

            # 🔥 ПРИЗНАКИ АКТИВНОСТИ
            features['has_images'] = 1.0 if item.get('images') else 0.0
            features['seller_rating'] = min(item.get('seller_rating', 0) / 5.0, 1.0)
            features['description_length'] = min(len(description) / 500.0, 1.0)

            return features

        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения признаков свежести: {e}")
            return {}

    async def get_optimal_search_times(self, category):
        """🕒 Возвращает лучшее время для поиска по категории"""
        try:
            if category in self.timing_optimization:
                pattern = self.timing_optimization[category]['hourly_pattern']
                total_finds = self.timing_optimization[category]['total_finds']

                if total_finds > 10:
                    # НОРМАЛИЗУЕМ И НАХОДИМ ПИКИ
                    normalized_pattern = [count / total_finds for count in pattern]
                    best_hours = sorted(range(24), key=lambda h: normalized_pattern[h], reverse=True)[:3]
                    return best_hours

            # 🔥 ЗАПАСНЫЕ ЗНАЧЕНИЯ
            return [9, 14, 19]  # Утро, день, вечер

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения оптимального времени: {e}")
            return [9, 14, 19]

    async def get_successful_queries(self, category, limit=5):
        """🔍 Возвращает самые успешные запросы для категории"""
        try:
            if category in self.freshness_knowledge['successful_queries']:
                queries = self.freshness_knowledge['successful_queries'][category]
                sorted_queries = sorted(queries.items(), key=lambda x: x[1], reverse=True)
                return [q[0] for q in sorted_queries[:limit]]
            return []

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения успешных запросов: {e}")
            return []

    async def get_freshness_insights(self, category):
        """📊 Возвращает инсайты по свежести для категории"""
        try:
            insights = {
                'optimal_times': await self.get_optimal_search_times(category),
                'successful_queries': await self.get_successful_queries(category),
                'total_learned_samples': 0,
                'feature_importance': [],
                'confidence_level': 'medium'
            }

            if category in self.freshness_patterns:
                pattern_data = self.freshness_patterns[category]
                insights['total_learned_samples'] = pattern_data['total_samples']

                # ТОП ПРИЗНАКИ
                top_features = sorted(
                    pattern_data['feature_counts'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                insights['feature_importance'] = top_features

                # УРОВЕНЬ УВЕРЕННОСТИ
                if pattern_data['total_samples'] > 100:
                    insights['confidence_level'] = 'high'
                elif pattern_data['total_samples'] > 20:
                    insights['confidence_level'] = 'medium'
                else:
                    insights['confidence_level'] = 'low'

            return insights

        except Exception as e:
            logger.error(f"❌ Ошибка получения инсайтов: {e}")
            return {}

    async def collect_freshness_feedback(self, product, actual_freshness, predicted_freshness):
        """📥 Сбор обратной связи для обучения модели свежести"""
        try:
            features = self._extract_freshness_features(product)
            error = abs(predicted_freshness - actual_freshness)

            # СОХРАНЯЕМ ДЛЯ БУДУЩЕГО ОБУЧЕНИЯ
            feedback_data = {
                'timestamp': datetime.now().isoformat(),
                'category': product.get('category', 'unknown'),
                'features': features,
                'predicted_freshness': predicted_freshness,
                'actual_freshness': actual_freshness,
                'error': error,
                'product_title': product.get('name', '')[:100]
            }

            # ДОБАВЛЯЕМ В ОЧЕРЕДЬ ДЛЯ ОБУЧЕНИЯ
            self.successful_patterns.append(feedback_data)

            logger.debug(f"📥 Собрана обратная связь по свежести. Ошибка: {error:.3f}")

        except Exception as e:
            logger.error(f"❌ Ошибка сбора обратной связи свежести: {e}")

    async def get_learning_progress(self):
        """📈 Прогресс обучения системы"""
        try:
            total_categories = len(self.timing_optimization)
            total_samples = sum(
                pattern['total_samples']
                for pattern in self.freshness_patterns.values()
                if 'total_samples' in pattern
            )

            # УРОВЕНЬ ИНТЕЛЛЕКТА СИСТЕМЫ
            intelligence_level = min(total_samples / 100.0, 1.0)

            return {
                'total_categories_learned': total_categories,
                'total_samples_collected': total_samples,
                'intelligence_level': f"{intelligence_level:.1%}",
                'successful_patterns_count': len(self.successful_patterns),
                'system_confidence': 'high' if intelligence_level > 0.7 else 'medium' if intelligence_level > 0.3 else 'low',
                'last_learning_update': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения прогресса обучения: {e}")
            return {}

    async def _save_learning_state(self):
        """💾 Сохранение состояния обучения"""
        try:
            state = {
                'timing_optimization': self.timing_optimization,
                'freshness_patterns': self.freshness_patterns,
                'freshness_knowledge': self.freshness_knowledge,
                'successful_patterns': list(self.successful_patterns),
                'last_saved': datetime.now().isoformat()
            }

            with open('freshness_learning_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            logger.info("💾 Состояние обучения свежести сохранено")

        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить состояние обучения: {e}")

    async def load_learning_state(self):
        """📥 Загрузка состояния обучения"""
        try:
            with open('freshness_learning_state.json', 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.timing_optimization = state.get('timing_optimization', {})
            self.freshness_patterns = state.get('freshness_patterns', {})
            self.freshness_knowledge = state.get('freshness_knowledge', {})
            self.successful_patterns = deque(
                state.get('successful_patterns', []),
                maxlen=1000
            )

            logger.info("📥 Состояние обучения свежести загружено")
            return True

        except FileNotFoundError:
            logger.info("📥 Файл состояния обучения не найден, начинаем с чистого листа")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки состояния обучения: {e}")
            return False

    async def get_learning_stats(self) -> Dict[str, Any]:
        """📊 Статистика обучения для совместимости"""
        progress = await self.get_learning_progress()
        return {
            'status': 'active',
            'system': 'FreshnessLearningSystem',
            'learning_samples': progress.get('total_samples_collected', 0),
            'patterns_learned': progress.get('successful_patterns_count', 0),
            'intelligence_level': progress.get('intelligence_level', '0%'),
            'confidence': progress.get('system_confidence', 'low')
        }