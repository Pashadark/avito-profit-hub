import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter
import hashlib

logger = logging.getLogger('parser.ai')


class QueryOptimizer:
    """🎯 УМНЫЙ ОПТИМИЗАТОР ПОИСКОВЫХ ЗАПРОСОВ"""

    def __init__(self):
        self.freshness_modifiers = [
            "сегодня",
            "только что",
            "свежий",
            "новый",
            "только добавлен",
            "срочно",
            "быстрая продажа",
            "только появился",
            "новинка"
        ]

        self.time_specific_modifiers = {
            'morning': ["утро", "сегодня утром", "утренняя"],
            'afternoon': ["день", "сегодня днем", "дневная"],
            'evening': ["вечер", "сегодня вечером", "вечерняя"],
            'night': ["ночь", "сегодня ночью", "ночная"]
        }

        self.successful_combinations = {}
        self.query_stats = {}

    async def optimize_queries(self, base_queries: List[str], time_of_day: str = None) -> List[str]:
        """🎯 ОПТИМИЗАЦИЯ запросов для поиска СВЕЖИХ объявлений"""
        try:
            logger.info(f"🔍 Оптимизация {len(base_queries)} запросов для свежести...")

            optimized_queries = set()

            for query in base_queries:
                # 🔥 БАЗОВЫЕ ВАРИАНТЫ СО СВЕЖЕСТЬЮ
                base_fresh = await self._add_freshness_modifiers(query)
                optimized_queries.update(base_fresh)

                # 🔥 ВРЕМЕННЫЕ ВАРИАНТЫ
                if time_of_day:
                    time_fresh = await self._add_time_specific_modifiers(query, time_of_day)
                    optimized_queries.update(time_fresh)

                # 🔥 СИНОНИМИЧНЫЕ ВАРИАНТЫ
                synonym_fresh = await self._generate_synonym_variants(query)
                optimized_queries.update(synonym_fresh)

            final_queries = list(optimized_queries)
            logger.info(f"🚀 Сгенерировано {len(final_queries)} оптимизированных запросов")

            return final_queries[:20]  # Ограничиваем количество

        except Exception as e:
            logger.error(f"❌ Ошибка оптимизации запросов: {e}")
            return base_queries

    async def _add_freshness_modifiers(self, query: str) -> List[str]:
        """➕ Добавляем модификаторы свежести к запросу"""
        variants = []

        # 🔥 ТОП-3 МОДИФИКАТОРА СВЕЖЕСТИ
        top_modifiers = self.freshness_modifiers[:3]

        for modifier in top_modifiers:
            # ДОБАВЛЯЕМ В НАЧАЛО
            variants.append(f"{modifier} {query}")
            # ДОБАВЛЯЕМ В КОНЕЦ
            variants.append(f"{query} {modifier}")

        return variants

    async def _add_time_specific_modifiers(self, query: str, time_of_day: str) -> List[str]:
        """🕒 Добавляем временные модификаторы"""
        variants = []

        if time_of_day in self.time_specific_modifiers:
            modifiers = self.time_specific_modifiers[time_of_day]

            for modifier in modifiers:
                variants.append(f"{query} {modifier}")
                variants.append(f"{modifier} {query}")

        return variants

    async def _generate_synonym_variants(self, query: str) -> List[str]:
        """🔄 Генерируем синонимичные варианты"""
        synonyms_map = {
            'б/у': ['бу', 'подержанный', 'second hand'],
            'новый': ['новенький', 'с гарантией', 'оригинал'],
            'срочно': ['срочная продажа', 'нужно быстро', 'быстрая продажа'],
            'iphone': ['айфон', 'iphone', 'apple iphone'],
            'macbook': ['макбук', 'mac book', 'apple macbook'],
            'samsung': ['самсунг', 'samsung galaxy'],
            'телефон': ['смартфон', 'mobile', 'мобильный'],
            'ноутбук': ['лэптоп', 'laptop', 'ноут']
        }

        variants = []
        words = query.lower().split()

        for i, word in enumerate(words):
            if word in synonyms_map:
                for synonym in synonyms_map[word]:
                    new_words = words.copy()
                    new_words[i] = synonym
                    variants.append(' '.join(new_words))

        return variants

    async def learn_from_successful_queries(self, successful_queries: List[str]):
        """🧠 Учимся на успешных запросах"""
        try:
            for query in successful_queries:
                query_hash = self._hash_query(query)

                if query_hash not in self.successful_combinations:
                    self.successful_combinations[query_hash] = {
                        'query': query,
                        'success_count': 0,
                        'last_used': datetime.now().isoformat()
                    }

                self.successful_combinations[query_hash]['success_count'] += 1
                self.successful_combinations[query_hash]['last_used'] = datetime.now().isoformat()

            logger.info(f"📚 Обучено на {len(successful_queries)} успешных запросах")

        except Exception as e:
            logger.error(f"❌ Ошибка обучения на успешных запросах: {e}")

    def _hash_query(self, query: str) -> str:
        """🔑 Хешируем запрос для идентификации"""
        return hashlib.md5(query.encode()).hexdigest()[:8]

    async def get_top_queries(self, limit: int = 10) -> List[str]:
        """🏆 Возвращает топ успешных запросов"""
        try:
            sorted_queries = sorted(
                self.successful_combinations.values(),
                key=lambda x: x['success_count'],
                reverse=True
            )

            return [q['query'] for q in sorted_queries[:limit]]

        except Exception as e:
            logger.error(f"❌ Ошибка получения топ запросов: {e}")
            return []

    async def get_optimization_stats(self) -> Dict[str, Any]:
        """📊 Статистика оптимизации"""
        return {
            'total_successful_queries': len(self.successful_combinations),
            'top_modifiers': self.freshness_modifiers[:5],
            'learning_enabled': True,
            'success_rate': self._calculate_success_rate(),
            'most_successful_combinations': await self.get_top_queries(5)
        }

    def _calculate_success_rate(self) -> float:
        """📈 Расчет успешности оптимизации"""
        if not self.successful_combinations:
            return 0.0

        total_success = sum(q['success_count'] for q in self.successful_combinations.values())
        avg_success = total_success / len(self.successful_combinations)

        return min(avg_success / 10.0, 1.0)  # Нормализуем

    async def optimize_for_category(self, category: str, base_queries: List[str]) -> List[str]:
        """🎯 Оптимизация запросов для конкретной категории"""
        try:
            category_specific_modifiers = {
                'electronics': ['с гарантией', 'оригинал', 'новый', 'не распакован'],
                'clothing': ['новый с биркой', 'не ношенный', 'с этикеткой'],
                'automotive': ['пробег', 'состояние отличное', 'обслужен'],
                'real_estate': ['свежий', 'сегодня', 'срочно']
            }

            optimized_queries = set()

            for query in base_queries:
                # Добавляем категорийные модификаторы
                if category in category_specific_modifiers:
                    for modifier in category_specific_modifiers[category][:2]:
                        optimized_queries.add(f"{query} {modifier}")
                        optimized_queries.add(f"{modifier} {query}")

                # Добавляем общие модификаторы свежести
                base_optimized = await self._add_freshness_modifiers(query)
                optimized_queries.update(base_optimized)

            return list(optimized_queries)[:15]

        except Exception as e:
            logger.error(f"❌ Ошибка оптимизации для категории {category}: {e}")
            return base_queries

    async def analyze_query_performance(self, query: str, found_items: int, total_items: int):
        """📊 Анализ производительности запроса"""
        try:
            success_rate = found_items / total_items if total_items > 0 else 0

            if query not in self.query_stats:
                self.query_stats[query] = {
                    'total_searches': 0,
                    'successful_searches': 0,
                    'total_found': 0,
                    'success_rate': 0
                }

            stats = self.query_stats[query]
            stats['total_searches'] += 1
            stats['total_found'] += found_items

            if found_items > 0:
                stats['successful_searches'] += 1

            stats['success_rate'] = stats['successful_searches'] / stats['total_searches'] if stats[
                                                                                                  'total_searches'] > 0 else 0

            # Обновляем успешные комбинации если запрос успешен
            if success_rate > 0.3:  # Если успешность выше 30%
                await self.learn_from_successful_queries([query])

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа производительности запроса: {e}")

    async def get_query_recommendations(self, base_query: str, limit: int = 5) -> List[str]:
        """💡 Рекомендации по улучшению запроса"""
        try:
            recommendations = set()

            # Добавляем модификаторы свежести
            freshness_recs = await self._add_freshness_modifiers(base_query)
            recommendations.update(freshness_recs)

            # Добавляем синонимы
            synonym_recs = await self._generate_synonym_variants(base_query)
            recommendations.update(synonym_recs)

            # Добавляем успешные комбинации из истории
            top_queries = await self.get_top_queries(limit)
            for successful_query in top_queries:
                if base_query in successful_query:
                    recommendations.add(successful_query)

            return list(recommendations)[:limit]

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения рекомендаций: {e}")
            return [base_query]