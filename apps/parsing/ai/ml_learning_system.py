"""
🔥 МОЗГ СИСТЕМЫ - УМНАЯ ОБУЧАЮЩАЯСЯ СИСТЕМА
🎯 ОБУЧАЕТСЯ НА ВСЕХ ДАННЫХ ИЗ БАЗЫ, УЛУЧШАЕТ АЛГОРИТМЫ
"""

import logging
import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict, deque
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger('parser.ai.learning')


class MLLearningSystem:
    """🧠 МОЗГ СИСТЕМЫ - УМНАЯ ОБУЧАЮЩАЯСЯ СИСТЕМА"""

    def __init__(self, db_path="ml_knowledge.db"):
        self.db_path = db_path
        self.logger = logging.getLogger('parser.ai.learning')
        # 🔥 КОМПОНЕНТЫ МОЗГА
        self.freshness_detector = None  # Детектор свежести
        self.freshness_scaler = None    # Нормализатор фич

        # 🔥 БАЗА ЗНАНИЙ
        self.knowledge_base = {
            'freshness_patterns': defaultdict(list),
            'timing_patterns': defaultdict(dict),
            'successful_queries': defaultdict(list),
            'category_insights': defaultdict(dict),
            'seller_patterns': defaultdict(dict),
            'price_trends': defaultdict(list)
        }

        # 🔥 ИСТОРИЯ ОБУЧЕНИЯ
        self.learning_history = deque(maxlen=10000)  # 10000 последних товаров
        self.found_items_history = set()  # Хэши уже обработанных товаров
        self.improvement_rate = 0.0

        # 🔥 МЕТРИКИ
        self.total_learned = 0
        self.fresh_items_found = 0
        self.successful_searches = 0
        self.avg_freshness_score = 0.0

        # 🔥 ФЛАГИ
        self.is_initialized = False
        self.continuous_learning = True

        logger.info("🧠 МОЗГ СИСТЕМЫ инициализирован")

    # 🔥 УТИЛИТЫ ДЛЯ БЕЗОПАСНОГО ПРЕОБРАЗОВАНИЯ
    def _safe_float(self, value, default=0.0):
        """Безопасное преобразование в float"""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    def _safe_int(self, value, default=0):
        """Безопасное преобразование в int"""
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    async def initialize_from_database(self):
        """🚀 ИНИЦИАЛИЗАЦИЯ МОЗГА ИЗ ВСЕЙ БАЗЫ ДАННЫХ"""
        try:
            from apps.website.models import FoundItem
            from asgiref.sync import sync_to_async

            logger.info("🔍 Загрузка ВСЕХ знаний из базы данных...")

            # 🔥 БЕРЕМ ВСЕ ТОВАРЫ БЕЗ ОГРАНИЧЕНИЙ
            all_items = await sync_to_async(list)(
                FoundItem.objects.all().values(
                    'title', 'description', 'price', 'category',
                    'seller_rating', 'reviews_count', 'found_at',
                    'posted_date', 'ml_freshness_score', 'priority_score',
                    'views_count', 'images'
                )
            )

            if not all_items:
                logger.warning("⚠️ В базе нет данных для обучения мозга")
                return False

            total_items = len(all_items)
            logger.info(f"📚 Загружено ВСЕГО {total_items} товаров для обучения мозга")

            # 🔥 ОБУЧАЕМ МОЗГ НА ВСЕХ ТОВАРАХ
            for i, item in enumerate(all_items, 1):
                await self._deep_learn_from_item(item)
                if i % 500 == 0:  # Логируем каждые 500 товаров
                    logger.info(f"📖 Обучили {i}/{total_items} товаров ({i/total_items*100:.1f}%)")

            # 🔥 ОБУЧАЕМ МОДЕЛИ
            await self._train_freshness_detector()

            self.is_initialized = True
            self.total_learned = total_items

            logger.info(f"🧠 МОЗГ ОБУЧЕН НА {total_items} ТОВАРАХ!")
            logger.info(f"🎯 Найдено свежих товаров: {self.fresh_items_found}")

            # Сохраняем состояние
            await self._save_brain_state()

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации мозга: {e}")
            return False

    async def _deep_learn_from_item(self, item):
        """🎯 ГЛУБОКОЕ ОБУЧЕНИЕ НА ОДНОМ ТОВАРЕ"""
        try:
            # 🔥 КОНВЕРТИРУЕМ ВСЕ ДАННЫЕ
            insights = {
                'timestamp': datetime.now().isoformat(),
                'item_data': {
                    'title': str(item.get('title', '')),
                    'description': str(item.get('description', '')),
                    'price': self._safe_float(item.get('price', 0)),
                    'category': str(item.get('category', 'unknown')),
                    'seller_rating': self._safe_float(item.get('seller_rating', 0)),
                    'reviews_count': self._safe_int(item.get('reviews_count', 0)),
                    'freshness_score': self._safe_float(item.get('ml_freshness_score', 0))
                },
                'freshness_score': self._safe_float(item.get('ml_freshness_score', 0)),
                'category': str(item.get('category', 'unknown')),
                'found_time': item.get('found_at', datetime.now()),
                'seller_rating': self._safe_float(item.get('seller_rating', 0)),
                'price': self._safe_float(item.get('price', 0))
            }

            # 🔥 АНАЛИЗ СВЕЖЕСТИ
            await self._analyze_freshness_patterns(item)

            # 🔥 АНАЛИЗ ВРЕМЕНИ
            await self._analyze_timing_patterns(item)

            # 🔥 АНАЛИЗ ЦЕН
            await self._analyze_price_patterns(item)

            # 🔥 АНАЛИЗ ПРОДАВЦОВ
            await self._analyze_seller_patterns(item)

            # 🔥 АНАЛИЗ КАТЕГОРИЙ
            await self._analyze_category_patterns(item)

            # Сохраняем в историю
            self.learning_history.append(insights)

            # Обновляем метрики
            freshness = insights['freshness_score']
            if freshness > 0.7:
                self.fresh_items_found += 1

            # Обновляем среднюю свежесть
            if self.total_learned > 0:
                self.avg_freshness_score = (
                    (self.avg_freshness_score * self.total_learned + freshness) /
                    (self.total_learned + 1)
                )
            else:
                self.avg_freshness_score = freshness

            self.total_learned += 1

            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка глубокого обучения: {e}")
            return False

    async def _analyze_freshness_patterns(self, item):
        """🔥 АНАЛИЗ ПАТТЕРНОВ СВЕЖЕСТИ"""
        try:
            category = str(item.get('category', 'unknown'))
            freshness = self._safe_float(item.get('ml_freshness_score', 0))
            posted_date = item.get('posted_date')

            if not posted_date:
                return

            # Анализируем время публикации
            if isinstance(posted_date, str):
                try:
                    posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                except:
                    return

            hours_ago = (datetime.now() - posted_date).total_seconds() / 3600

            # Сохраняем паттерн
            title_lower = str(item.get('title', '')).lower()
            desc_lower = str(item.get('description', '')).lower()

            pattern = {
                'hours_ago': hours_ago,
                'freshness_score': freshness,
                'has_urgency': 'срочно' in title_lower or 'срочно' in desc_lower,
                'is_new': 'новый' in title_lower or 'новый' in desc_lower,
                'seller_type': 'Компания' if self._safe_float(item.get('seller_rating', 0)) > 4.8 else 'Частное лицо'
            }

            self.knowledge_base['freshness_patterns'][category].append(pattern)

            # Ограничиваем размер
            if len(self.knowledge_base['freshness_patterns'][category]) > 1000:
                self.knowledge_base['freshness_patterns'][category] = \
                    self.knowledge_base['freshness_patterns'][category][-1000:]

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа свежести: {e}")

    async def _analyze_timing_patterns(self, item):
        """🕒 АНАЛИЗ ВРЕМЕННЫХ ПАТТЕРНОВ"""
        try:
            category = str(item.get('category', 'unknown'))
            found_at = item.get('found_at', datetime.now())

            if isinstance(found_at, str):
                found_at = datetime.fromisoformat(found_at.replace('Z', '+00:00'))

            hour = found_at.hour
            day_of_week = found_at.weekday()

            if category not in self.knowledge_base['timing_patterns']:
                self.knowledge_base['timing_patterns'][category] = {
                    'hourly_counts': [0] * 24,
                    'daily_counts': [0] * 7,
                    'best_hours': [],
                    'best_days': []
                }

            self.knowledge_base['timing_patterns'][category]['hourly_counts'][hour] += 1
            self.knowledge_base['timing_patterns'][category]['daily_counts'][day_of_week] += 1

            # Пересчитываем лучшие часы
            hourly = self.knowledge_base['timing_patterns'][category]['hourly_counts']
            self.knowledge_base['timing_patterns'][category]['best_hours'] = \
                sorted(range(24), key=lambda h: hourly[h], reverse=True)[:3]

            # Пересчитываем лучшие дни
            daily = self.knowledge_base['timing_patterns'][category]['daily_counts']
            self.knowledge_base['timing_patterns'][category]['best_days'] = \
                sorted(range(7), key=lambda d: daily[d], reverse=True)[:2]

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа времени: {e}")

    async def _analyze_price_patterns(self, item):
        """💰 АНАЛИЗ ЦЕНОВЫХ ПАТТЕРНОВ"""
        try:
            category = str(item.get('category', 'unknown'))
            price = self._safe_float(item.get('price', 0))

            if price > 0:
                self.knowledge_base['price_trends'][category].append({
                    'price': price,
                    'timestamp': datetime.now().isoformat(),
                    'freshness': self._safe_float(item.get('ml_freshness_score', 0))
                })

                # Ограничиваем размер
                if len(self.knowledge_base['price_trends'][category]) > 500:
                    self.knowledge_base['price_trends'][category] = \
                        self.knowledge_base['price_trends'][category][-500:]

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа цен: {e}")

    async def _analyze_seller_patterns(self, item):
        """👤 АНАЛИЗ ПАТТЕРНОВ ПРОДАВЦОВ"""
        try:
            seller_rating = self._safe_float(item.get('seller_rating', 0))
            reviews_count = self._safe_int(item.get('reviews_count', 0))
            category = str(item.get('category', 'unknown'))

            if seller_rating > 0:
                if category not in self.knowledge_base['seller_patterns']:
                    self.knowledge_base['seller_patterns'][category] = {
                        'total_sellers': 0,
                        'avg_rating': 0.0,
                        'top_sellers': []
                    }

                seller_data = {
                    'rating': seller_rating,
                    'reviews': reviews_count,
                    'freshness_avg': self._safe_float(item.get('ml_freshness_score', 0))
                }

                # Обновляем средний рейтинг
                current_avg = self._safe_float(self.knowledge_base['seller_patterns'][category]['avg_rating'])
                total = self._safe_int(self.knowledge_base['seller_patterns'][category]['total_sellers'])

                self.knowledge_base['seller_patterns'][category]['avg_rating'] = \
                    (current_avg * total + seller_rating) / (total + 1)
                self.knowledge_base['seller_patterns'][category]['total_sellers'] = total + 1

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа продавцов: {e}")

    async def _analyze_category_patterns(self, item):
        """🏷️ АНАЛИЗ ПАТТЕРНОВ КАТЕГОРИЙ"""
        try:
            category = str(item.get('category', 'unknown'))

            if category not in self.knowledge_base['category_insights']:
                self.knowledge_base['category_insights'][category] = {
                    'total_items': 0,
                    'avg_freshness': 0.0,
                    'avg_price': 0.0,
                    'success_rate': 0.0,
                    'last_updated': datetime.now().isoformat()
                }

            insights = self.knowledge_base['category_insights'][category]

            # 🔥 КОНВЕРТИРУЕМ ВСЁ В ЧИСЛА
            total = self._safe_int(insights['total_items'])
            current_avg_freshness = self._safe_float(insights['avg_freshness'])
            current_avg_price = self._safe_float(insights['avg_price'])

            # Получаем значения из item
            item_freshness = self._safe_float(item.get('ml_freshness_score', 0))
            item_price = self._safe_float(item.get('price', 0))

            # 🔥 ПРОСТОЙ РАСЧЁТ БЕЗ ОШИБОК
            if total == 0:
                insights['avg_freshness'] = item_freshness
                if item_price > 0:
                    insights['avg_price'] = item_price
            else:
                insights['avg_freshness'] = (current_avg_freshness * total + item_freshness) / (total + 1)
                if item_price > 0:
                    insights['avg_price'] = (current_avg_price * total + item_price) / (total + 1)

            insights['total_items'] = total + 1
            insights['last_updated'] = datetime.now().isoformat()

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа категорий: {e}")

    async def _train_freshness_detector(self):
        """🎯 ОБУЧЕНИЕ ДЕТЕКТОРА СВЕЖЕСТИ"""
        try:
            if not self.knowledge_base['freshness_patterns']:
                logger.warning("⚠️ Нет данных для обучения детектора свежести")
                return False

            # Собираем данные для обучения
            X, y = [], []

            for category, patterns in self.knowledge_base['freshness_patterns'].items():
                for pattern in patterns:
                    features = [
                        pattern['hours_ago'] / 168,  # Нормализуем до недели
                        1.0 if pattern['has_urgency'] else 0.0,
                        1.0 if pattern['is_new'] else 0.0,
                        1.0 if pattern['seller_type'] == 'Компания' else 0.0,
                        pattern['freshness_score']  # Это target
                    ]

                    X.append(features[:-1])  # Все кроме target
                    y.append(features[-1])   # Только target

            if len(X) < 50:
                logger.warning(f"⚠️ Недостаточно данных для обучения: {len(X)} samples")
                return False

            # Создаем и обучаем модель
            self.freshness_scaler = StandardScaler()
            X_scaled = self.freshness_scaler.fit_transform(X)

            # Преобразуем свежесть в классы
            y_classes = np.digitize(y, bins=[0.3, 0.6, 0.8])

            self.freshness_detector = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )

            self.freshness_detector.fit(X_scaled, y_classes)

            logger.info(f"🎯 Детектор свежести обучен на {len(X)} samples")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обучения детектора свежести: {e}")
            return False

    async def predict_freshness_category(self, product_data):
        """🔍 ПРЕДСКАЗАНИЕ КАТЕГОРИИ СВЕЖЕСТИ"""
        try:
            if not self.freshness_detector or not self.freshness_scaler:
                return await self._simple_freshness_prediction(product_data)

            # Извлекаем фичи
            hours_ago = await self._get_hours_since_publication(product_data)
            title_lower = str(product_data.get('title', '')).lower()
            desc_lower = str(product_data.get('description', '')).lower()

            has_urgency = 'срочно' in title_lower or 'срочно' in desc_lower
            is_new = 'новый' in title_lower or 'новый' in desc_lower
            seller_type = 'Компания' if self._safe_float(product_data.get('seller_rating', 0)) > 4.8 else 'Частное лицо'

            features = [
                hours_ago / 168,
                1.0 if has_urgency else 0.0,
                1.0 if is_new else 0.0,
                1.0 if seller_type == 'Компания' else 0.0
            ]

            # Масштабируем и предсказываем
            features_scaled = self.freshness_scaler.transform([features])
            prediction = self.freshness_detector.predict(features_scaled)[0]

            # Преобразуем класс в текстовую категорию
            categories = ['💀 Устаревшее', '🌙 Мало свежее', '⚡ Средне свежее', '🔥 Очень свежее']
            return categories[min(prediction, len(categories) - 1)]

        except Exception as e:
            logger.warning(f"⚠️ Ошибка предсказания свежести: {e}")
            return '⚡ Средне свежее'

    async def _simple_freshness_prediction(self, product_data):
        """🔄 ПРОСТОЕ ПРЕДСКАЗАНИЕ СВЕЖЕСТИ"""
        try:
            hours_ago = await self._get_hours_since_publication(product_data)

            if hours_ago < 1:
                return '🔥 Очень свежее'
            elif hours_ago < 6:
                return '🔥 Очень свежее'
            elif hours_ago < 24:
                return '⚡ Средне свежее'
            elif hours_ago < 48:
                return '🌙 Мало свежее'
            else:
                return '💀 Устаревшее'

        except:
            return '⚡ Средне свежее'

    async def _get_hours_since_publication(self, product_data):
        """⏰ Получение часов с публикации"""
        try:
            posted_date = product_data.get('posted_date')
            if posted_date:
                if isinstance(posted_date, str):
                    posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))

                hours_ago = (datetime.now() - posted_date).total_seconds() / 3600
                return hours_ago

            return 24.0
        except:
            return 24.0

    async def get_optimal_search_times(self, category):
        """🕒 ЛУЧШЕЕ ВРЕМЯ ДЛЯ ПОИСКА"""
        try:
            category = str(category)
            if category in self.knowledge_base['timing_patterns']:
                pattern = self.knowledge_base['timing_patterns'][category]
                if pattern['best_hours']:
                    return pattern['best_hours']

            return [9, 14, 19]  # Утро, обед, вечер

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения оптимального времени: {e}")
            return [9, 14, 19]

    async def find_fresh_deals(self, limit=20):
        """🔍 ПОИСК САМЫХ СВЕЖИХ ТОВАРОВ В БАЗЕ (ИСПРАВЛЕННАЯ)"""
        try:
            from apps.website.models import FoundItem
            from asgiref.sync import sync_to_async

            # Ищем товары с высокой свежестью
            fresh_items = await sync_to_async(list)(
                FoundItem.objects.filter(
                    ml_freshness_score__gte=0.7
                ).order_by('-ml_freshness_score', '-found_at')[:limit]
            )

            if not fresh_items:
                return []

            # Форматируем результат
            results = []
            for item in fresh_items:
                # 🔥 БЕЗОПАСНО ПРОВЕРЯЕМ expected_profit
                profit = 0
                try:
                    if hasattr(item, 'expected_profit') and item.expected_profit is not None:
                        profit = self._safe_float(item.expected_profit)
                except:
                    profit = 0

                results.append({
                    'id': item.id,
                    'title': item.title[:50] + '...' if len(item.title) > 50 else item.title,
                    'price': self._safe_float(item.price),
                    'freshness': self._safe_float(item.ml_freshness_score),
                    'category': str(item.category) if item.category else 'Неизвестно',
                    'posted': str(item.posted_date) if item.posted_date else 'Неизвестно',
                    'profit': profit  # 🔥 БЕЗОПАСНО
                })

            return results

        except Exception as e:
            logger.error(f"❌ Ошибка поиска свежих товаров: {e}")
            return []

    async def get_brain_stats(self):
        """📊 СТАТИСТИКА МОЗГА"""
        try:
            total_categories = len(self.knowledge_base['category_insights'])
            total_patterns = sum(len(patterns) for patterns in self.knowledge_base['freshness_patterns'].values())

            # Рассчитываем уровень интеллекта
            intelligence_level = min((self.total_learned / 2000.0), 1.0)

            stats = {
                'brain_version': 'v2.0_smart',
                'total_learned': self._safe_int(self.total_learned),
                'fresh_items_found': self._safe_int(self.fresh_items_found),
                'successful_searches': self._safe_int(self.successful_searches),
                'avg_freshness_score': self._safe_float(self.avg_freshness_score),
                'categories_known': self._safe_int(total_categories),
                'patterns_learned': self._safe_int(total_patterns),
                'intelligence_level': f"{intelligence_level:.1%}",
                'continuous_learning': self.continuous_learning,
                'is_initialized': self.is_initialized,
                'freshness_detector_trained': self.freshness_detector is not None,
                'last_learning': datetime.now().isoformat()
            }

            # 🔥 ТОП КАТЕГОРИЙ ПО СВЕЖЕСТИ
            top_categories = []
            for category, insights in self.knowledge_base['category_insights'].items():
                if insights['total_items'] >= 3:  # Минимум 3 товара
                    avg_freshness = self._safe_float(insights.get('avg_freshness', 0))
                    total_items = self._safe_int(insights.get('total_items', 0))

                    if avg_freshness > 0:  # Только с данными
                        top_categories.append({
                            'name': str(category),
                            'avg_freshness': round(avg_freshness, 3),
                            'total_items': total_items
                        })

            # Сортируем по свежести
            top_categories.sort(key=lambda x: x['avg_freshness'], reverse=True)
            stats['top_fresh_categories'] = top_categories[:5]

            return stats

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}

    async def _save_brain_state(self):
        """💾 СОХРАНЕНИЕ СОСТОЯНИЯ МОЗГА"""
        try:
            def convert_for_json(obj):
                """Конвертация для JSON"""
                if isinstance(obj, (dict, list, tuple, str, int, bool, type(None), float)):
                    return obj
                elif hasattr(obj, '__dict__'):
                    return obj.__dict__
                else:
                    return str(obj)

            state = {
                'knowledge_base': self.knowledge_base,
                'stats': {
                    'total_learned': self.total_learned,
                    'fresh_items_found': self.fresh_items_found,
                    'avg_freshness_score': float(self.avg_freshness_score),
                    'successful_searches': self.successful_searches
                },
                'last_saved': datetime.now().isoformat()
            }

            with open('brain_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, default=convert_for_json, ensure_ascii=False, indent=2)

            logger.info("💾 Состояние мозга сохранено")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка сохранения мозга: {e}")

    async def load_brain_state(self):
        """📂 ЗАГРУЗКА СОСТОЯНИЯ МОЗГА"""
        try:
            with open('brain_state.json', 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.knowledge_base = defaultdict(list, state.get('knowledge_base', {}))

            stats = state.get('stats', {})
            self.total_learned = self._safe_int(stats.get('total_learned', 0))
            self.fresh_items_found = self._safe_int(stats.get('fresh_items_found', 0))
            self.avg_freshness_score = self._safe_float(stats.get('avg_freshness_score', 0))
            self.successful_searches = self._safe_int(stats.get('successful_searches', 0))

            self.is_initialized = True
            logger.info(f"🧠 Мозг загружен: {self.total_learned} знаний")

            return True

        except FileNotFoundError:
            logger.info("🧠 Мозг не найден, будет создан новый")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки мозга: {e}")
            return False

    async def analyze_database(self):
        """📊 АНАЛИЗ ВСЕЙ БАЗЫ ДАННЫХ"""
        try:
            from apps.website.models import FoundItem
            from asgiref.sync import sync_to_async
            from django.db.models import Count, Avg

            print("\n" + "=" * 60)
            print("📊 АНАЛИЗ ВСЕЙ БАЗЫ ДАННЫХ")
            print("=" * 60)

            # 1. Общая статистика
            total_items = await sync_to_async(FoundItem.objects.count)()
            print(f"\n📦 ВСЕГО ТОВАРОВ В БАЗЕ: {total_items}")

            # 2. Распределение по свежести
            freshness_stats = await sync_to_async(list)(
                FoundItem.objects.extra(
                    select={
                        'freshness_range': """
                            CASE 
                                WHEN ml_freshness_score >= 0.8 THEN '🔥 Очень свежее (>0.8)'
                                WHEN ml_freshness_score >= 0.5 THEN '⚡ Средне свежее (0.5-0.8)'
                                WHEN ml_freshness_score >= 0.3 THEN '🌙 Мало свежее (0.3-0.5)'
                                ELSE '💀 Устаревшее (<0.3)'
                            END
                        """
                    }
                ).values('freshness_range').annotate(count=Count('id')).order_by('-count')
            )

            print("\n📈 РАСПРЕДЕЛЕНИЕ ПО СВЕЖЕСТИ:")
            for stat in freshness_stats:
                percentage = (stat['count'] / total_items) * 100
                print(f"  • {stat['freshness_range']}: {stat['count']} ({percentage:.1f}%)")

            # 3. Топ категорий по количеству
            top_categories = await sync_to_async(list)(
                FoundItem.objects.values('category').annotate(
                    count=Count('id'),
                    avg_freshness=Avg('ml_freshness_score'),
                    avg_price=Avg('price')
                ).filter(category__isnull=False).order_by('-count')[:10]
            )

            print(f"\n🏆 ТОП-10 КАТЕГОРИЙ ПО КОЛИЧЕСТВУ:")
            for cat in top_categories:
                avg_freshness = self._safe_float(cat.get('avg_freshness', 0))
                avg_price = self._safe_float(cat.get('avg_price', 0))
                print(
                    f"  • {cat['category']}: {cat['count']} товаров, свежесть: {avg_freshness:.2f}, цена: {avg_price:.0f} руб")

            # 4. Самые свежие товары
            fresh_items = await sync_to_async(list)(
                FoundItem.objects.filter(ml_freshness_score__gte=0.8)
                .order_by('-ml_freshness_score', '-found_at')[:5]
            )

            print(f"\n🎯 САМЫЕ СВЕЖИЕ ТОВАРЫ (свежесть > 0.8):")
            for item in fresh_items:
                price = self._safe_float(item.price) if item.price else 0
                freshness = self._safe_float(item.ml_freshness_score) if item.ml_freshness_score else 0
                title = str(item.title)[:40] + '...' if len(str(item.title)) > 40 else str(item.title)
                print(f"  • {title} - свежесть: {freshness:.2f}, цена: {price} руб")

            print("\n" + "=" * 60)
            return True

        except Exception as e:
            print(f"❌ Ошибка анализа базы: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 🔥 ПАТЧ ДЛЯ СОВМЕСТИМОСТИ С ПАРСЕРОМ
    async def load_learning_state(self):
        """📂 Загрузка состояния обучения (патч для совместимости)"""
        try:
            import logging
            logger = logging.getLogger('parser.ai.learning')
            logger.info("📂 Загрузка состояния обучения...")
            return await self.load_brain_state()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка load_learning_state: {e}")
            return False