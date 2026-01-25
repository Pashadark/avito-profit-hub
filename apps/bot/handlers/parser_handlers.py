"""
Обработчики парсера
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from asgiref.sync import sync_to_async

from apps.bot.keyboards import (
    get_parser_menu_keyboard,
    get_parser_stats_keyboard,
    get_parser_queries_keyboard
)

logger = logging.getLogger('bot.handlers.parser')


class ParserHandlers:
    """Обработчики парсера"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def handle_parser_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню парсера"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user = query.from_user

        logger.info(f"🔄 Обработка парсера: {callback_data} от {user.id}")

        if callback_data == "menu_parser":
            await self.show_parser_menu(query)
        elif callback_data == "parser_stats":
            await self.show_parser_stats(query)
        elif callback_data == "parser_queries":
            await self.show_parser_queries(query)
        elif callback_data == "parser_start":
            await self.start_parser(query)
        elif callback_data == "parser_stop":
            await self.stop_parser(query)
        elif callback_data == "parser_add_query":
            await self.add_parser_query(query)
        elif callback_data == "parser_clear":
            await self.clear_parser_queries(query)
        elif callback_data == "parser_export":
            await self.export_parser_data(query)
        elif callback_data == "parser_detailed_stats":
            await self.show_detailed_stats(query)
        else:
            await query.edit_message_text("⚙️ Команда в разработке")

    async def show_parser_menu(self, query):
        """Показать меню парсера"""
        parser_text = """
🤖 **Парсер Avito**

Система мониторинга цен на Avito в реальном времени.
Находит выгодные предложения по вашим запросам.

**Функции:**
• Автоматический поиск товаров
• Уведомления о выгодных ценах
• Статистика эффективности
• Управление запросами

Выберите действие:
        """

        keyboard = get_parser_menu_keyboard()

        await query.edit_message_text(
            parser_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_parser_stats(self, query):
        """Показать статистику парсера"""
        try:
            # Пробуем получить статистику из парсера
            from apps.parsing.utils.parser_selenium import selenium_parser

            if hasattr(selenium_parser, 'is_running'):
                status = "🟢 Работает" if selenium_parser.is_running else "🔴 Остановлен"
                queries = getattr(selenium_parser, 'search_queries', [])

                stats_text = f"""
📊 **Статистика парсера**

**Состояние:** {status}
**Активных запросов:** {len(queries)}
**Интервал проверки:** {getattr(selenium_parser, 'check_interval', 30)} мин.

**Последние запросы:**
{', '.join(queries[:5]) if queries else 'Нет запросов'}
                """
            else:
                stats_text = """
📊 **Статистика парсера**

**Состояние:** 🔴 Модуль недоступен
**Активных запросов:** 0
**Интервал проверки:** Неизвестно

⚠️ *Модуль парсера не инициализирован*
                """

        except ImportError:
            stats_text = """
📊 **Статистика парсера**

**Состояние:** 🔴 Модуль не найден
**Активных запросов:** 0
**Интервал проверки:** Неизвестно

⚠️ *Установите модуль парсера*
            """

        except Exception as e:
            logger.error(f"Ошибка получения статистики парсера: {e}")
            stats_text = f"""
📊 **Статистика парсера**

**Состояние:** 🔴 Ошибка
**Ошибка:** {str(e)[:100]}

⚠️ *Обратитесь к администратору*
            """

        keyboard = get_parser_stats_keyboard()

        await query.edit_message_text(
            stats_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_parser_queries(self, query):
        """Показать запросы парсера"""
        try:
            from apps.parsing.utils.parser_selenium import selenium_parser

            queries = getattr(selenium_parser, 'search_queries', [])

            if not queries:
                queries_text = "📭 **Запросы отсутствуют**\n\nДобавьте первый запрос для начала поиска."
            else:
                queries_text = "🔍 **Мои поисковые запросы**\n\n"
                for i, query_text in enumerate(queries, 1):
                    queries_text += f"{i}. {query_text}\n"

        except Exception as e:
            logger.error(f"Ошибка получения запросов: {e}")
            queries_text = "❌ Не удалось загрузить запросы"

        keyboard = get_parser_queries_keyboard()

        await query.edit_message_text(
            queries_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def start_parser(self, query):
        """Запустить парсер"""
        try:
            from apps.parsing.utils.parser_selenium import selenium_parser

            if not hasattr(selenium_parser, 'start_parsing'):
                await query.edit_message_text("❌ Метод запуска не найден в парсере")
                return

            if selenium_parser.is_running:
                await query.edit_message_text("✅ Парсер уже запущен")
                return

            # Запускаем в отдельном потоке
            import threading
            thread = threading.Thread(target=selenium_parser.start_parsing)
            thread.daemon = True
            thread.start()

            await query.edit_message_text("🚀 Парсер запускается...")

            # Ждем немного и обновляем статус
            import time
            time.sleep(2)

            if selenium_parser.is_running:
                await query.edit_message_text(
                    "✅ **Парсер успешно запущен!**\n\n"
                    "Теперь система будет автоматически мониторить цены на Avito.",
                    reply_markup=get_parser_menu_keyboard()
                )
            else:
                await query.edit_message_text(
                    "❌ **Не удалось запустить парсер**\n\n"
                    "Проверьте настройки и логи парсера.",
                    reply_markup=get_parser_menu_keyboard()
                )

        except Exception as e:
            logger.error(f"Ошибка запуска парсера: {e}")
            await query.edit_message_text(
                f"❌ **Ошибка запуска:** {str(e)}",
                reply_markup=get_parser_menu_keyboard()
            )

    async def stop_parser(self, query):
        """Остановить парсер"""
        try:
            from apps.parsing.utils.parser_selenium import selenium_parser

            if not hasattr(selenium_parser, 'stop_parsing'):
                await query.edit_message_text("❌ Метод остановки не найден в парсере")
                return

            if not selenium_parser.is_running:
                await query.edit_message_text("ℹ️ Парсер уже остановлен")
                return

            selenium_parser.stop_parsing()

            await query.edit_message_text(
                "⏹️ **Парсер остановлен!**\n\n"
                "Автоматический поиск приостановлен.",
                reply_markup=get_parser_menu_keyboard()
            )

        except Exception as e:
            logger.error(f"Ошибка остановки парсера: {e}")
            await query.edit_message_text(
                f"❌ **Ошибка остановки:** {str(e)}",
                reply_markup=get_parser_menu_keyboard()
            )

    async def add_parser_query(self, query):
        """Добавить запрос в парсер"""
        await query.edit_message_text(
            "🔍 **Добавление поискового запроса**\n\n"
            "Отправьте текст поискового запроса в чат.\n\n"
            "**Примеры:**\n"
            "• iphone 13\n"
            "• macbook pro\n"
            "• велосипед горный\n\n"
            "⚠️ *Запрос должен быть на русском языке*",
            reply_markup=get_parser_queries_keyboard()
        )

    async def clear_parser_queries(self, query):
        """Очистить все запросы"""
        try:
            from apps.parsing.utils.parser_selenium import selenium_parser

            if hasattr(selenium_parser, 'search_queries'):
                selenium_parser.search_queries = []
                await query.edit_message_text(
                    "🗑️ **Все запросы очищены!**\n\n"
                    "Добавьте новые запросы для продолжения поиска.",
                    reply_markup=get_parser_queries_keyboard()
                )
            else:
                await query.edit_message_text(
                    "❌ Не удалось очистить запросы",
                    reply_markup=get_parser_queries_keyboard()
                )

        except Exception as e:
            logger.error(f"Ошибка очистки запросов: {e}")
            await query.edit_message_text(
                f"❌ **Ошибка:** {str(e)}",
                reply_markup=get_parser_queries_keyboard()
            )

    async def export_parser_data(self, query):
        """Экспортировать данные парсера"""
        await query.edit_message_text(
            "💾 **Экспорт данных**\n\n"
            "Функция экспорта находится в разработке.\n\n"
            "Скоро можно будет экспортировать:\n"
            "• Найденные товары\n"
            "• Статистику поиска\n"
            "• Историю цен\n\n"
            "Ожидайте в следующих обновлениях!",
            reply_markup=get_parser_menu_keyboard()
        )

    async def show_detailed_stats(self, query):
        """Показать детальную статистику"""
        await query.edit_message_text(
            "📊 **Детальная статистика**\n\n"
            "Раздел находится в разработке.\n\n"
            "Скоро здесь будет:\n"
            "• Графики эффективности\n"
            "• Анализ по категориям\n"
            "• Прогнозы и рекомендации\n\n"
            "Ожидайте в следующих обновлениях!",
            reply_markup=get_parser_stats_keyboard()
        )

    def register_handlers(self, application):
        """Регистрация обработчиков"""
        application.add_handler(CallbackQueryHandler(
            self.handle_parser_callback,
            pattern="^(menu_parser|parser_stats|parser_queries|parser_start|parser_stop|parser_add_query|parser_clear|parser_export|parser_detailed_stats)$"
        ))

        logger.info("✅ Обработчики парсера зарегистрированы")