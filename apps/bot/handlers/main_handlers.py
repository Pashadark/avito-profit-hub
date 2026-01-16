"""
Основные обработчики команд бота
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from telegram.error import TelegramError
import logging

logger = logging.getLogger('bot.handlers.main')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f'🚀 Добро пожаловать в Profit Hub, {user.first_name}!\n\n'
        'Я помогу вам находить выгодные предложения на Avito.\n\n'
        '📋 Доступные команды:\n'
        '/search - добавить поисковый запрос\n'
        '/queries - показать текущие запросы\n'
        '/remove_query - удалить запрос\n'
        '/clear_queries - очистить все запросы\n'
        '/stats - статистика работы\n'
        '/help - показать справку'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
🤖 <b>Команды бота:</b>

<b>Управление поиском:</b>
/search - Добавить новый поисковый запрос
/queries - Показать текущие запросы
/remove_query <запрос> - Удалить конкретный запрос
/clear_queries - Очистить все запросы

<b>Информация:</b>
/stats - Статистика работы
/help - Эта справка

<b>Примеры:</b>
/search → введите "pioneer"
/remove_query iphone
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from apps.parsing.utils.parser_selenium import selenium_parser
        from apps.bot.bot import bot_instance

        stats_text = f"""
📊 <b>Статистика парсера:</b>

<b>Состояние:</b> {'🟢 Запущен' if selenium_parser.is_running else '🔴 Остановлен'}
<b>Запросов в поиске:</b> {len(selenium_parser.search_queries)}
<b>Запросы:</b> {', '.join(selenium_parser.search_queries[:5])}{'...' if len(selenium_parser.search_queries) > 5 else ''}

<b>Бот:</b> {'🟢 Активен' if bot_instance and bot_instance.is_running else '🔴 Не активен'}
"""
        await update.message.reply_text(stats_text, parse_mode='HTML')
    except ImportError as e:
        await update.message.reply_text('❌ Ошибка: модуль парсера не найден')
    except Exception as e:
        await update.message.reply_text('❌ Ошибка получения статистики.')


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'ℹ️ Используйте команды для управления поиском:\n'
        '/search - добавить запрос\n'
        '/queries - показать запросы\n'
        '/help - помощь'
    )


def setup_handlers(app: Application) -> None:
    """
    Настройка основных обработчиков команд для бота

    Args:
        app: Экземпляр Application из python-telegram-bot
    """
    try:
        logger.info("🔧 Настройка основных обработчиков команд...")

        # Основные команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("stats", stats))

        # Обработчик текстовых сообщений (если не команда)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

        logger.info("✅ Основные обработчики команд настроены")

    except Exception as e:
        logger.error(f"❌ Ошибка настройки обработчиков: {e}")
        raise


# Если нужно экспортировать обработчик избранного, добавь:
async def handle_favorite_callback(query, context):
    """Обработчик кнопки 'Добавить в избранное'"""
    try:
        # Импорт здесь чтобы избежать циклических импортов
        from apps.bot.bot import bot_instance

        if bot_instance:
            # Вызываем метод из экземпляра бота
            return await bot_instance.handle_favorite_callback(query, context)
        else:
            await query.answer("❌ Бот не инициализирован", show_alert=True)

    except Exception as e:
        logger.error(f"❌ Ошибка в handle_favorite_callback: {e}")
        await query.answer("❌ Произошла ошибка", show_alert=True)