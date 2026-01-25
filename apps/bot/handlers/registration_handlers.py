"""
Обработчики регистрации и привязки аккаунта
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from asgiref.sync import sync_to_async

from apps.bot.services.user_service import UserService

logger = logging.getLogger('bot.handlers.registration')


class RegistrationHandlers:
    """Обработчики регистрации"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def link_account_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /link - привязка аккаунта"""
        user = update.effective_user

        try:
            # Проверяем, не привязан ли уже профиль
            profile = await sync_to_async(UserService.get_user_profile)(user.id)

            if profile:
                await update.message.reply_text(
                    f"✅ Ваш Telegram уже привязан к аккаунту: **{profile.user.username}**\n\n"
                    f"👤 Имя: {profile.user.get_full_name() or 'Не указано'}\n"
                    f"💰 Баланс: {profile.balance} ₽\n"
                    f"🆔 Telegram ID: `{user.id}`",
                    parse_mode='Markdown'
                )
                return

            # Получаем логин Django из сообщения
            if not context.args:
                # Генерируем код верификации
                code = await sync_to_async(UserService.generate_verification_code)(user.id)

                await update.message.reply_text(
                    f"🔗 **Система привязки аккаунта**\n\n"
                    f"📱 **Ваш Telegram:**\n"
                    f"• User ID: `{user.id}`\n"
                    f"• Username: @{user.username or 'не указан'}\n"
                    f"• Имя: {user.first_name or 'Не указано'}\n\n"
                    f"🔐 **Код верификации:** `{code}`\n\n"
                    f"**Для привязки:**\n"
                    f"1. Перейдите на сайт: http://127.0.0.1:8000/profile/\n"
                    f"2. В разделе 'Telegram' введите код\n"
                    f"3. Или используйте команду: `/link ВАШ_ЛОГИН_ДЖАНГО`\n\n"
                    f"**Пример:** `/link {user.username or 'ваш_логин'}`",
                    parse_mode='Markdown'
                )
                return

            django_username = context.args[0].strip()

            # Привязываем аккаунт
            from django.contrib.auth.models import User

            try:
                django_user = await sync_to_async(User.objects.get)(username=django_username)
            except User.DoesNotExist:
                await update.message.reply_text(
                    "❌ Пользователь с таким логином не найден.\n"
                    "Проверьте правильность написания логина Django.",
                    parse_mode='Markdown'
                )
                return

            # Проверяем, не привязан ли уже этот аккаунт к другому Telegram
            from apps.website.models import UserProfile

            existing_link = await sync_to_async(UserProfile.objects.filter)(
                user=django_user,
                telegram_verified=True
            ).first()

            if existing_link:
                await update.message.reply_text(
                    f"❌ Аккаунт `{django_username}` уже привязан к другому Telegram.\n"
                    f"Telegram ID: `{existing_link.telegram_user_id}`",
                    parse_mode='Markdown'
                )
                return

            # Привязываем
            profile = await sync_to_async(UserService.link_telegram_account)(
                django_username, user.id, user.username
            )

            if not profile:
                await update.message.reply_text(
                    "❌ Ошибка привязки аккаунта.\n"
                    "Попробуйте еще раз или обратитесь к администратору.",
                    parse_mode='Markdown'
                )
                return

            # Получаем информацию о подписке
            subscription = await sync_to_async(UserService.get_user_subscription)(django_user)

            if subscription:
                from django.utils import timezone
                days_left = (subscription.end_date - timezone.now()).days
                subscription_info = f"📋 **Тариф:** {subscription.plan.name} (осталось {days_left} дн.)"
            else:
                subscription_info = "📋 **Тариф:** Не активна"

            await update.message.reply_text(
                f"✅ **Успешная привязка!**\n\n"
                f"Telegram аккаунт привязан к Django: **{django_user.username}**\n"
                f"👤 Имя: {django_user.get_full_name() or 'Не указано'}\n"
                f"💰 Баланс: {profile.balance} ₽\n"
                f"🔔 Уведомления: {'✅ Включены' if profile.telegram_notifications else '❌ Выключены'}\n"
                f"{subscription_info}\n\n"
                f"Теперь вы можете управлять аккаунтом через бота!",
                parse_mode='Markdown'
            )

            logger.info(f"✅ User {user.id} привязан к Django аккаунту {django_user.username}")

        except Exception as e:
            logger.error(f"Ошибка в link_account_command: {e}")
            await update.message.reply_text("❌ Ошибка привязки аккаунта.")

    async def handle_registration_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопок регистрации"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data == "link_account":
            await self.show_link_dialog(query)
        else:
            await query.edit_message_text("⚙️ Команда в разработке")

    async def show_link_dialog(self, query):
        """Показать диалог привязки"""
        user = query.from_user

        # Генерируем код верификации
        code = await sync_to_async(UserService.generate_verification_code)(user.id)

        await query.edit_message_text(
            f"🔗 **Привязка аккаунта**\n\n"
            f"📱 **Ваш Telegram:**\n"
            f"• User ID: `{user.id}`\n"
            f"• Username: @{user.username or 'не указан'}\n"
            f"• Имя: {user.first_name or 'Не указано'}\n\n"
            f"🔐 **Код верификации:** `{code}`\n\n"
            f"**Способы привязки:**\n"
            f"1. На сайте: http://127.0.0.1:8000/profile/\n"
            f"2. Командой: `/link ваш_логин`\n\n"
            f"**Код действителен 10 минут**",
            parse_mode='Markdown'
        )

    def register_handlers(self, application):
        """Регистрация обработчиков"""
        # Команда привязки
        application.add_handler(CommandHandler("link", self.link_account_command))

        # Callback обработчик
        application.add_handler(CallbackQueryHandler(
            self.handle_registration_callback,
            pattern="^link_account$"
        ))

        logger.info("✅ Обработчики регистрации зарегистрированы")