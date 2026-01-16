import os
import sys

# ========== НАСТРОЙКА DJANGO ДЛЯ БЕЗОПАСНОГО ИМПОРТА ==========
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

try:
    import django
    if not django.conf.settings.configured:
        django.setup()
except Exception as e:
    print(f"⚠️ Не удалось настроить Django: {e}")
# ==============================================================

import logging
import asyncio
import sqlite3
import os
import json
from datetime import datetime, timedelta
from collections import Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

logger = logging.getLogger(__name__)


class UserPointsSystem:
    """Система баллов для пользователей"""

    def __init__(self, db_path=None):
        self.db_path = db_path or self._find_vision_database()
        self._ensure_points_table()

    def _find_vision_database(self):
        """Находит базу данных vision_knowledge.db"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vision_knowledge.db'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vision_knowledge.db'),
            'vision_knowledge.db',
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"✅ Найдена база данных: {path}")
                return path

        logger.warning("⚠️ База данных vision_knowledge.db не найдена")
        return None

    def _ensure_points_table(self):
        """Создает таблицу для баллов если не существует"""
        if not self.db_path:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id INTEGER PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    feedback_count INTEGER DEFAULT 0,
                    descriptions_count INTEGER DEFAULT 0,
                    corrections_count INTEGER DEFAULT 0,
                    last_activity DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            logger.info("✅ Таблица баллов пользователей готова")

        except Exception as e:
            logger.error(f"❌ Ошибка создания таблицы баллов: {e}")

    async def add_points(self, user_id: int, points: int, reason: str):
        """Добавляет баллы пользователю"""
        if not self.db_path:
            return 0

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Получаем текущие баллы
            cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()

            current_points = result[0] if result else 0
            new_points = current_points + points

            # Обновляем или создаем запись
            if result:
                # Обновляем существующую запись
                if reason == 'feedback':
                    cursor.execute("""
                        UPDATE user_points 
                        SET points = ?, feedback_count = feedback_count + 1, last_activity = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    """, (new_points, user_id))
                elif reason == 'description':
                    cursor.execute("""
                        UPDATE user_points 
                        SET points = ?, descriptions_count = descriptions_count + 1, last_activity = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    """, (new_points, user_id))
                elif reason == 'correction':
                    cursor.execute("""
                        UPDATE user_points 
                        SET points = ?, corrections_count = corrections_count + 1, last_activity = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    """, (new_points, user_id))
                else:
                    cursor.execute("""
                        UPDATE user_points 
                        SET points = ?, last_activity = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    """, (new_points, user_id))
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO user_points (user_id, points, feedback_count, descriptions_count, corrections_count, last_activity)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, new_points,
                      1 if reason == 'feedback' else 0,
                      1 if reason == 'description' else 0,
                      1 if reason == 'correction' else 0))

            conn.commit()
            conn.close()

            logger.info(f"✅ Добавлено {points} баллов пользователю {user_id} за {reason}")
            return new_points

        except Exception as e:
            logger.error(f"❌ Ошибка добавления баллов: {e}")
            return 0

    async def get_user_stats(self, user_id: int):
        """Возвращает статистику пользователя"""
        if not self.db_path:
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT points, feedback_count, descriptions_count, corrections_count, last_activity
                FROM user_points WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'points': result[0],
                    'feedback_count': result[1],
                    'descriptions_count': result[2],
                    'corrections_count': result[3],
                    'last_activity': result[4],
                    'rank': self._calculate_rank(result[0])
                }
            else:
                return {
                    'points': 0,
                    'feedback_count': 0,
                    'descriptions_count': 0,
                    'corrections_count': 0,
                    'last_activity': None,
                    'rank': 'Новичок'
                }

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return None

    def _calculate_rank(self, points: int):
        """Рассчитывает ранг пользователя по баллам"""
        if points >= 1000:
            return "🎖️ Гуру ИИ"
        elif points >= 500:
            return "🏆 Эксперт"
        elif points >= 200:
            return "⭐ Профессионал"
        elif points >= 100:
            return "🔥 Активный помощник"
        elif points >= 50:
            return "🚀 Продвинутый"
        elif points >= 20:
            return "📚 Ученик"
        else:
            return "🎯 Новичок"

    async def get_leaderboard(self, limit=10):
        """Возвращает таблицу лидеров"""
        if not self.db_path:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, points, feedback_count, descriptions_count, corrections_count
                FROM user_points 
                ORDER BY points DESC 
                LIMIT ?
            """, (limit,))

            leaders = []
            for row in cursor.fetchall():
                leaders.append({
                    'user_id': row[0],
                    'points': row[1],
                    'feedback_count': row[2],
                    'descriptions_count': row[3],
                    'corrections_count': row[4],
                    'rank': self._calculate_rank(row[1])
                })

            conn.close()
            return leaders

        except Exception as e:
            logger.error(f"❌ Ошибка получения таблицы лидеров: {e}")
            return []


class VisionFeedbackAnalyzer:
    """Анализатор обратной связи для обучения компьютерного зрения"""

    def __init__(self):
        self.db_path = self._find_vision_database()
        self.knowledge_cache = {}

    def _find_vision_database(self):
        """Находит базу данных vision_knowledge.db"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vision_knowledge.db'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vision_knowledge.db'),
            'vision_knowledge.db',
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"✅ Найдена база знаний: {path}")
                return path

        logger.warning("⚠️ База знаний vision_knowledge.db не найдена")
        return None

    async def analyze_recent_feedback(self, days=7):
        """Анализирует последние фидбэки и извлекает паттерны"""
        if not self.db_path:
            return {"error": "База знаний не найдена"}

        try:
            category_patterns = await self._analyze_category_patterns(days)
            color_patterns = await self._analyze_color_patterns(days)
            material_patterns = await self._analyze_material_patterns(days)
            error_patterns = await self._analyze_error_patterns(days)

            update_results = await self._update_knowledge_base(
                category_patterns, color_patterns, material_patterns, error_patterns
            )

            return {
                "category_patterns": category_patterns,
                "color_patterns": color_patterns,
                "material_patterns": material_patterns,
                "error_patterns": error_patterns,
                "knowledge_updated": update_results,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Ошибка анализа фидбэка: {e}")
            return {"error": str(e)}

    async def _analyze_category_patterns(self, days):
        """Анализирует паттерны категорий из описаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT description FROM vision_feedback 
                WHERE feedback_type = 'manual_description' 
                AND created_at >= datetime('now', ?)
            """, (f'-{days} days',))

            descriptions = [row[0] for row in cursor.fetchall() if row[0]]

            category_keywords = {
                'электроника': ['телефон', 'iphone', 'android', 'ноутбук', 'планшет', 'наушники', 'камера'],
                'одежда': ['футболка', 'кофта', 'куртка', 'джинсы', 'платье', 'обувь'],
                'мебель': ['стол', 'стул', 'кровать', 'диван', 'шкаф', 'полка'],
                'авто': ['машина', 'автомобиль', 'запчасти', 'шины', 'аккумулятор'],
                'недвижимость': ['квартира', 'дом', 'комната', 'аренда', 'продажа'],
                'спорт': ['велосипед', 'лыжи', 'тренажер', 'мяч', 'форма']
            }

            category_counts = Counter()

            for desc in descriptions:
                desc_lower = desc.lower()
                for category, keywords in category_keywords.items():
                    if any(keyword in desc_lower for keyword in keywords):
                        category_counts[category] += 1

            conn.close()
            return dict(category_counts.most_common())

        except Exception as e:
            logger.error(f"❌ Ошибка анализа категорий: {e}")
            return {}

    async def _analyze_color_patterns(self, days):
        """Анализирует паттерны цветов из описаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT description FROM vision_feedback 
                WHERE feedback_type = 'manual_description' 
                AND created_at >= datetime('now', ?)
            """, (f'-{days} days',))

            descriptions = [row[0] for row in cursor.fetchall() if row[0]]

            colors = ['белый', 'черный', 'красный', 'синий', 'зеленый', 'желтый',
                      'оранжевый', 'фиолетовый', 'розовый', 'серый', 'коричневый',
                      'голубой', 'бирюзовый', 'золотой', 'серебряный']

            color_counts = Counter()

            for desc in descriptions:
                desc_lower = desc.lower()
                for color in colors:
                    if color in desc_lower:
                        color_counts[color] += 1

            conn.close()
            return dict(color_counts.most_common())

        except Exception as e:
            logger.error(f"❌ Ошибка анализа цветов: {e}")
            return {}

    async def _analyze_material_patterns(self, days):
        """Анализирует паттерны материалов из описаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT description FROM vision_feedback 
                WHERE feedback_type = 'manual_description' 
                AND created_at >= datetime('now', ?)
            """, (f'-{days} days',))

            descriptions = [row[0] for row in cursor.fetchall() if row[0]]

            materials = ['кожа', 'дерево', 'металл', 'пластик', 'стекло', 'хлопок',
                         'шерсть', 'синтетика', 'резина', 'керамика', 'камень']

            material_counts = Counter()

            for desc in descriptions:
                desc_lower = desc.lower()
                for material in materials:
                    if material in desc_lower:
                        material_counts[material] += 1

            conn.close()
            return dict(material_counts.most_common())

        except Exception as e:
            logger.error(f"❌ Ошибка анализа материалов: {e}")
            return {}

    async def _analyze_error_patterns(self, days):
        """Анализирует частые ошибки распознавания"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM vision_feedback 
                WHERE feedback_type IN ('negative', 'learn_wrong')
                AND created_at >= datetime('now', ?)
            """, (f'-{days} days',))

            error_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM vision_feedback 
                WHERE feedback_type IN ('positive', 'learn_perfect')
                AND created_at >= datetime('now', ?)
            """, (f'-{days} days',))

            success_count = cursor.fetchone()[0]

            total = error_count + success_count
            accuracy = (success_count / total * 100) if total > 0 else 0

            conn.close()

            return {
                "total_feedback": total,
                "errors": error_count,
                "successes": success_count,
                "accuracy": round(accuracy, 1),
                "error_rate": round((error_count / total * 100) if total > 0 else 0, 1)
            }

        except Exception as e:
            logger.error(f"❌ Ошибка анализа ошибок: {e}")
            return {}

    async def _update_knowledge_base(self, categories, colors, materials, errors):
        """Обновляет базу знаний на основе анализа"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_stats (
                    id INTEGER PRIMARY KEY,
                    stat_type TEXT,
                    stat_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            stats_data = {
                "categories": categories,
                "colors": colors,
                "materials": materials,
                "errors": errors,
                "analyzed_at": datetime.now().isoformat()
            }

            cursor.execute("""
                INSERT INTO learning_stats (stat_type, stat_data)
                VALUES (?, ?)
            """, ("weekly_analysis", json.dumps(stats_data, ensure_ascii=False)))

            await self._update_quick_lookup(cursor, categories, colors, materials)

            conn.commit()
            conn.close()

            logger.info("✅ База знаний обновлена на основе анализа фидбэка")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления базы знаний: {e}")
            return False

    async def _update_quick_lookup(self, cursor, categories, colors, materials):
        """Обновляет таблицу быстрого доступа с частыми паттернами"""
        try:
            for category, count in list(categories.items())[:10]:
                if count >= 2:
                    cursor.execute("""
                        INSERT OR REPLACE INTO quick_lookup 
                        (object_type, object_name, confidence, usage_count)
                        VALUES (?, ?, ?, ?)
                    """, ("category", category, min(0.9, count * 0.1), count))

            for color, count in list(colors.items())[:10]:
                if count >= 2:
                    cursor.execute("""
                        INSERT OR REPLACE INTO quick_lookup 
                        (object_type, object_name, confidence, usage_count)
                        VALUES (?, ?, ?, ?)
                    """, ("color", color, min(0.9, count * 0.1), count))

            for material, count in list(materials.items())[:10]:
                if count >= 2:
                    cursor.execute("""
                        INSERT OR REPLACE INTO quick_lookup 
                        (object_type, object_name, confidence, usage_count)
                        VALUES (?, ?, ?, ?)
                    """, ("material", material, min(0.9, count * 0.1), count))

        except Exception as e:
            logger.error(f"❌ Ошибка обновления quick_lookup: {e}")


class VisionFeedbackHandlers:
    """Обработчики для системы обратной связи компьютерного зрения"""

    def __init__(self):
        self.pending_descriptions = {}
        self.notification_sender = None
        self.analyzer = VisionFeedbackAnalyzer()
        self.points_system = UserPointsSystem()
        self.analysis_task = None

        try:
            # Пробуем разные пути импорта
            try:
                from apps.bot.utils.notification_sender import NotificationSender
            except ImportError:
                try:
                    from shared.utils.notification_sender import NotificationSender
                except ImportError:
                    # Если не нашли, создаем заглушку
                    class NotificationSenderStub:
                        async def save_product_to_db(self, *args, **kwargs):
                            return False

                    NotificationSender = NotificationSenderStub

            self.notification_sender = NotificationSender()
            logger.info("✅ NotificationSender инициализирован")
        except Exception as e:
            logger.warning(f"⚠️ NotificationSender не доступен: {e}")
            self.notification_sender = None

    async def start_periodic_analysis(self):
        """Запускает периодический анализ (теперь асинхронный)"""
        try:
            if self.analysis_task is None or self.analysis_task.done():
                self.analysis_task = asyncio.create_task(self._periodic_analysis_worker())
                logger.info("✅ Периодический анализ фидбэка запущен")
                return True
            else:
                logger.info("ℹ️ Периодический анализ уже запущен")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка запуска периодического анализа: {e}")
            return False

    async def _periodic_analysis_worker(self):
        """Рабочий процесс периодического анализа с улучшенной обработкой ошибок"""
        logger.info("🔄 Запуск рабочего процесса периодического анализа...")

        # Первоначальная задержка для стабилизации системы
        await asyncio.sleep(30)

        while True:
            try:
                logger.info("🔄 Запуск анализа фидбэка...")
                analysis = await self.analyzer.analyze_recent_feedback(days=1)

                if "error" not in analysis:
                    logger.info("✅ Ежедневный анализ фидбэка завершен")

                    # Логируем результаты
                    if analysis.get("category_patterns"):
                        top_categories = list(analysis['category_patterns'].items())[:3]
                        logger.info(f"📊 Топ категории: {top_categories}")

                    if analysis.get("error_patterns"):
                        accuracy = analysis['error_patterns'].get('accuracy', 0)
                        logger.info(f"📊 Точность ИИ: {accuracy}%")
                else:
                    logger.warning(f"⚠️ Ошибка анализа: {analysis['error']}")

                # Анализируем раз в 6 часов (21600 секунд)
                await asyncio.sleep(6 * 60 * 60)

            except asyncio.CancelledError:
                logger.info("⏹️ Периодический анализ остановлен")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в рабочем процессе анализа: {e}")
                # Ждем 1 час при ошибке
                await asyncio.sleep(60 * 60)

    async def stop_periodic_analysis(self):
        """Останавливает периодический анализ"""
        try:
            if self.analysis_task and not self.analysis_task.done():
                self.analysis_task.cancel()
                try:
                    await self.analysis_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ Периодический анализ остановлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка остановки анализа: {e}")
            return False

    async def handle_vision_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает обратную связь по компьютерному зрению"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = query.from_user.id

        logger.info(f"🔄 Обработка обратной связи: {data} от пользователя {user_id}")

        try:
            if data.startswith('vision_yes_'):
                url_suffix = data.replace('vision_yes_', '')
                await self._process_positive_feedback(url_suffix, user_id, query)

            elif data.startswith('vision_no_'):
                url_suffix = data.replace('vision_no_', '')
                await self._process_negative_feedback(url_suffix, user_id, query)

            elif data.startswith('vision_unsure_'):
                url_suffix = data.replace('vision_unsure_', '')
                await self._process_unsure_feedback(url_suffix, user_id, query)

            elif data.startswith('vision_describe_'):
                url_suffix = data.replace('vision_describe_', '')
                await self._request_manual_description(url_suffix, user_id, query)

            elif data.startswith('learn_perfect_'):
                url_suffix = data.replace('learn_perfect_', '')
                await self._process_learning_feedback(url_suffix, "perfect", user_id, query)

            elif data.startswith('learn_partial_'):
                url_suffix = data.replace('learn_partial_', '')
                await self._process_learning_feedback(url_suffix, "partial", user_id, query)

            elif data.startswith('learn_wrong_'):
                url_suffix = data.replace('learn_wrong_', '')
                await self._process_learning_feedback(url_suffix, "wrong", user_id, query)

            elif data.startswith('learn_category_'):
                url_suffix = data.replace('learn_category_', '')
                await self._request_category_feedback(url_suffix, user_id, query)

            elif data.startswith('learn_appearance_'):
                url_suffix = data.replace('learn_appearance_', '')
                await self._request_appearance_feedback(url_suffix, user_id, query)

            else:
                await query.edit_message_text("❌ Неизвестный тип обратной связи")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки обратной связи: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке обратной связи")

    async def handle_text_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает текстовые описания товаров от пользователей"""
        user_id = update.message.from_user.id
        description = update.message.text

        logger.info(f"📝 Получено описание от пользователя {user_id}: {description}")

        if user_id in self.pending_descriptions:
            url_suffix = self.pending_descriptions[user_id]

            try:
                success = await self._save_description_to_knowledge_base(url_suffix, description, user_id)
                del self.pending_descriptions[user_id]

                if success:
                    # Добавляем баллы за описание
                    new_points = await self.points_system.add_points(user_id, 20, 'description')

                    # Запускаем немедленный анализ
                    asyncio.create_task(self._analyze_new_description(description))

                    await update.message.reply_text(
                        f"✅ Спасибо за описание! Система обучения уже анализирует его...\n\n"
                        f"🎯 +20 баллов за качественное описание!\n"
                        f"💎 Теперь у вас: {new_points} баллов\n"
                        f"🤖 ИИ станет умнее благодаря вам!"
                    )
                else:
                    await update.message.reply_text("⚠️ Описание получено, но возникла проблема с сохранением.")

            except Exception as e:
                logger.error(f"❌ Ошибка сохранения описания: {e}")
                await update.message.reply_text("❌ Произошла ошибка при сохранении описания")
        else:
            await update.message.reply_text(
                "ℹ️ Чтобы описать товар, сначала нажмите кнопку \"📝 Описать вручную\" "
                "в меню обратной связи компьютерного зрения."
            )

    async def _analyze_new_description(self, description):
        """Немедленно анализирует новое описание"""
        try:
            from collections import Counter
            import re

            words = re.findall(r'\w+', description.lower())
            word_freq = Counter(words)

            if not hasattr(self, 'word_cache'):
                self.word_cache = Counter()

            self.word_cache.update(word_freq)
            logger.info(f"🔍 Проанализировано новое описание: {len(words)} слов")

        except Exception as e:
            logger.error(f"❌ Ошибка быстрого анализа описания: {e}")

    async def _process_positive_feedback(self, url_suffix: str, user_id: int, query):
        """Обрабатывает положительную обратную связь"""
        await self._save_feedback_to_db(url_suffix, "positive", user_id)
        new_points = await self.points_system.add_points(user_id, 5, 'feedback')

        await query.edit_message_text(
            f"✅ Спасибо за подтверждение! Это поможет улучшить компьютерное зрение!\n\n"
            f"🎯 +5 баллов за помощь в обучении ИИ!\n"
            f"💎 Теперь у вас: {new_points} баллов"
        )

    async def _process_negative_feedback(self, url_suffix: str, user_id: int, query):
        """Обрабатывает отрицательную обратную связь"""
        await self._save_feedback_to_db(url_suffix, "negative", user_id)
        new_points = await self.points_system.add_points(user_id, 10, 'correction')

        await query.edit_message_text(
            f"❌ Понятно! Спасибо за исправление ошибки ИИ!\n\n"
            f"🎯 +10 баллов за исправление ошибки!\n"
            f"💎 Теперь у вас: {new_points} баллов"
        )

    async def _process_unsure_feedback(self, url_suffix: str, user_id: int, query):
        """Обрабатывает неопределенную обратную связь"""
        await self._save_feedback_to_db(url_suffix, "unsure", user_id)
        new_points = await self.points_system.add_points(user_id, 2, 'feedback')

        await query.edit_message_text(
            f"🤷 Понятно, бывает сложно определить.\n\n"
            f"🎯 +2 балла за честность!\n"
            f"💎 Теперь у вас: {new_points} баллов"
        )

    async def _process_learning_feedback(self, url_suffix: str, feedback_type: str, user_id: int, query):
        """Обрабатывает расширенную обратную связь для обучения"""
        await self._save_feedback_to_db(url_suffix, f"learn_{feedback_type}", user_id)

        points_map = {
            "perfect": (5, 'feedback'),
            "partial": (8, 'feedback'),
            "wrong": (12, 'correction')
        }

        points, reason = points_map.get(feedback_type, (5, 'feedback'))
        new_points = await self.points_system.add_points(user_id, points, reason)

        messages = {
            "perfect": f"✅ Отлично! ИИ правильно распознал! +{points} баллов\n💎 Теперь у вас: {new_points} баллов",
            "partial": f"⚠️ Понятно, есть неточности. +{points} баллов\n💎 Теперь у вас: {new_points} баллов",
            "wrong": f"❌ Ясно, ИИ ошибся. Спасибо за исправление! +{points} баллов\n💎 Теперь у вас: {new_points} баллов"
        }

        await query.edit_message_text(messages.get(feedback_type, "Спасибо за обратную связь!"))

    async def _request_manual_description(self, url_suffix: str, user_id: int, query):
        """Запрашивает ручное описание и сохраняет ожидание"""
        self.pending_descriptions[user_id] = url_suffix

        await query.edit_message_text(
            "📝 Отлично! Пожалуйста, опишите товар своими словами:\n\n"
            "• Основные характеристики\n• Цвет\n• Материалы\n• Состояние\n\n"
            "Отправьте сообщение с описанием, и я учту это для обучения.\n\n"
            "💡 Просто напишите в чат то, что видите на картинке!\n"
            "🎯 +20 баллов за качественное описание!"
        )

    async def _request_category_feedback(self, url_suffix: str, user_id: int, query):
        """Запрашивает категорию"""
        await query.edit_message_text(
            "📁 Выберите правильную категорию из списка выше"
        )

    async def _request_appearance_feedback(self, url_suffix: str, user_id: int, query):
        """Запрашивает описание внешнего вида"""
        await query.edit_message_text(
            "🎨 Опишите внешний вид товара:\n\n"
            "• Цветовая гамма\n• Материалы\n• Стиль\n• Особенности\n\n"
            "Это очень поможет в обучении! +20 баллов за подробное описание!"
        )

    async def _save_description_to_knowledge_base(self, url_suffix: str, description: str, user_id: int):
        """Сохраняет описание в базу знаний"""
        try:
            logger.info(f"💾 Сохранение описания для {url_suffix}: {description}")

            if self.notification_sender:
                product_data = {
                    'url': url_suffix,
                    'name': f"Товар с описанием от пользователя {user_id}",
                    'description': description,
                    'user_feedback': description,
                    'feedback_type': 'manual_description'
                }

                success = await self.notification_sender.save_product_to_db(
                    product_data, economy=0, economy_percent=0
                )

                if success:
                    logger.info(f"✅ Описание сохранено через NotificationSender: {url_suffix}")
                    return True

            return await self._save_description_directly(url_suffix, description, user_id)

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в базу знаний: {e}")
            return await self._save_description_directly(url_suffix, description, user_id)

    async def _save_description_directly(self, url_suffix: str, description: str, user_id: int):
        """Сохраняет описание напрямую в базу данных"""
        try:
            from asgiref.sync import sync_to_async
            from apps.website.models import FoundItem

            @sync_to_async
            def update_item_description():
                try:
                    items = FoundItem.objects.filter(url__contains=url_suffix)
                    if items.exists():
                        item = items.first()
                        if not item.description or item.description == 'Описание отсутствует':
                            item.description = description
                        else:
                            item.description += f"\n\n👤 Описание пользователя: {description}"
                        item.save()
                        logger.info(f"✅ Описание обновлено для товара: {item.title}")
                        return True
                    else:
                        logger.warning(f"⚠️ Товар с URL содержащим '{url_suffix}' не найден в базе")
                        return False
                except Exception as e:
                    logger.error(f"❌ Ошибка обновления описания в базе: {e}")
                    return False

            return await update_item_description()

        except Exception as e:
            logger.error(f"❌ Ошибка прямого сохранения описания: {e}")
            return False

    async def _save_feedback_to_db(self, url_suffix: str, feedback_type: str, user_id: int):
        """Сохраняет фидбэк в базу данных"""
        try:
            from asgiref.sync import sync_to_async
            from apps.website.models import VisionFeedback
            from django.utils import timezone

            @sync_to_async
            def save_feedback():
                try:
                    feedback = VisionFeedback(
                        user_id=user_id,
                        item_url=url_suffix,
                        feedback_type=feedback_type,
                        created_at=timezone.now()
                    )
                    feedback.save()
                    logger.info(f"✅ Feedback сохранен: {feedback_type} для {url_suffix}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Ошибка сохранения фидбэка: {e}")
                    return False

            return await save_feedback()

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения фидбэка в базу: {e}")
            return False

    async def get_learning_stats(self):
        """Возвращает статистику обучения"""
        try:
            analysis = await self.analyzer.analyze_recent_feedback(days=7)
            return analysis
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики обучения: {e}")
            return {"error": str(e)}

    async def get_user_points_stats(self, user_id: int):
        """Возвращает статистику баллов пользователя"""
        return await self.points_system.get_user_stats(user_id)

    async def get_leaderboard(self, limit=10):
        """Возвращает таблицу лидеров"""
        return await self.points_system.get_leaderboard(limit)

    def get_handlers(self) -> list:
        """Возвращает список обработчиков"""
        return [
            CallbackQueryHandler(self.handle_vision_feedback, pattern="^(vision_|learn_)"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_description)
        ]


# Создаем глобальный экземпляр обработчиков
vision_handlers = VisionFeedbackHandlers()