"""
Основные обработчики главного меню и команд
Исправленная версия с правильной структурой python-telegram-bot
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from asgiref.sync import sync_to_async

from apps.bot.keyboards import (
    get_main_menu_keyboard,
    get_unlinked_menu_keyboard,
    get_back_to_main_menu_keyboard
)
from apps.bot.services.user_service import UserService

logger = logging.getLogger('bot.handlers.main')


class MainHandlers:
    """Обработчики главного меню"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"👤 Пользователь {user.id} ({user.username}) запустил бота")

        await self._show_start_menu(update)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        help_text = (
            "📖 *Справка по командам:*\n\n"
            "*Основные команды:*\n"
            "/start - Главное меню\n"
            "/help - Эта справка\n"
            "/link - Привязать аккаунт Django\n"
            "/todo - Управление задачами\n\n"
            "*Управление через меню:*\n"
            "👤 Мой профиль - информация о профиле, баланс, подписка\n"
            "🤖 Парсер - управление поиском на Avito\n"
            "⚙️ Настройки - настройки бота и аккаунта\n\n"
            "💡 *Все функции доступны через кнопки меню!*"
        )

        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=get_back_to_main_menu_keyboard()
        )

    async def _show_start_menu(self, update: Update, edit_message: bool = False) -> None:
        """Показать/обновить стартовое меню"""
        user = update.effective_user

        # Получаем профиль пользователя
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if profile:
            # Получаем username через sync_to_async
            username = await sync_to_async(
                lambda: profile.user.username if profile.user else "Неизвестный"
            )()

            welcome_text = (
                f"🚀 *Добро пожаловать в Profit Hub, {user.first_name}!*\n\n"
                f"Ваш Telegram привязан к аккаунту: *{username}*\n\n"
                "Выберите раздел для управления:"
            )
            keyboard = get_main_menu_keyboard()
        else:
            welcome_text = (
                f"🔗 *Добро пожаловать в Profit Hub!*\n\n"
                f"Ваш Telegram не привязан к аккаунту.\n"
                f"Для начала работы нужно привязать аккаунт Django.\n\n"
                f"*Как привязать:*\n"
                f"1. Используйте команду `/link ВАШ_ЛОГИН`\n"
                f"2. Или перейдите на сайт: http://127.0.0.1:8000/profile/\n\n"
                f"Ваш User ID: `{user.id}`"
            )
            keyboard = get_unlinked_menu_keyboard()

        try:
            if edit_message and update.callback_query:
                await update.callback_query.edit_message_text(
                    text=welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            # Фолбэк без Markdown
            fallback_text = "Добро пожаловать! Выберите действие:"
            await update.message.reply_text(fallback_text, reply_markup=keyboard)

    async def _handle_main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик callback-запросов главного меню"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        logger.info(f"🔄 Обработка главного меню: {callback_data}")

        if callback_data == "main_menu":
            await self._show_start_menu(update, edit_message=True)
        elif callback_data == "help":
            await self._show_help_callback(query)
        else:
            await query.edit_message_text(
                "⚙️ Переходим к другому разделу...",
                reply_markup=get_back_to_main_menu_keyboard()
            )

    async def _show_help_callback(self, query) -> None:
        """Показать справку через callback"""
        help_text = (
            "📖 *Справка по боту:*\n\n"
            "*Основные разделы:*\n"
            "👤 *Мой профиль* - информация о вашем аккаунте, баланс, подписка\n"
            "🤖 *Парсер* - управление поиском товаров на Avito\n"
            "⚙️ *Настройки* - настройки бота и уведомлений\n\n"
            "*Команды:*\n"
            "/start - Главное меню\n"
            "/link - Привязать аккаунт\n"
            "/todo - Создать задачу\n\n"
            "*Для привязки аккаунта используйте команду:*\n"
            "`/link ваш_логин_django`"
        )

        await query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=get_back_to_main_menu_keyboard()
        )

    def register_handlers(self, application) -> None:
        """Регистрация обработчиков в приложении"""
        # Регистрируем команды
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))

        # Регистрируем обработчики callback-запросов
        application.add_handler(
            CallbackQueryHandler(
                self._handle_main_menu_callback,
                pattern="^(main_menu|help)$"
            )
        )

        logger.info("✅ Основные обработчики зарегистрированы")