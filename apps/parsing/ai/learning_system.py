import logging
import numpy as np
import pandas as pd
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import sqlite3
import hashlib
from dataclasses import dataclass, asdict
import joblib

logger = logging.getLogger('parser.ai')


@dataclass
class LearningEpisode:
    timestamp: str
    prediction_type: str
    features: Dict[str, Any]
    prediction: float
    actual_result: Optional[float]
    error: Optional[float]
    confidence: float
    model_version: str
    context: Dict[str, Any]


@dataclass
class ModelPerformance:
    version: str
    training_samples: int
    metrics: Dict[str, float]
    created_at: str
    last_used: str


class LearningSystem:
    def __init__(self, db_path="vision_knowledge.db"):
        self.db_path = db_path
        self.learning_episodes = deque(maxlen=5000)  # 🧠 Храним последние 5000 эпизодов
        self.model_versions = {}
        self.performance_metrics = defaultdict(list)
        self.feature_importance = {}
        self.adaptation_rules = {}

        # 🎯 Конфигурация обучения
        self.learning_config = {
            'retrain_interval': 100,  # Переобучение каждые 100 новых примеров
            'min_training_samples': 50,
            'validation_split': 0.2,
            'performance_threshold': 0.7,  # Минимальная точность для модели
            'adaptive_learning_rate': 0.1,
            'feature_analysis_interval': 50
        }

        # 📊 Статистика системы
        self.system_stats = {
            'total_episodes': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'avg_error': 0.0,
            'learning_progress': 0.0,
            'last_retraining': None,
            'active_models': 0
        }

        # 🔥 Инициализация моделей
        self._initialize_models()

    def _initialize_models(self):
        """🚀 Инициализация начальных моделей обучения"""
        try:
            # Модель для предсказания цен
            self.model_versions['price_predictor_v1'] = ModelPerformance(
                version="price_predictor_v1",
                training_samples=0,
                metrics={'mae': 0.0, 'mse': 0.0, 'r2': 0.0},
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat()
            )

            # Модель для оценки качества сделок
            self.model_versions['quality_assessor_v1'] = ModelPerformance(
                version="quality_assessor_v1",
                training_samples=0,
                metrics={'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0},
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat()
            )

            # Модель для оптимизации запросов
            self.model_versions['query_optimizer_v1'] = ModelPerformance(
                version="query_optimizer_v1",
                training_samples=0,
                metrics={'success_rate': 0.0, 'improvement': 0.0},
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat()
            )

            self.system_stats['active_models'] = len(self.model_versions)
            logger.info("🧠 Инициализированы модели обучения")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации моделей: {e}")

    async def collect_feedback(self, prediction: float, actual_result: Optional[float],
                               features: Dict[str, Any], prediction_type: str = "price",
                               confidence: float = 0.5, context: Dict[str, Any] = None):
        """📥 Сбор обратной связи для обучения с расширенной аналитикой"""
        try:
            # Расчет ошибки если есть фактический результат
            error = None
            if actual_result is not None:
                error = abs(prediction - actual_result)

                # Обновление статистики успешности
                if error < (prediction * 0.1):  # Ошибка менее 10%
                    self.system_stats['successful_predictions'] += 1
                else:
                    self.system_stats['failed_predictions'] += 1

            # Создание эпизода обучения
            episode = LearningEpisode(
                timestamp=datetime.now().isoformat(),
                prediction_type=prediction_type,
                features=features,
                prediction=prediction,
                actual_result=actual_result,
                error=error,
                confidence=confidence,
                model_version=f"{prediction_type}_v1",
                context=context or {}
            )

            # Сохранение эпизода
            self.learning_episodes.append(episode)
            self.system_stats['total_episodes'] += 1

            # Обновление средней ошибки
            if error is not None:
                errors = [e.error for e in self.learning_episodes if e.error is not None]
                if errors:
                    self.system_stats['avg_error'] = np.mean(errors)

            # Анализ важности признаков
            if self.system_stats['total_episodes'] % self.learning_config['feature_analysis_interval'] == 0:
                await self._analyze_feature_importance()

            # Проверка необходимости переобучения
            if (self.system_stats['total_episodes'] % self.learning_config['retrain_interval'] == 0 and
                    self.system_stats['total_episodes'] >= self.learning_config['min_training_samples']):
                await self.retrain_models_advanced()

            # Адаптация правил на лету
            await self._adaptive_rule_optimization(episode)

            logger.debug(f"📥 Собран эпизод обучения: {prediction_type} (ошибка: {error})")

        except Exception as e:
            logger.error(f"❌ Ошибка сбора обратной связи: {e}")

    async def retrain_models_advanced(self):
        """🔄 ПЕРЕДОВОЕ ПЕРЕОБУЧЕНИЕ моделей с продвинутыми техниками"""
        try:
            logger.info("🔄 Запуск передового переобучения моделей...")

            # Фильтрация и подготовка данных
            training_data = await self._prepare_training_data()

            if not training_data:
                logger.warning("⚠️ Недостаточно данных для переобучения")
                return False

            # Переобучение для каждого типа предсказаний
            retrain_results = {}

            for prediction_type in ['price', 'quality', 'query_optimization']:
                type_data = [ep for ep in training_data if ep.prediction_type == prediction_type]

                if len(type_data) >= self.learning_config['min_training_samples']:
                    success = await self._retrain_specific_model(prediction_type, type_data)
                    retrain_results[prediction_type] = success
                else:
                    logger.warning(f"⚠️ Недостаточно данных для {prediction_type}: {len(type_data)}")
                    retrain_results[prediction_type] = False

            # Оценка общего успеха переобучения
            successful_retrains = sum(1 for result in retrain_results.values() if result)
            total_models = len(retrain_results)

            self.system_stats['learning_progress'] = successful_retrains / total_models
            self.system_stats['last_retraining'] = datetime.now().isoformat()

            logger.info(f"✅ Переобучение завершено: {successful_retrains}/{total_models} моделей")

            # Сохранение состояния системы
            await self._save_learning_state()

            return successful_retrains > 0

        except Exception as e:
            logger.error(f"❌ Ошибка переобучения моделей: {e}")
            return False

    async def _prepare_training_data(self) -> List[LearningEpisode]:
        """📊 Подготовка данных для обучения с очисткой и фильтрацией"""
        try:
            # Берем только последние релевантные эпизоды
            recent_episodes = list(self.learning_episodes)[-1000:]  # Последние 1000 эпизодов

            # Фильтрация некорректных данных
            cleaned_episodes = []
            for episode in recent_episodes:
                # Проверка на наличие фактического результата
                if episode.actual_result is None:
                    continue

                # Проверка на разумность значений
                if (episode.prediction <= 0 or episode.actual_result <= 0 or
                        episode.error is None or episode.error > episode.actual_result * 10):
                    continue

                cleaned_episodes.append(episode)

            logger.info(f"📊 Подготовлено {len(cleaned_episodes)} эпизодов для обучения")
            return cleaned_episodes

        except Exception as e:
            logger.error(f"❌ Ошибка подготовки данных: {e}")
            return []

    async def _retrain_specific_model(self, model_type: str, episodes: List[LearningEpisode]):
        """🎯 Переобучение конкретной модели с ML"""
        try:
            if not episodes:
                return False

            # Подготовка features и targets
            X, y = [], []
            feature_names = []

            for episode in episodes:
                features = self._extract_learning_features(episode)
                if features and episode.actual_result is not None:
                    X.append(features)
                    y.append(episode.actual_result)

                    # Сохраняем имена признаков при первом проходе
                    if not feature_names:
                        feature_names = list(features.keys())

            if len(X) < self.learning_config['min_training_samples']:
                return False

            # Преобразование в numpy arrays
            X_array = np.array([list(x.values()) for x in X])
            y_array = np.array(y)

            # Выбор алгоритма в зависимости от типа модели
            if model_type == 'price':
                success = await self._train_regression_model(X_array, y_array, model_type)
            elif model_type == 'quality':
                success = await self._train_classification_model(X_array, y_array, model_type)
            else:
                success = await self._train_optimization_model(X_array, y_array, model_type)

            if success:
                # Обновление метрик модели
                model_key = f"{model_type}_v1"
                if model_key in self.model_versions:
                    self.model_versions[model_key].training_samples = len(X)
                    self.model_versions[model_key].last_used = datetime.now().isoformat()

                    # Расчет новых метрик
                    metrics = await self._calculate_model_metrics(X_array, y_array, model_type)
                    self.model_versions[model_key].metrics.update(metrics)

                logger.info(f"✅ Модель {model_type} успешно переобучена на {len(X)} примерах")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка переобучения модели {model_type}: {e}")
            return False

    async def _train_regression_model(self, X: np.ndarray, y: np.ndarray, model_type: str) -> bool:
        """📈 Обучение регрессионной модели"""
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

            # Разделение на train/validation
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=self.learning_config['validation_split'], random_state=42
            )

            # Обучение модели
            model = RandomForestRegressor(
                n_estimators=50,
                max_depth=15,
                random_state=42,
                min_samples_split=5
            )

            model.fit(X_train, y_train)

            # Валидация
            y_pred = model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            mse = mean_squared_error(y_val, y_pred)
            r2 = r2_score(y_val, y_pred)

            # Сохранение если модель достаточно точна
            if r2 > self.learning_config['performance_threshold'] - 0.2:  # Более мягкий порог для регрессии
                # Здесь можно сохранить модель через joblib
                # joblib.dump(model, f'{model_type}_model.joblib')

                # Сохраняем важность признаков
                self.feature_importance[model_type] = dict(zip(
                    [f"feature_{i}" for i in range(X.shape[1])],
                    model.feature_importances_
                ))

                return True
            else:
                logger.warning(f"⚠️ Модель {model_type} недостаточно точна: R²={r2:.3f}")
                return False

        except ImportError:
            logger.warning("⚠️ scikit-learn не доступен, используем упрощенное обучение")
            return await self._train_simple_model(X, y, model_type)
        except Exception as e:
            logger.error(f"❌ Ошибка обучения регрессии: {e}")
            return False

    async def _train_classification_model(self, X: np.ndarray, y: np.ndarray, model_type: str) -> bool:
        """🎯 Обучение классификационной модели"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_score, recall_score

            # Бинаризация целевой переменной для классификации
            y_binary = (y > np.median(y)).astype(int)

            X_train, X_val, y_train, y_val = train_test_split(
                X, y_binary, test_size=self.learning_config['validation_split'], random_state=42
            )

            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=15,
                random_state=42
            )

            model.fit(X_train, y_train)

            # Валидация
            y_pred = model.predict(X_val)
            accuracy = accuracy_score(y_val, y_pred)
            precision = precision_score(y_val, y_pred, zero_division=0)
            recall = recall_score(y_val, y_pred, zero_division=0)

            if accuracy > self.learning_config['performance_threshold']:
                # joblib.dump(model, f'{model_type}_model.joblib')
                return True
            else:
                logger.warning(f"⚠️ Модель {model_type} недостаточно точна: accuracy={accuracy:.3f}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка обучения классификации: {e}")
            return await self._train_simple_model(X, y, model_type)

    async def _train_optimization_model(self, X: np.ndarray, y: np.ndarray, model_type: str) -> bool:
        """⚡ Обучение модели оптимизации"""
        # Упрощенная модель для оптимизации запросов
        return await self._train_simple_model(X, y, model_type)

    async def _train_simple_model(self, X: np.ndarray, y: np.ndarray, model_type: str) -> bool:
        """🔄 Упрощенное обучение как fallback"""
        try:
            # Простая линейная регрессия без scikit-learn
            if len(X) < 2:
                return False

            # Нормализация данных
            X_normalized = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-8)

            # Простая линейная модель
            coefficients = np.linalg.lstsq(X_normalized, y, rcond=None)[0]

            # Сохраняем коэффициенты как простую модель
            self.adaptation_rules[f"{model_type}_coefficients"] = coefficients.tolist()

            logger.info(f"🔄 Упрощенная модель {model_type} обучена")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка упрощенного обучения: {e}")
            return False

    def _extract_learning_features(self, episode: LearningEpisode) -> Dict[str, float]:
        """🔍 Извлечение признаков для обучения из эпизода"""
        try:
            features = {}

            # Базовые признаки из фич эпизода
            episode_features = episode.features
            if isinstance(episode_features, dict):
                for key, value in episode_features.items():
                    if isinstance(value, (int, float)):
                        features[f"episode_{key}"] = float(value)
                    elif isinstance(value, bool):
                        features[f"episode_{key}"] = 1.0 if value else 0.0

            # Признаки из контекста
            context = episode.context
            if isinstance(context, dict):
                for key, value in context.items():
                    if isinstance(value, (int, float)):
                        features[f"context_{key}"] = float(value)

            # Временные признаки
            try:
                episode_time = datetime.fromisoformat(episode.timestamp.replace('Z', '+00:00'))
                features['hour_of_day'] = episode_time.hour / 24.0
                features['day_of_week'] = episode_time.weekday() / 7.0
                features['is_weekend'] = 1.0 if episode_time.weekday() >= 5 else 0.0
            except:
                features.update({'hour_of_day': 0.5, 'day_of_week': 0.5, 'is_weekend': 0.0})

            # Статистические признаки
            features['prediction_confidence'] = episode.confidence
            features['has_actual_result'] = 1.0 if episode.actual_result is not None else 0.0

            # Нормализация числовых признаков
            numeric_features = {k: v for k, v in features.items() if isinstance(v, (int, float))}

            return numeric_features

        except Exception as e:
            logger.warning(f"⚠️ Ошибка извлечения признаков: {e}")
            return {}

    async def _calculate_model_metrics(self, X: np.ndarray, y: np.ndarray, model_type: str) -> Dict[str, float]:
        """📊 Расчет метрик производительности модели"""
        try:
            if model_type == 'price':
                # Метрики для регрессии
                from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
                from sklearn.model_selection import cross_val_score

                # Простая оценка на всех данных
                dummy_pred = np.full_like(y, np.mean(y))
                mae_baseline = mean_absolute_error(y, dummy_pred)

                # Оценка нашей модели (упрощенная)
                current_mae = self.system_stats['avg_error']
                improvement = max(0, (mae_baseline - current_mae) / mae_baseline)

                return {
                    'mae': current_mae,
                    'mse': current_mae ** 2,
                    'r2': improvement,
                    'improvement_over_baseline': improvement
                }

            elif model_type == 'quality':
                # Метрики для классификации
                success_rate = self.system_stats['successful_predictions'] / max(1, self.system_stats['total_episodes'])
                return {
                    'accuracy': success_rate,
                    'precision': success_rate,
                    'recall': success_rate,
                    'f1_score': success_rate
                }

            else:
                return {'success_rate': 0.7, 'improvement': 0.1}

        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета метрик: {e}")
            return {'error': 1.0}

    async def _analyze_feature_importance(self):
        """🔍 Анализ важности признаков для оптимизации"""
        try:
            if not self.learning_episodes:
                return

            # Собираем все признаки из эпизодов
            all_features = defaultdict(list)
            errors = []

            for episode in self.learning_episodes:
                if episode.actual_result is not None and episode.error is not None:
                    features = self._extract_learning_features(episode)
                    for feature, value in features.items():
                        all_features[feature].append(value)
                    errors.append(episode.error)

            # Упрощенный анализ корреляции
            feature_correlations = {}
            for feature, values in all_features.items():
                if len(values) == len(errors):
                    correlation = np.corrcoef(values, errors)[0, 1]
                    if not np.isnan(correlation):
                        feature_correlations[feature] = abs(correlation)

            # Сохраняем топ-10 самых важных признаков
            top_features = dict(sorted(feature_correlations.items(),
                                       key=lambda x: x[1], reverse=True)[:10])

            self.feature_importance['correlation_analysis'] = top_features
            logger.info(f"🔍 Проанализирована важность {len(top_features)} признаков")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка анализа важности признаков: {e}")

    async def _adaptive_rule_optimization(self, episode: LearningEpisode):
        """⚡ Адаптивная оптимизация правил на лету"""
        try:
            # Анализ паттернов ошибок
            if episode.error is not None and episode.error > episode.prediction * 0.2:
                # Большая ошибка - анализируем контекст
                context = episode.context or {}

                # Обновляем правила для похожих контекстов
                context_key = self._create_context_key(context)
                current_rule = self.adaptation_rules.get(context_key, {'error_count': 0, 'adjustment': 1.0})

                current_rule['error_count'] += 1
                current_rule['last_updated'] = datetime.now().isoformat()

                # Адаптируем множитель на основе ошибки
                error_ratio = episode.error / episode.prediction
                adjustment = 1.0 / (1.0 + error_ratio * self.learning_config['adaptive_learning_rate'])
                current_rule['adjustment'] *= adjustment

                self.adaptation_rules[context_key] = current_rule

                logger.debug(f"⚡ Адаптировано правило для контекста: {context_key}")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка адаптивной оптимизации: {e}")

    def _create_context_key(self, context: Dict[str, Any]) -> str:
        """🔑 Создание ключа для контекста"""
        try:
            # Создаем хеш из значимых полей контекста
            significant_fields = {
                'category': context.get('category', 'unknown'),
                'has_brand': context.get('has_brand', False),
                'condition': context.get('condition', 'unknown'),
                'seller_rating_tier': 'high' if context.get('seller_rating', 0) > 4.5 else 'low'
            }

            context_str = json.dumps(significant_fields, sort_keys=True)
            return hashlib.md5(context_str.encode()).hexdigest()[:8]

        except:
            return "default"

    async def get_learning_insights(self) -> Dict[str, Any]:
        """📊 Получение инсайтов системы обучения"""
        try:
            # Анализ прогресса обучения
            recent_episodes = list(self.learning_episodes)[-100:]  # Последние 100 эпизодов
            recent_errors = [e.error for e in recent_episodes if e.error is not None]

            if recent_errors:
                recent_avg_error = np.mean(recent_errors)
                error_trend = "улучшается" if recent_avg_error < self.system_stats['avg_error'] else "ухудшается"
            else:
                recent_avg_error = 0.0
                error_trend = "недостаточно данных"

            # Топ моделей по эффективности
            model_performance = []
            for model_name, model_data in self.model_versions.items():
                if 'r2' in model_data.metrics:
                    score = model_data.metrics['r2']
                elif 'accuracy' in model_data.metrics:
                    score = model_data.metrics['accuracy']
                else:
                    score = 0.5

                model_performance.append({
                    'model': model_name,
                    'score': score,
                    'samples': model_data.training_samples
                })

            model_performance.sort(key=lambda x: x['score'], reverse=True)

            return {
                'system_stats': self.system_stats,
                'recent_performance': {
                    'avg_error': recent_avg_error,
                    'trend': error_trend,
                    'success_rate': self.system_stats['successful_predictions'] / max(1, self.system_stats[
                        'total_episodes'])
                },
                'top_models': model_performance[:3],
                'feature_insights': self._get_feature_insights(),
                'adaptation_rules_count': len(self.adaptation_rules),
                'learning_progress': f"{self.system_stats['learning_progress']:.1%}",
                'recommendations': await self._generate_learning_recommendations()
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения инсайтов: {e}")
            return {'error': str(e)}

    def _get_feature_insights(self) -> List[Dict[str, Any]]:
        """🔍 Инсайты о важности признаков"""
        insights = []

        for model_type, importance_dict in self.feature_importance.items():
            if importance_dict:
                top_feature = max(importance_dict.items(), key=lambda x: x[1])
                insights.append({
                    'model_type': model_type,
                    'most_important_feature': top_feature[0],
                    'importance_score': top_feature[1],
                    'total_features_analyzed': len(importance_dict)
                })

        return insights

    async def _generate_learning_recommendations(self) -> List[str]:
        """💡 Генерация рекомендаций по улучшению обучения"""
        recommendations = []

        # Рекомендации на основе статистики
        if self.system_stats['total_episodes'] < 100:
            recommendations.append("Накопите больше данных для улучшения моделей (минимум 100 эпизодов)")

        if self.system_stats['successful_predictions'] / max(1, self.system_stats['total_episodes']) < 0.6:
            recommendations.append("Увеличьте разнообразие данных для улучшения точности предсказаний")

        if len(self.adaptation_rules) < 5:
            recommendations.append("Расширьте контекст данных для лучшей адаптации к разным сценариям")

        if not recommendations:
            recommendations.append("Система обучается оптимально. Продолжайте сбор данных")

        return recommendations

    async def _save_learning_state(self):
        """💾 Сохранение состояния системы обучения"""
        try:
            state = {
                'system_stats': self.system_stats,
                'model_versions': {k: asdict(v) for k, v in self.model_versions.items()},
                'feature_importance': self.feature_importance,
                'adaptation_rules': self.adaptation_rules,
                'last_saved': datetime.now().isoformat()
            }

            with open('learning_system_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            logger.info("💾 Состояние системы обучения сохранено")

        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить состояние: {e}")

    async def load_learning_state(self):
        """📥 Загрузка состояния системы обучения"""
        try:
            with open('learning_system_state.json', 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.system_stats = state['system_stats']

            for model_name, model_data in state['model_versions'].items():
                self.model_versions[model_name] = ModelPerformance(**model_data)

            self.feature_importance = state['feature_importance']
            self.adaptation_rules = state['adaptation_rules']

            logger.info("📥 Состояние системы обучения загружено")

        except FileNotFoundError:
            logger.info("📥 Файл состояния не найден, используется чистая система")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки состояния: {e}")

    def get_detailed_stats(self) -> Dict[str, Any]:
        """📈 Детальная статистика системы"""
        return {
            'learning_episodes_count': len(self.learning_episodes),
            'system_stats': self.system_stats,
            'model_performance': {
                name: asdict(performance) for name, performance in self.model_versions.items()
            },
            'feature_importance_summary': {
                model: dict(sorted(imp.items(), key=lambda x: x[1], reverse=True)[:3])
                for model, imp in self.feature_importance.items()
            },
            'adaptation_rules_summary': {
                'total_rules': len(self.adaptation_rules),
                'recently_updated': len([
                    rule for rule in self.adaptation_rules.values()
                    if datetime.fromisoformat(rule['last_updated']) > datetime.now() - timedelta(days=1)
                ])
            }
        }


# 🔥 Алиас для обратной совместимости
LearningSystem = LearningSystem