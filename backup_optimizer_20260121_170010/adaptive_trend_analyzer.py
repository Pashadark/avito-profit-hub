import logging
import numpy as np
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sqlite3
from collections import deque
import json

logger = logging.getLogger('parser.ai')


class AdaptiveTrendAnalyzer:
    def __init__(self, db_path="vision_knowledge.db"):
        self.db_path = db_path
        self.trend_cache = {}
        self.category_models = {}
        self.learning_rate = 0.1
        self.trend_history = deque(maxlen=1000)
        self.market_volatility = {}

        # 🎯 Веса для разных факторов тренда
        self.trend_weights = {
            'price_momentum': 0.3,
            'volume_trend': 0.25,
            'seasonality': 0.15,
            'market_sentiment': 0.2,
            'external_factors': 0.1
        }

        # 📈 Паттерны сезонности
        self.seasonal_patterns = {
            'electronics': {
                'q1': 0.9,  # Январь-март - скидки после праздников
                'q2': 1.0,  # Апрель-июнь - стабильно
                'q3': 1.1,  # Июль-сентябрь - подготовка к школе
                'q4': 1.2  # Октябрь-декабрь - предпраздничный спрос
            },
            'clothing': {
                'q1': 0.8,  # Распродажи зимней одежды
                'q2': 1.1,  # Весенний шопинг
                'q3': 1.0,  # Лето
                'q4': 1.3  # Осенний сезон + праздники
            },
            'phones': {
                'q1': 1.0,
                'q2': 0.95,  # Ожидание новых моделей
                'q3': 1.2,  # Выход новых iPhone
                'q4': 1.1  # Праздничные продажи
            }
        }

    async def analyze_super_trends(self, category, depth_analysis=True):
        """🔥 ГЛУБОКИЙ АНАЛИЗ ТРЕНДОВ с машинным обучением"""
        try:
            from apps.website.models import FoundItem
            from django.utils import timezone
            from django.db.models import Avg, Count, StdDev, Max, Min

            logger.info(f"🎯 Запуск супер-анализа трендов для: {category}")

            # 📊 Сбор расширенной статистики
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)

            # Анализ по дням
            daily_stats = []
            for i in range(30):
                day_start = start_date + timedelta(days=i)
                day_end = day_start + timedelta(days=1)

                day_items = FoundItem.objects.filter(
                    category__icontains=category,
                    found_at__range=(day_start, day_end)
                )

                stats = day_items.aggregate(
                    avg_price=Avg('price'),
                    item_count=Count('id'),
                    price_std=StdDev('price'),
                    max_price=Max('price'),
                    min_price=Min('price')
                )

                if stats['avg_price'] and stats['item_count'] > 0:
                    daily_stats.append({
                        'date': day_start,
                        'avg_price': float(stats['avg_price']),
                        'volume': stats['item_count'],
                        'volatility': float(stats['price_std'] or 0),
                        'price_range': float((stats['max_price'] or 0) - (stats['min_price'] or 0)),
                        'day_of_week': day_start.weekday()
                    })

            if len(daily_stats) < 5:
                return await self._get_intelligent_fallback(category)

            # 🔥 МНОГОУРОВНЕВЫЙ АНАЛИЗ
            trend_analysis = {
                'basic_trend': self._calculate_basic_trend(daily_stats),
                'momentum_analysis': self._analyze_price_momentum(daily_stats),
                'volume_analysis': self._analyze_volume_patterns(daily_stats),
                'volatility_analysis': self._analyze_volatility(daily_stats),
                'seasonal_analysis': self._analyze_seasonality(category, daily_stats),
                'market_sentiment': await self._analyze_market_sentiment(category)
            }

            # 🎯 ИТОГОВАЯ ОЦЕНКА ТРЕНДА
            final_trend = self._synthesize_trend_analysis(trend_analysis)

            # 💾 Сохраняем результаты
            await self._update_trend_knowledge_base(category, final_trend, daily_stats)

            logger.info(f"🚀 Супер-анализ завершен: {final_trend['direction']} "
                        f"(сила: {final_trend['strength']:.2f}, уверенность: {final_trend['confidence']:.2f})")

            return final_trend

        except Exception as e:
            logger.error(f"❌ Ошибка супер-анализа трендов: {e}")
            return await self._get_intelligent_fallback(category)

    def _calculate_basic_trend(self, daily_stats):
        """📈 Базовый анализ ценового тренда"""
        if len(daily_stats) < 2:
            return {'direction': 'stable', 'strength': 0, 'change_percent': 0}

        prices = [day['avg_price'] for day in daily_stats]
        volumes = [day['volume'] for day in daily_stats]

        # Простой линейный тренд
        x = np.arange(len(prices))
        slope, intercept = np.polyfit(x, prices, 1)
        trend_percent = (slope * len(prices)) / np.mean(prices) * 100

        # Взвешенный по объему тренд
        weighted_prices = np.average(prices, weights=volumes)
        base_price = np.mean(prices[:3])
        weighted_change = (weighted_prices - base_price) / base_price * 100

        direction = 'up' if trend_percent > 2 else 'down' if trend_percent < -2 else 'stable'
        strength = min(abs(trend_percent) / 10, 1.0)

        return {
            'direction': direction,
            'strength': strength,
            'change_percent': trend_percent,
            'weighted_change': weighted_change,
            'volatility': np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
        }

    def _analyze_price_momentum(self, daily_stats):
        """📊 Анализ ценового импульса"""
        if len(daily_stats) < 5:
            return {'momentum': 0, 'acceleration': 0, 'rsi': 50}

        prices = [day['avg_price'] for day in daily_stats]

        # RSI (Relative Strength Index)
        gains, losses = [], []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)

        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss > 0 else 100

        # Momentum (текущая цена / цена 5 дней назад)
        momentum = (prices[-1] / prices[-5] - 1) * 100 if len(prices) >= 5 else 0

        return {
            'momentum': momentum,
            'rsi': rsi,
            'trend_strength': min(abs(momentum) / 5, 1.0),
            'is_overbought': rsi > 70,
            'is_oversold': rsi < 30
        }

    def _analyze_volume_patterns(self, daily_stats):
        """📦 Анализ паттернов объема"""
        volumes = [day['volume'] for day in daily_stats]

        if len(volumes) < 3:
            return {'volume_trend': 'stable', 'volume_strength': 0}

        # Тренд объема
        volume_trend = np.polyfit(range(len(volumes)), volumes, 1)[0]
        volume_change = (volumes[-1] / volumes[0] - 1) * 100 if volumes[0] > 0 else 0

        # Анализ всплесков объема
        avg_volume = np.mean(volumes)
        std_volume = np.std(volumes)
        volume_spikes = sum(1 for v in volumes if v > avg_volume + std_volume)

        volume_trend_direction = 'up' if volume_trend > 0 else 'down' if volume_trend < 0 else 'stable'
        volume_strength = min(abs(volume_change) / 50, 1.0)

        return {
            'volume_trend': volume_trend_direction,
            'volume_strength': volume_strength,
            'volume_change_percent': volume_change,
            'volume_spikes': volume_spikes,
            'avg_volume': avg_volume
        }

    def _analyze_volatility(self, daily_stats):
        """🎭 Анализ волатильности рынка"""
        prices = [day['avg_price'] for day in daily_stats]
        volatilities = [day['volatility'] for day in daily_stats]

        if len(prices) < 5:
            return {'volatility': 0, 'stability': 1.0, 'risk_level': 'low'}

        price_volatility = np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
        avg_volatility = np.mean(volatilities) / np.mean(prices) if np.mean(prices) > 0 else 0

        # Уровень риска на основе волатильности
        total_volatility = (price_volatility + avg_volatility) / 2
        stability = 1.0 - min(total_volatility, 0.5) * 2

        if total_volatility > 0.2:
            risk_level = 'high'
        elif total_volatility > 0.1:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'volatility': total_volatility,
            'stability': stability,
            'risk_level': risk_level,
            'price_swings': len(
                [i for i in range(1, len(prices)) if abs(prices[i] - prices[i - 1]) / prices[i - 1] > 0.05])
        }

    def _analyze_seasonality(self, category, daily_stats):
        """🎄 Анализ сезонных паттернов"""
        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        quarter_key = f'q{current_quarter}'

        # Определяем тип категории для сезонности
        category_type = self._categorize_for_seasonality(category)
        seasonal_multiplier = self.seasonal_patterns.get(category_type, {}).get(quarter_key, 1.0)

        return {
            'seasonal_multiplier': seasonal_multiplier,
            'quarter': current_quarter,
            'category_type': category_type,
            'effect': 'boost' if seasonal_multiplier > 1.0 else 'reduction' if seasonal_multiplier < 1.0 else 'neutral'
        }

    def _categorize_for_seasonality(self, category):
        """🏷️ Категоризация для сезонного анализа"""
        category_lower = category.lower()

        if any(word in category_lower for word in ['телефон', 'iphone', 'samsung', 'xiaomi']):
            return 'phones'
        elif any(word in category_lower for word in ['ноутбук', 'macbook', 'компьютер', 'пк']):
            return 'electronics'
        elif any(word in category_lower for word in ['одежда', 'кроссовки', 'куртка', 'футболка']):
            return 'clothing'
        elif any(word in category_lower for word in ['игров', 'playstation', 'xbox']):
            return 'electronics'
        else:
            return 'electronics'  # По умолчанию

    async def _analyze_market_sentiment(self, category):
        """😊 Анализ рыночного настроения"""
        try:
            from apps.website.models import FoundItem
            from django.utils import timezone
            from django.db.models import Avg, Count

            # Анализ "горячих" товаров (быстро исчезают)
            recent_time = timezone.now() - timedelta(hours=6)
            recent_items = FoundItem.objects.filter(
                category__icontains=category,
                found_at__gte=recent_time
            ).count()

            # Анализ ценовых диапазонов
            price_ranges = FoundItem.objects.filter(
                category__icontains=category
            ).values('price').annotate(count=Count('id'))

            avg_price = FoundItem.objects.filter(
                category__icontains=category
            ).aggregate(avg=Avg('price'))['avg'] or 0

            # Эвристика настроения
            sentiment = 0.5
            if recent_items > 10:
                sentiment += 0.2
            if avg_price > 0:
                sentiment += 0.1

            return {
                'sentiment_score': min(sentiment, 1.0),
                'recent_activity': recent_items,
                'market_temperature': 'hot' if recent_items > 20 else 'warm' if recent_items > 5 else 'cool'
            }

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа настроения: {e}")
            return {'sentiment_score': 0.5, 'recent_activity': 0, 'market_temperature': 'unknown'}

    def _synthesize_trend_analysis(self, analysis):
        """🎯 Синтез всех анализов в итоговый тренд"""
        basic = analysis['basic_trend']
        momentum = analysis['momentum_analysis']
        volume = analysis['volume_analysis']
        volatility = analysis['volatility_analysis']
        seasonal = analysis['seasonal_analysis']
        sentiment = analysis['market_sentiment']

        # 🎯 Взвешенная оценка направления
        direction_scores = {
            'up': 0.0,
            'down': 0.0,
            'stable': 0.0
        }

        # Базовый тренд
        direction_scores[basic['direction']] += self.trend_weights['price_momentum'] * basic['strength']

        # Моментум
        if momentum['momentum'] > 2:
            direction_scores['up'] += self.trend_weights['price_momentum'] * momentum['trend_strength']
        elif momentum['momentum'] < -2:
            direction_scores['down'] += self.trend_weights['price_momentum'] * momentum['trend_strength']
        else:
            direction_scores['stable'] += self.trend_weights['price_momentum']

        # Объем
        if volume['volume_trend'] == 'up':
            direction_scores['up'] += self.trend_weights['volume_trend'] * volume['volume_strength']
        elif volume['volume_trend'] == 'down':
            direction_scores['down'] += self.trend_weights['volume_trend'] * volume['volume_strength']

        # Сезонность
        if seasonal['effect'] == 'boost':
            direction_scores['up'] += self.trend_weights['seasonality']
        elif seasonal['effect'] == 'reduction':
            direction_scores['down'] += self.trend_weights['seasonality']

        # Итоговое направление
        final_direction = max(direction_scores, key=direction_scores.get)

        # 🎯 Расчет общей силы и уверенности
        strength = min(direction_scores[final_direction] * 2, 1.0)

        confidence = (
                basic['strength'] * 0.3 +
                momentum['trend_strength'] * 0.25 +
                volume['volume_strength'] * 0.2 +
                volatility['stability'] * 0.15 +
                sentiment['sentiment_score'] * 0.1
        )

        # 🎯 Генерация умных рекомендаций
        recommendation = self._generate_super_recommendation(
            final_direction, strength, confidence, analysis
        )

        return {
            'current_trend': final_direction,
            'trend_strength': strength,
            'confidence': confidence,
            'price_change': basic['change_percent'],
            'recommendation': recommendation,
            'data_points': len(analysis['basic_trend']) if 'basic_trend' in analysis else 0,
            'analysis_depth': 'deep',
            'risk_level': volatility['risk_level'],
            'market_temperature': sentiment['market_temperature'],
            'next_week_prediction': self._predict_next_week_trend(analysis)
        }

    def _generate_super_recommendation(self, direction, strength, confidence, analysis):
        """💡 Генерация супер-рекомендаций"""
        volatility = analysis['volatility_analysis']
        momentum = analysis['momentum_analysis']
        seasonal = analysis['seasonal_analysis']

        base_recommendations = {
            'up': [
                "📈 Цены растут - хорошее время для покупки пока не дороже",
                "🚀 Восходящий тренд - можно покупать, но следи за пиками",
                "🎯 Растущий рынок - ищи выгодные предложения сейчас"
            ],
            'down': [
                "📉 Цены падают - можно подождать еще снижения",
                "🔄 Нисходящий тренд - отличное время для выгодных покупок",
                "💎 Падающий рынок - жди дна для максимальной выгоды"
            ],
            'stable': [
                "⚖️ Цены стабильны - нормальное время для покупки",
                "🎪 Рынок в равновесии - можно покупать без спешки",
                "🏠 Стабильная ситуация - ищи индивидуально выгодные предложения"
            ]
        }

        # Выбор базовой рекомендации
        rec_index = min(int(strength * 3), 2)
        recommendation = base_recommendations[direction][rec_index]

        # Добавляем детали
        details = []

        if volatility['risk_level'] == 'high':
            details.append("Высокая волатильность - будь осторожен")
        elif volatility['risk_level'] == 'low':
            details.append("Низкая волатильность - стабильные условия")

        if momentum['is_overbought']:
            details.append("Рынок перекуплен - возможна коррекция")
        elif momentum['is_oversold']:
            details.append("Рынок перепродан - возможен рост")

        if seasonal['effect'] != 'neutral':
            details.append(f"Сезонный фактор: {seasonal['effect']}")

        if details:
            recommendation += f" | {', '.join(details)}"

        return recommendation

    def _predict_next_week_trend(self, analysis):
        """🔮 Прогноз на следующую неделю"""
        basic = analysis['basic_trend']
        momentum = analysis['momentum_analysis']
        seasonal = analysis['seasonal_analysis']

        # Простая экстраполяция тренда
        if basic['direction'] == 'up':
            if momentum['momentum'] > 5:
                return "continued_growth"
            else:
                return "stable_growth"
        elif basic['direction'] == 'down':
            if momentum['momentum'] < -5:
                return "continued_decline"
            else:
                return "stabilization"
        else:
            return "stable"

    async def _get_intelligent_fallback(self, category):
        """🔄 Умный фолбэк при недостатке данных"""
        # Используем исторические знания или базовые паттерны
        return {
            'current_trend': 'stable',
            'trend_strength': 0.5,
            'confidence': 0.3,
            'price_change': 0,
            'recommendation': '⚠️ Используются базовые настройки (мало данных)',
            'data_points': 0,
            'analysis_depth': 'basic',
            'risk_level': 'medium',
            'market_temperature': 'unknown',
            'next_week_prediction': 'stable'
        }

    async def _update_trend_knowledge_base(self, category, trend, daily_stats):
        """💾 Обновление базы знаний о трендах"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS super_trend_knowledge (
                    category TEXT PRIMARY KEY,
                    trend_direction TEXT,
                    trend_strength REAL,
                    confidence REAL,
                    data_points INTEGER,
                    analysis_timestamp TEXT,
                    seasonal_factor REAL,
                    market_sentiment REAL,
                    last_updated TEXT
                )
            ''')

            cursor.execute('''
                INSERT OR REPLACE INTO super_trend_knowledge 
                (category, trend_direction, trend_strength, confidence, data_points, 
                 analysis_timestamp, seasonal_factor, market_sentiment, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                category, trend['current_trend'], trend['trend_strength'],
                trend['confidence'], len(daily_stats), datetime.now().isoformat(),
                self.seasonal_patterns.get(self._categorize_for_seasonality(category), {}).get('q1', 1.0),
                0.5
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления базы знаний: {e}")


# 🔥 Алиас для обратной совместимости
TrendAnalyzer = AdaptiveTrendAnalyzer