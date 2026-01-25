"""
Обработчики настроек
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from asgiref.sync import sync_to_async

from apps.bot.keyboards import (
    get_settings_menu_keyboard,
    get_group_settings_keyboard,
    get_notifications_keyboard,
    get_back_to_main_menu_keyboard
)
from apps.bot.services.user_service import UserService

logger = logging.getLogger('bot.handlers.settings')


class SettingsHandlers:
    """Обработчики настроек"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def handle_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню настроек"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user = query.from_user

        logger.info(f"🔄 Обработка настроек: {callback_data} от {user.id}")

        if callback_data == "menu_settings":
            await self.show_settings_menu(query)
        elif callback_data == "settings_userid":
            await self.show_user_id(query, user)
        elif callback_data == "settings_group":
            await self.show_group_settings(query)
        elif callback_data == "settings_notifications":
            await self.show_notifications_settings(query, user)
        elif callback_data == "group_info":
            await self.show_group_info(query)
        elif callback_data == "group_members":
            await self.show_group_members(query)
        elif callback_data == "group_limits":
            await self.show_group_limits(query)
        elif callback_data == "notifications_on":
            await self.toggle_notifications(query, user, True)
        elif callback_data == "notifications_off":
            await self.toggle_notifications(query, user, False)
        else:
            await query.edit_message_text("⚙️ Команда в разработке")

    async def show_settings_menu(self, query):
        """Показать меню настроек"""
        settings_text = """
⚙️ **Настройки**

Настройте параметры бота и аккаунта.

**Доступные настройки:**
🆔 **User ID** - информация о вашем Telegram ID
👥 **Управление группой** - настройки группового чата
🔔 **Уведомления** - включение/выключение уведомлений
🔗 **Привязка аккаунта** - привязка Telegram к Django

Выберите раздел:
        """

        keyboard = get_settings_menu_keyboard()

        await query.edit_message_text(
            settings_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_user_id(self, query, user):
        """Показать User ID"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if profile:
            id_text = f"""
🆔 **Информация о пользователе**

💬 **Ваш Telegram User ID:** `{user.id}`
📧 **Username:** @{user.username or 'Не указан'}
👤 **Имя:** {user.first_name or 'Не указано'}
🔗 **Привязан к Django:** ✅ {profile.user.username}

💡 *Этот ID уникален для вашего аккаунта Telegram*
            """
        else:
            id_text = f"""
🆔 **Информация о пользователе**

💬 **Ваш Telegram User ID:** `{user.id}`
📧 **Username:** @{user.username or 'Не указан'}
👤 **Имя:** {user.first_name or 'Не указано'}
🔗 **Привязан к Django:** ❌ Не привязан

💡 *Используйте команду /link для привязки к Django аккаунту*
            """

        keyboard = get_back_to_main_menu_keyboard()

        await query.edit_message_text(
            id_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_group_settings(self, query):
        """Показать настройки группы"""
        group_text = """
👥 **Управление группой**

Настройки группового чата для уведомлений.

**Доступные функции:**
ℹ️ **Информация о группе** - основная информация о чате
👥 **Участники** - список участников и статистика
⚙️ **Настройки лимитов** - ограничения на отправку сообщений

💡 *Для работы с группой добавьте бота в чат и назначьте администратором*
        """

        keyboard = get_group_settings_keyboard()

        await query.edit_message_text(
            group_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_notifications_settings(self, query, user):
        """Показать настройки уведомлений"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if profile:
            notifications_status = "✅ Включены" if profile.telegram_notifications else "❌ Выключены"
            notifications_text = f"""
🔔 **Настройки уведомлений**

**Текущий статус:** {notifications_status}

**Типы уведомлений:**
• Новые товары по вашим запросам
• Изменение цен на отслеживаемые товары
• Уведомления о подписке и балансе
• Системные уведомления

Выберите действие:
            """
        else:
            notifications_text = """
🔔 **Настройки уведомлений**

❌ **Сначала привяжите аккаунт!**

Для настройки уведомлений нужно привязать Telegram к Django аккаунту.

Используйте команду /link или кнопку "Привязка аккаунта"
            """

        keyboard = get_notifications_keyboard()

        await query.edit_message_text(
            notifications_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_group_info(self, query):
        """Показать информацию о группе"""
        try:
            # Проверяем доступен ли менеджер групп
            from apps.bot.group_manager import group_manager

            if not group_manager:
                await query.edit_message_text(
                    "❌ Менеджер групп недоступен\n\n"
                    "Модуль управления группами не инициализирован.",
                    reply_markup=get_group_settings_keyboard()
                )
                return

            # Получаем информацию о группе
            chat_id = query.message.chat.id
            group_info = await group_manager.get_group_info(chat_id)

            if group_info:
                status = "✅ Можно отправлять" if not group_info['is_over_limit'] else "🚫 Превышен лимит"

                info_text = f"""
👥 **Информация о группе**

📝 **Название:** {group_info['title']}
🆔 **ID:** `{group_info['id']}`
👤 **Участников:** {group_info['members_count']}
📊 **Лимит:** {group_manager.max_members}
🎯 **Статус:** {status}

💡 *Лимит участников: {group_manager.max_members}*
                """
            else:
                info_text = """
👥 **Информация о группе**

❌ **Не удалось получить информацию**

Возможные причины:
1. Бот не добавлен в группу
2. Бот не является администратором
3. Ошибка получения данных

💡 *Добавьте бота в группу и назначьте администратором*
                """

        except ImportError:
            info_text = """
👥 **Информация о группе**

❌ **Модуль управления группами не установлен**

Установите модуль group_manager для работы с группами.
            """

        except Exception as e:
            logger.error(f"Ошибка получения информации о группе: {e}")
            info_text = f"""
👥 **Информация о группе**

❌ **Ошибка:** {str(e)[:100]}

Обратитесь к администратору.
            """

        keyboard = get_group_settings_keyboard()

        await query.edit_message_text(
            info_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_group_members(self, query):
        """Показать участников группы"""
        await query.edit_message_text(
            "👥 **Участники группы**\n\n"
            "Функция просмотра участников находится в разработке.\n\n"
            "Скоро здесь будет:\n"
            "• Список участников\n"
            "• Статистика активности\n"
            "• Управление участниками\n\n"
            "Ожидайте в следующих обновлениях!",
            reply_markup=get_group_settings_keyboard()
        )

    async def show_group_limits(self, query):
        """Показать настройки лимитов"""
        await query.edit_message_text(
            "⚙️ **Настройки лимитов**\n\n"
            "Функция настройки лимитов находится в разработке.\n\n"
            "Скоро можно будет настроить:\n"
            "• Лимит участников для отправки\n"
            "• Частоту уведомлений\n"
            "• Фильтрацию сообщений\n\n"
            "Ожидайте в следующих обновлениях!",
            reply_markup=get_group_settings_keyboard()
        )

    async def toggle_notifications(self, query, user, enable):
        """Включить/выключить уведомления"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if not profile:
            await query.edit_message_text(
                "❌ Профиль не найден\n\n"
                "Сначала привяжите Telegram к Django аккаунту.",
                reply_markup=get_settings_menu_keyboard()
            )
            return

        profile.telegram_notifications = enable
        await sync_to_async(profile.save)()

        status = "✅ включены" if enable else "❌ выключены"

        await query.edit_message_text(
            f"🔔 **Уведомления {status}!**\n\n"
            f"Теперь вы {'будете получать' if enable else 'не будете получать'} уведомления от бота.",
            reply_markup=get_notifications_keyboard()
        )

    def register_handlers(self, application):
        """Регистрация обработчиков"""
        application.add_handler(CallbackQueryHandler(
            self.handle_settings_callback,
            pattern="^(menu_settings|settings_userid|settings_group|settings_notifications|group_info|group_members|group_limits|notifications_on|notifications_off)$"
        ))

        logger.info("✅ Обработчики настроек зарегистрированы")