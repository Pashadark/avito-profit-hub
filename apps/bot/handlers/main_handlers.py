"""
Основные обработчики главного меню и команд
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from asgiref.sync import sync_to_async

from apps.bot.keyboards import (
    get_main_menu_keyboard,
    get_unlinked_menu_keyboard
)

from apps.bot.services.user_service import UserService

logger = logging.getLogger('bot.handlers.main')


class MainHandlers:
    """Обработчики главного меню"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        logger.info(f"👤 Пользователь {user.id} ({user.username}) запустил бота")

        await self.show_start_menu(update, from_callback=False)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 **Справка по командам:**

**Основные команды:**
/start - Главное меню
/help - Эта справка
/link - Привязать аккаунт Django
/todo - Управление задачами

**Управление через меню:**
👤 Мой профиль - информация о профиле, баланс, подписка
🤖 Парсер - управление поиском на Avito
⚙️ Настройки - настройки бота и аккаунта

💡 **Все функции доступны через кнопки меню!**
        """

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def show_start_menu(self, update: Update, from_callback: bool = False):
        """Показать стартовое меню

        Args:
            update: Объект Update от Telegram
            from_callback: True если вызвано из callback_query, False если из команды
        """
        from apps.bot.keyboards import get_main_menu_keyboard, get_unlinked_menu_keyboard
        from apps.bot.services.user_service import UserService

        # Определяем источник вызова
        if from_callback and update.callback_query:
            # Вызвано из кнопки
            user = update.callback_query.from_user
            chat_id = update.callback_query.message.chat_id
            message_id = update.callback_query.message.message_id
            await update.callback_query.answer()
            is_callback = True
        elif update.message:
            # Вызвано командой /start
            user = update.effective_user
            chat_id = update.message.chat_id
            message_id = None
            is_callback = False
        else:
            logger.error("Неизвестный тип update")
            return

        # Получаем профиль
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if profile:
            # Получаем username через sync_to_async
            @sync_to_async
            def get_username(profile_obj):
                return profile_obj.user.username if profile_obj and profile_obj.user else "Неизвестный"

            username = await get_username(profile)

            welcome_text = f"""
🚀 **Добро пожаловать в Profit Hub, {user.first_name}!**

Ваш Telegram привязан к аккаунту: **{username}**

Выберите раздел для управления:
            """
            keyboard = get_main_menu_keyboard()
        else:
            welcome_text = f"""
🔗 **Добро пожаловать в Profit Hub!**

Ваш Telegram не привязан к аккаунту.
Для начала работы нужно привязать аккаунт Django.

💡 **Как привязать:**
1. Используйте команду /link ВАШ_ЛОГИН
2. Или перейдите на сайт: http://127.0.0.1:8000/profile/

Ваш User ID: `{user.id}`
            """
            keyboard = get_unlinked_menu_keyboard()

        # Отправляем или редактируем сообщение
        try:
            if is_callback:
                # Редактируем существующее сообщение
                await update.callback_query.edit_message_text(
                    text=welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                # Отправляем новое сообщение
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            # Фолбэк: всегда отправляем новое сообщение
            await self.bot.send_message(
                chat_id,
                welcome_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    # 🔥 ДОБАВЛЕННЫЙ МЕТОД!
    async def handle_main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик главного меню"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        logger.info(f"🔄 Обработка главного меню: {callback_data}")

        if callback_data == "main_menu":
            await self.show_start_menu(update, from_callback=True)
        elif callback_data == "help":
            await self.help_callback(query)
        else:
            await query.edit_message_text("⚙️ Команда передана в другой обработчик")

    async def help_callback(self, query):
        """Обработчик справки из кнопки"""
        help_text = """
📖 **Справка по боту:**

**Основные разделы:**
👤 **Мой профиль** - информация о вашем аккаунте, баланс, подписка
🤖 **Парсер** - управление поиском товаров на Avito
⚙️ **Настройки** - настройки бота и уведомлений

**Команды:**
/start - Главное меню
/link - Привязать аккаунт
/todo - Создать задачу

💡 **Для привязки аккаунта используйте команду:**
`/link ваш_логин_django`
        """

        # 🔥 ИСПРАВЛЕНО: импорт из правильного места
        from apps.bot.keyboards import get_back_to_main_menu_keyboard

        await query.edit_message_text(
            help_text,
            reply_markup=get_back_to_main_menu_keyboard(),
            parse_mode='Markdown'
        )

    def register_handlers(self, application):
        """Регистрация обработчиков"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))

        # Обработчики главного меню
        application.add_handler(CallbackQueryHandler(
            self.handle_main_menu_callback,  # ✅ Теперь метод существует
            pattern="^(main_menu|help)$"
        ))

        logger.info("✅ Основные обработчики зарегистрированы")