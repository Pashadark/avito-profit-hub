"""
Обработчики профиля пользователя
Исправленная версия с правильной асинхронностью
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from asgiref.sync import sync_to_async

from apps.bot.keyboards import (
    get_profile_menu_keyboard,
    get_balance_keyboard,
    get_subscription_keyboard,
    get_items_keyboard,
    get_stats_keyboard
)
from apps.bot.services.user_service import UserService

logger = logging.getLogger('bot.handlers.profile')


class ProfileHandlers:
    """Обработчики профиля"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def handle_profile_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню профиля"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user = query.from_user

        logger.info(f"🔄 Обработка профиля: {callback_data} от {user.id}")

        if callback_data == "menu_profile":
            await self.show_profile_menu(query, user)
        elif callback_data == "profile_balance":
            await self.show_balance(query, user)
        elif callback_data == "profile_subscription":
            await self.show_subscription(query, user)
        elif callback_data == "profile_items":
            await self.show_items(query, user)
        elif callback_data == "profile_stats":
            await self.show_stats(query, user)
        else:
            await query.edit_message_text("⚙️ Команда в разработке")

    async def show_profile_menu(self, query, user):
        """Показать меню профиля"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if not profile:
            await query.edit_message_text(
                "❌ Сначала привяжите Telegram к аккаунту!\n\n"
                "Используйте команду /link или перейдите на сайт: "
                "http://127.0.0.1:8000/profile/"
            )
            return

        # Получаем информацию о профиле
        subscription = await sync_to_async(UserService.get_user_subscription)(profile.user)

        if subscription:
            from django.utils import timezone
            # ✅ ИСПРАВЛЕНО: вычисляем days_left через sync_to_async
            days_left = await sync_to_async(
                lambda: (subscription.end_date - timezone.now()).days
            )()
            subscription_text = f"🔔 Тариф: {subscription.plan.name} (осталось {days_left} дн.)"
        else:
            subscription_text = "🔔 Тариф: Не активна"

        profile_text = f"""
👤 **Мой профиль**

👤 **Пользователь:** {profile.user.username}
💰 **Баланс:** {profile.balance or 0} ₽
{subscription_text}

Выберите действие:
        """

        keyboard = get_profile_menu_keyboard()

        await query.edit_message_text(
            profile_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_balance(self, query, user):
        """Показать баланс"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if not profile:
            await query.edit_message_text("❌ Профиль не найден")
            return

        try:
            # ✅ ИСПРАВЛЕНО: Добавляем импорт Transaction внутри функции
            from apps.website.models import Transaction

            # Получаем транзакции через sync_to_async
            transactions = await sync_to_async(
                lambda: list(
                    Transaction.objects.filter(
                        user=profile.user,
                        status='completed'
                    ).order_by('-created_at')[:5]
                )
            )()

            transactions_text = ""
            for i, transaction in enumerate(transactions, 1):
                sign = "+" if transaction.amount > 0 else ""
                type_icons = {
                    'topup': '💳',
                    'subscription': '🔔',
                    'refund': '↩️',
                    'daily_charge': '📅'
                }
                icon = type_icons.get(transaction.transaction_type, '💼')
                transactions_text += f"{i}. {icon} {sign}{transaction.amount} ₽\n"

            balance_text = f"""
💰 **Баланс аккаунта**

💵 **Текущий баланс:** {profile.balance or 0} ₽

📋 **Последние операции:**
{transactions_text or '• Нет операций'}

💡 *Для пополнения баланса обратитесь к администратору*
            """

            keyboard = get_balance_keyboard()

            await query.edit_message_text(
                balance_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Ошибка показа баланса: {e}")
            await query.edit_message_text("❌ Ошибка загрузки баланса")

    async def show_subscription(self, query, user):
        """Показать подписку"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if not profile:
            await query.edit_message_text("❌ Профиль не найден")
            return

        subscription = await sync_to_async(UserService.get_user_subscription)(profile.user)

        if subscription:
            from django.utils import timezone
            # ✅ ИСПРАВЛЕНО: вычисляем days_left через sync_to_async
            days_left = await sync_to_async(
                lambda: (subscription.end_date - timezone.now()).days
            )()
            status_icon = "✅" if days_left > 7 else "⚠️" if days_left > 0 else "❌"

            subscription_text = f"""
🔔 **Информация о подписке**

{status_icon} **Статус:** Активна
📋 **Тариф:** {subscription.plan.name}
💳 **Тип:** {subscription.plan.plan_type}
💰 **Цена:** {subscription.plan.price} ₽/мес
📅 **Осталось дней:** {days_left}
⏰ **Заканчивается:** {subscription.end_date.strftime('%d.%m.%Y')}

💡 *Подписка активна и работает в штатном режиме*
            """
        else:
            subscription_text = """
🔔 **Информация о подписке**

❌ **Статус:** Не активна
📋 **Тариф:** Отсутствует
📅 **Осталось дней:** 0

💡 *Для активации подписки обратитесь к администратору*
            """

        keyboard = get_subscription_keyboard()

        await query.edit_message_text(
            subscription_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_items(self, query, user):
        """Показать товары"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if not profile:
            await query.edit_message_text("❌ Профиль не найден")
            return

        # ✅ ИСПРАВЛЕНО: все вызовы UserService уже обернуты в sync_to_async
        items = await sync_to_async(UserService.get_user_items)(profile.user, limit=5)

        if not items:
            items_text = "📭 **Найдено товаров:** 0\n\nЕще не найдено ни одного товара."
        else:
            items_text = "📦 **Последние найденные товары**\n\n"
            for i, item in enumerate(items, 1):
                profit_icon = "💰" if item.profit and item.profit > 0 else "⚡"
                profit_text = f"{profit_icon} Прибыль: {item.profit} ₽" if item.profit and item.profit > 0 else "🎯 Мониторинг"
                items_text += f"{i}. **{item.title}**\n"
                items_text += f"   💵 Цена: {item.price} ₽\n"
                items_text += f"   {profit_text}\n"
                items_text += f"   📅 {item.found_at.astimezone().strftime('%d.%m.%Y %H:%M')}\n\n"

        # ✅ ИСПРАВЛЕНО: получение статистики через sync_to_async
        stats = await sync_to_async(UserService.get_user_stats)(profile.user)

        if stats:
            stats_text = f"""
📊 **Статистика:**
• Всего найдено: {stats['total_items']}
• Выгодных: {stats['good_deals']}
• За неделю: {stats['week_items']}
• Эффективность: {stats['efficiency']}%
            """
        else:
            stats_text = "\n📊 Статистика недоступна"

        keyboard = get_items_keyboard()

        await query.edit_message_text(
            items_text + stats_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def show_stats(self, query, user):
        """Показать статистику"""
        profile = await sync_to_async(UserService.get_user_profile)(user.id)

        if not profile:
            await query.edit_message_text("❌ Профиль не найден")
            return

        stats = await sync_to_async(UserService.get_user_stats)(profile.user)

        if not stats:
            await query.edit_message_text("❌ Статистика недоступна")
            return

        stats_text = f"""
📊 **Детальная статистика**

📦 **Товары:**
• Всего найдено: {stats['total_items']}
• Выгодных предложений: {stats['good_deals']}
• За последние 7 дней: {stats['week_items']}
• Эффективность: {stats['efficiency']}%

💰 **Цены:**
• Средняя цена: {round(stats['price_stats']['avg_price'] or 0, 0)} ₽
• Максимальная цена: {stats['price_stats']['max_price'] or 0} ₽
• Минимальная цена: {stats['price_stats']['min_price'] or 0} ₽

📈 **Активность:**
• Парсер: {'🟢 Активен' if stats['week_items'] > 0 else '🟡 Низкая' if stats['total_items'] > 0 else '🔴 Не активен'}
• Рекомендация: {'Продолжайте в том же духе! ✅' if stats['week_items'] > 10 else 'Увеличьте количество запросов ⚡' if stats['week_items'] > 0 else 'Настройте поисковые запросы 🔧'}
        """

        keyboard = get_stats_keyboard()

        await query.edit_message_text(
            stats_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def register_handlers(self, application):
        """Регистрация обработчиков"""
        application.add_handler(CallbackQueryHandler(
            self.handle_profile_callback,
            pattern="^(menu_profile|profile_balance|profile_subscription|profile_items|profile_stats)$"
        ))

        logger.info("✅ Обработчики профиля зарегистрированы")