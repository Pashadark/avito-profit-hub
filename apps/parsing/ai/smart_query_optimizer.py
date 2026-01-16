import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any
import hashlib

logger = logging.getLogger('parser.ai.queries')

class QueryOptimizer:
    """🎯 УМНЫЙ ОПТИМИЗАТОР ПОИСКОВЫХ ЗАПРОСОВ"""

    def __init__(self):
        self.freshness_modifiers = [
            "сегодня", "только что", "свежий", "новый", "только добавлен",
            "срочно", "быстрая продажа", "только появился"
        ]

        self.time_modifiers = {
            'morning': ["утро", "сегодня утром", "утренняя"],
            'afternoon': ["день", "сегодня днем", "дневная"],
            'evening': ["вечер", "сегодня вечером", "вечерняя"],
            'night': ["ночь", "сегодня ночью", "ночная"]
        }

        self.successful_queries = {}
        self.query_stats = {}

    async def optimize_queries(self, base_queries: List[str], time_of_day: str = None) -> List[str]:
        """🎯 Оптимизация запросов для максимальной эффективности"""
        try:
            logger.info(f"🔍 Оптимизация {len(base_queries)} запросов...")

            optimized_queries = set()

            for query in base_queries:
                # Базовые варианты
                base_optimized = await self._add_freshness_modifiers(query)
                optimized_queries.update(base_optimized)

                # Временные варианты
                if time_of_day:
                    time_optimized = await self._add_time_modifiers(query, time_of_day)
                    optimized_queries.update(time_optimized)

                # Синонимичные варианты
                synonym_optimized = await self._generate_synonyms(query)
                optimized_queries.update(synonym_optimized)

            final_queries = list(optimized_queries)
            logger.info(f"🚀 Сгенерировано {len(final_queries)} оптимизированных запросов")

            return final_queries[:15]  # Ограничиваем количество

        except Exception as e:
            logger.error(f"❌ Ошибка оптимизации запросов: {e}")
            return base_queries

    async def _add_freshness_modifiers(self, query: str) -> List[str]:
        """➕ Добавление модификаторов свежести"""
        variants = []
        top_modifiers = self.freshness_modifiers[:3]

        for modifier in top_modifiers:
            variants.append(f"{modifier} {query}")
            variants.append(f"{query} {modifier}")

        return variants

    async def _add_time_modifiers(self, query: str, time_of_day: str) -> List[str]:
        """🕒 Добавление временных модификаторов"""
        variants = []

        if time_of_day in self.time_modifiers:
            modifiers = self.time_modifiers[time_of_day]
            for modifier in modifiers:
                variants.append(f"{query} {modifier}")
                variants.append(f"{modifier} {query}")

        return variants

    async def _generate_synonyms(self, query: str) -> List[str]:
        """🔄 Генерация синонимичных вариантов"""
        synonyms_map = {
            'б/у': ['бу', 'подержанный', 'second hand'],
            'новый': ['новенький', 'с гарантией', 'оригинал'],
            'срочно': ['срочная продажа', 'нужно быстро', 'быстрая продажа'],
            'iphone': ['айфон', 'iphone', 'apple iphone'],
            'macbook': ['макбук', 'mac book', 'apple macbook']
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

    async def learn_from_success(self, successful_queries: List[str]):
        """🧠 Обучение на успешных запросах"""
        try:
            for query in successful_queries:
                query_hash = self._hash_query(query)

                if query_hash not in self.successful_queries:
                    self.successful_queries[query_hash] = {
                        'query': query,
                        'success_count': 0,
                        'last_used': datetime.now().isoformat()
                    }

                self.successful_queries[query_hash]['success_count'] += 1

            logger.info(f"📚 Обучено на {len(successful_queries)} успешных запросах")

        except Exception as e:
            logger.error(f"❌ Ошибка обучения на запросах: {e}")

    def _hash_query(self, query: str) -> str:
        """🔑 Хеширование запроса"""
        return hashlib.md5(query.encode()).hexdigest()[:8]

    async def get_top_queries(self, limit: int = 10) -> List[str]:
        """🏆 Топ успешных запросов"""
        try:
            sorted_queries = sorted(
                self.successful_queries.values(),
                key=lambda x: x['success_count'],
                reverse=True
            )
            return [q['query'] for q in sorted_queries[:limit]]
        except: return []

    async def get_optimization_stats(self) -> Dict[str, Any]:
        """📊 Статистика оптимизации"""
        return {
            'total_successful_queries': len(self.successful_queries),
            'top_modifiers': self.freshness_modifiers[:5],
            'learning_enabled': True,
            'most_successful_queries': await self.get_top_queries(5)
        }