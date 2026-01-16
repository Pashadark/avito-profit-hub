import logging
import numpy as np
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import sqlite3

logger = logging.getLogger('parser.ai')


class PublicationPredictor:
    """🔥 ПРЕДСКАЗАТЕЛЬ ВОЛН ПУБЛИКАЦИЙ СВЕЖИХ ОБЪЯВЛЕНИЙ"""

    def __init__(self, db_path="publication_patterns.db"):
        self.db_path = db_path
        self.publication_cycles = {}
        self.learning_rate = 0.1
        self.pattern_confidence = {}
        logger.info("🕒 Предсказатель времени публикации инициализирован")

    async def predict_publication_time(self, product_data: Dict[str, Any]) -> str:
        """🎯 АСИНХРОННОЕ предсказание времени публикации"""
        try:
            # Имитируем асинхронную работу
            await asyncio.sleep(0.001)

            time_listed = product_data.get('time_listed', 24)

            if time_listed <= 1:
                return "менее часа назад"
            elif time_listed <= 3:
                return "1-3 часа назад"
            elif time_listed <= 6:
                return "3-6 часов назад"
            elif time_listed <= 12:
                return "6-12 часов назад"
            else:
                return "более 12 часов назад"

        except Exception as e:
            logger.warning(f"⚠️ Ошибка предсказания времени публикации: {e}")
            return "Неизвестно"

    async def get_prediction_stats(self) -> Dict[str, Any]:
        """📊 Статистика предсказаний"""
        return {
            'status': 'active',
            'type': 'PublicationPredictor',
            'version': '1.0',
            'categories_analyzed': len(self.publication_cycles),
            'total_publications': sum(data['total_publications'] for data in self.publication_cycles.values())
        }

    async def analyze_publication_patterns(self, found_items):
        """📊 Анализирует паттерны публикаций свежих объявлений"""
        try:
            logger.info(f"🔍 Анализ паттернов публикаций на {len(found_items)} объявлениях...")

            for item in found_items:
                category = item.get('category', 'unknown')
                found_time = item.get('found_at')

                if category and found_time:
                    await self._update_publication_cycle(category, found_time)

            # 🔥 ПЕРЕСЧИТЫВАЕМ УВЕРЕННОСТЬ ПАТТЕРНОВ
            await self._recalculate_pattern_confidence()

            logger.info("🎯 Анализ паттернов публикаций завершен")

        except Exception as e:
            logger.error(f"❌ Ошибка анализа паттернов публикаций: {e}")

    async def _update_publication_cycle(self, category, found_time):
        """🔄 Обновляет циклы публикаций для категории"""
        try:
            if isinstance(found_time, str):
                found_time = datetime.fromisoformat(found_time.replace('Z', '+00:00'))

            if category not in self.publication_cycles:
                self.publication_cycles[category] = {
                    'hourly_pattern': [0] * 24,
                    'daily_pattern': [0] * 7,
                    'weekly_pattern': [0] * 4,
                    'total_publications': 0,
                    'last_updated': found_time.isoformat()
                }

            hour = found_time.hour
            day = found_time.weekday()
            week = found_time.isocalendar()[1] % 4  # Неделя месяца

            # ОБНОВЛЯЕМ ПАТТЕРНЫ
            self.publication_cycles[category]['hourly_pattern'][hour] += 1
            self.publication_cycles[category]['daily_pattern'][day] += 1
            self.publication_cycles[category]['weekly_pattern'][week] += 1
            self.publication_cycles[category]['total_publications'] += 1
            self.publication_cycles[category]['last_updated'] = found_time.isoformat()

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления цикла публикаций: {e}")

    async def _recalculate_pattern_confidence(self):
        """🎯 Пересчитывает уверенность паттернов"""
        for category, data in self.publication_cycles.items():
            total_pubs = data['total_publications']
            if total_pubs > 100:
                self.pattern_confidence[category] = 0.9
            elif total_pubs > 50:
                self.pattern_confidence[category] = 0.7
            elif total_pubs > 20:
                self.pattern_confidence[category] = 0.5
            else:
                self.pattern_confidence[category] = 0.3

    async def predict_next_publication_wave(self, category):
        """🔮 Предсказывает следующую волну публикаций"""
        try:
            if category not in self.publication_cycles:
                return await self._get_default_prediction()

            cycle_data = self.publication_cycles[category]

            if cycle_data['total_publications'] < 10:
                return await self._get_default_prediction()

            # 🔥 АНАЛИЗИРУЕМ ПАТТЕРНЫ
            hourly_peaks = self._find_peak_hours(cycle_data['hourly_pattern'])
            daily_peaks = self._find_peak_days(cycle_data['daily_pattern'])
            weekly_peaks = self._find_peak_weeks(cycle_data['weekly_pattern'])

            # 🔥 РАСЧЕТ УВЕРЕННОСТИ
            confidence = self._calculate_confidence(cycle_data)

            prediction = {
                'peak_hours': hourly_peaks,
                'peak_days': daily_peaks,
                'peak_weeks': weekly_peaks,
                'confidence': confidence,
                'next_recommended_search': self._get_next_search_time(hourly_peaks),
                'total_analyzed_publications': cycle_data['total_publications']
            }

            logger.info(f"🔮 Предсказание для {category}: {prediction}")
            return prediction

        except Exception as e:
            logger.error(f"❌ Ошибка предсказания волн публикаций: {e}")
            return await self._get_default_prediction()

    def _find_peak_hours(self, hourly_pattern):
        """🕒 Находит пиковые часы публикаций"""
        if not any(hourly_pattern):
            return [9, 14, 19]  # Умолчания

        # НОРМАЛИЗУЕМ
        total = sum(hourly_pattern)
        normalized = [count / total for count in hourly_pattern]

        # НАХОДИМ ПИКИ (выше среднего + 1 стандартное отклонение)
        mean = np.mean(normalized)
        std = np.std(normalized)
        threshold = mean + std

        peaks = [i for i, value in enumerate(normalized) if value > threshold]

        return peaks if peaks else [i for i, value in enumerate(normalized) if value > mean][:3]

    def _find_peak_days(self, daily_pattern):
        """📅 Находит пиковые дни публикаций"""
        if not any(daily_pattern):
            return [0, 1, 2, 3, 4]  # Будни

        # ДНИ С ВЫШЕ СРЕДНЕЙ АКТИВНОСТЬЮ
        mean = np.mean(daily_pattern)
        peaks = [i for i, count in enumerate(daily_pattern) if count > mean]

        return peaks if peaks else list(range(7))

    def _find_peak_weeks(self, weekly_pattern):
        """🗓️ Находит пиковые недели публикаций"""
        if not any(weekly_pattern):
            return [0, 1, 2, 3]

        mean = np.mean(weekly_pattern)
        peaks = [i for i, count in enumerate(weekly_pattern) if count > mean]

        return peaks if peaks else list(range(4))

    def _calculate_confidence(self, cycle_data):
        """🎯 Расчет уверенности в предсказании"""
        total_publications = cycle_data['total_publications']

        if total_publications > 100:
            return 0.9
        elif total_publications > 50:
            return 0.7
        elif total_publications > 20:
            return 0.5
        else:
            return 0.3

    def _get_next_search_time(self, peak_hours):
        """🕐 Рекомендует следующее время поиска"""
        current_hour = datetime.now().hour

        # ИЩЕМ СЛЕДУЮЩИЙ ПИКОВЫЙ ЧАС
        future_peaks = [h for h in peak_hours if h > current_hour]
        if future_peaks:
            return min(future_peaks)
        else:
            return min(peak_hours)  # Следующий день

    async def _get_default_prediction(self):
        """🔄 Предсказание по умолчанию"""
        return {
            'peak_hours': [9, 14, 19],
            'peak_days': list(range(5)),  # Будни
            'peak_weeks': list(range(4)),
            'confidence': 0.1,
            'next_recommended_search': 9,
            'total_analyzed_publications': 0
        }

    async def get_patterns(self):
        """📊 Возвращает все изученные паттерны"""
        return {
            'categories_analyzed': list(self.publication_cycles.keys()),
            'total_categories': len(self.publication_cycles),
            'category_details': {
                category: {
                    'total_publications': data['total_publications'],
                    'confidence': self._calculate_confidence(data),
                    'top_hours': self._find_peak_hours(data['hourly_pattern'])[:3]
                }
                for category, data in self.publication_cycles.items()
            }
        }

    async def get_model_info(self):
        """📊 Информация о модели для совместимости"""
        return await self.get_prediction_stats()

    async def initialize_model(self):
        """🚀 Инициализация модели публикаций"""
        try:
            # Можно добавить загрузку сохраненных паттернов
            await self.load_publication_patterns()
            logger.info("✅ Модель публикаций инициализирована")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации модели публикаций: {e}")
            return True

    async def load_publication_patterns(self):
        """📥 Загрузка сохраненных паттернов публикаций"""
        try:
            # Здесь можно добавить загрузку из файла/БД
            pass
        except Exception as e:
            logger.debug(f"📥 Нет сохраненных паттернов публикаций: {e}")