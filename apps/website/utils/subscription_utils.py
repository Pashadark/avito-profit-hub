from django.utils import timezone
from django.db import transaction
from ..models import UserProfile, UserSubscription, SubscriptionPlan, Transaction
import logging

# Создаем логгер для подписок
logger = logging.getLogger('subscriptions')


class SubscriptionManager:
    """Утилиты для управления подписками"""

    @staticmethod
    def can_user_use_parser(user):
        """
        Проверяет может ли пользователь использовать парсер
        Возвращает (bool, message)
        """
        try:
            profile = UserProfile.objects.get(user=user)

            # Проверяем активную подписку
            active_subscription = UserSubscription.objects.filter(
                user=user,
                is_active=True,
                end_date__gte=timezone.now()
            ).first()

            if not active_subscription:
                return False, "❌ Нет активной подписки. Пожалуйста, активируйте подписку для использования парсера."

            # Проверяем баланс
            daily_price = active_subscription.plan.daily_price
            if profile.balance < daily_price:
                return False, f"❌ Недостаточно средств на балансе. Требуется: {daily_price}₽/день. Пополните баланс для продолжения работы."

            return True, "✅ Доступ разрешен"

        except UserProfile.DoesNotExist:
            return False, "❌ Профиль пользователя не найден. Обратитесь в поддержку."
        except Exception as e:
            return False, f"❌ Ошибка проверки доступа: {str(e)}"

    @staticmethod
    def get_user_subscription_info(user):
        """Возвращает полную информацию о подписке пользователя"""
        try:
            profile = UserProfile.objects.get(user=user)
            subscription = UserSubscription.objects.filter(
                user=user,
                is_active=True,
                end_date__gte=timezone.now()
            ).select_related('plan').first()

            if subscription:
                daily_price = subscription.plan.daily_price
                can_use_parser = profile.balance >= daily_price
                days_remaining = subscription.days_remaining
                is_expired = subscription.is_expired
            else:
                daily_price = 0
                can_use_parser = False
                days_remaining = 0
                is_expired = True

            return {
                'has_active_subscription': subscription is not None,
                'subscription': subscription,
                'plan': subscription.plan if subscription else None,
                'balance': float(profile.balance),
                'daily_price': float(daily_price),
                'can_use_parser': can_use_parser,
                'days_remaining': days_remaining,
                'is_expired': is_expired,
                'required_balance': float(daily_price) if subscription else 0
            }
        except UserProfile.DoesNotExist:
            return {
                'has_active_subscription': False,
                'subscription': None,
                'plan': None,
                'balance': 0,
                'daily_price': 0,
                'can_use_parser': False,
                'days_remaining': 0,
                'is_expired': True,
                'required_balance': 0
            }

    @staticmethod
    def activate_subscription(user, plan_type, duration_days=30):
        """Активирует подписку для пользователя"""
        try:
            plan = SubscriptionPlan.objects.get(plan_type=plan_type, is_active=True)

            with transaction.atomic():
                # Деактивируем старые подписки
                UserSubscription.objects.filter(user=user, is_active=True).update(is_active=False)

                # Создаем новую подписку
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timezone.timedelta(days=duration_days),
                    is_active=True,
                    auto_renew=True
                )

            return True, subscription, "✅ Подписка успешно активирована"

        except SubscriptionPlan.DoesNotExist:
            return False, None, "❌ Тарифный план не найден"
        except Exception as e:
            return False, None, f"❌ Ошибка активации подписки: {str(e)}"

    @staticmethod
    def get_available_plans():
        """Возвращает список доступных тарифных планов"""
        return SubscriptionPlan.objects.filter(is_active=True).order_by('price')

    @staticmethod
    def check_and_deduct_daily_payment(user):
        """
        Проверяет и списывает ежедневный платеж для пользователя
        Возвращает (success, message)
        """
        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(user=user)
                subscription = UserSubscription.objects.filter(
                    user=user,
                    is_active=True,
                    end_date__gte=timezone.now()
                ).first()

                if not subscription:
                    return False, "Нет активной подписки"

                daily_price = subscription.plan.daily_price

                if profile.balance >= daily_price:
                    # Списание средств
                    profile.balance -= daily_price
                    profile.save()

                    # Создаем запись о транзакции
                    Transaction.objects.create(
                        user=user,
                        amount=daily_price,
                        transaction_type='daily_charge',
                        status='completed',
                        description=f'Ежедневное списание за подписку "{subscription.plan.name}"'
                    )

                    return True, f"Списано {daily_price}₽ за подписку"
                else:
                    # Деактивируем подписку
                    subscription.is_active = False
                    subscription.save()

                    return False, "Недостаточно средств, подписка деактивирована"

        except Exception as e:
            return False, f"Ошибка списания: {str(e)}"


def send_telegram_notification(chat_id, message, reply_markup=None):
    """
    Отправляет уведомление в личный чат пользователя через бота с поддержкой inline кнопок
    """
    try:
        import asyncio
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.error import TelegramError
        import logging

        logger = logging.getLogger('subscriptions')

        # Используем настройки из settings.py
        from django.conf import settings

        TELEGRAM_BOT_TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ Токен бота не настроен в settings.py")
            return False

        if not chat_id:
            logger.error("❌ Chat ID не указан")
            return False

        async def async_send_message():
            try:
                bot = Bot(token=TELEGRAM_BOT_TOKEN)

                # Проверяем что бот доступен
                bot_info = await bot.get_me()
                logger.info(f"✅ Бот: {bot_info.first_name} (@{bot_info.username})")

                # Отправляем сообщение в личный чат пользователя
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )

                logger.info(f"✅ Сообщение с кнопками отправлено в чат {chat_id}")
                return True

            except TelegramError as e:
                logger.error(f"❌ Ошибка Telegram для чата {chat_id}: {e}")
                return False
            except Exception as e:
                logger.error(f"❌ Ошибка отправки в чат {chat_id}: {e}")
                return False

        # Запускаем асинхронную отправку
        success = asyncio.run(async_send_message())
        return success

    except Exception as e:
        logger.error(f"❌ Критическая ошибка отправки Telegram: {e}")
        return False


def _format_subscription_message(notification_type, data, username, telegram_username):
    """
    Форматирует красивые сообщения для уведомлений о списаниях (без тегов)
    """
    from django.utils import timezone
    from datetime import timedelta
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Базовые данные
    amount = data.get('amount', 0)
    daily_price = data.get('daily_price', data.get('required_amount', 0))
    current_balance = data.get('current_balance', 0)
    subscription_name = data.get('subscription_name', '')
    days_remaining = data.get('days_remaining', 0)
    days_can_pay = data.get('days_can_pay', 0)

    # Форматируем числа
    amount_formatted = f"{amount:,.2f}₽".replace(',', ' ')
    daily_price_formatted = f"{daily_price:,.2f}₽".replace(',', ' ')
    balance_formatted = f"{current_balance:,.2f}₽".replace(',', ' ')

    # Информация о пользователе
    user_greeting = f"👋 <b>Привет, {username}!</b>"
    if telegram_username and telegram_username != username:
        user_greeting += f" (@{telegram_username})"

    # Эмодзи и заголовки для разных типов уведомлений
    notification_templates = {
        'successful_charge': {
            'header': "✅ <b>СПИСАНИЕ ПРОШЛО УСПЕШНО!</b>",
            'emoji': '💰',
            'lines': [
                user_greeting,
                "",
                f"💳 <b>Списано:</b> {amount_formatted}",
                f"📦 <b>Подписка:</b> {subscription_name}",
                f"💎 <b>Остаток на балансе:</b> {balance_formatted}",
                f"📅 <b>Следующее списание:</b> завтра в 00:01",
                "",
                f"💡 <b>Баланса хватит еще на:</b> {int(days_can_pay)} дней",
                f"📊 <b>Дней до конца подписки:</b> {days_remaining}"
            ]
        },
        'low_balance_warning': {
            'header': "⚠️ <b>ВНИМАНИЕ: НИЗКИЙ БАЛАНС!</b>",
            'emoji': '🔔',
            'lines': [
                user_greeting,
                "",
                f"💎 <b>Текущий баланс:</b> {balance_formatted}",
                f"💳 <b>Требуется для списания:</b> {daily_price_formatted}",
                f"📦 <b>Подписка:</b> {subscription_name}",
                f"📅 <b>Дата списания:</b> завтра в 00:01",
                "",
                f"⏳ <b>Баланса хватит еще на:</b> {int(days_can_pay)} дней",
                f"📊 <b>Дней до конца подписки:</b> {days_remaining}",
                "",
                "🔔 <b>РЕКОМЕНДУЕМ ПОПОЛНИТЬ БАЛАНС!</b>"
            ]
        },
        'subscription_deactivated': {
            'header': "❌ <b>ПОДПИСКА ДЕАКТИВИРОВАНА</b>",
            'emoji': '🚫',
            'lines': [
                user_greeting,
                "",
                f"📦 <b>Подписка:</b> {subscription_name}",
                f"💳 <b>Причина:</b> Недостаточно средств на балансе",
                f"💰 <b>Не хватило:</b> {data.get('missing_amount', 0):.2f}₽",
                f"💎 <b>Текущий баланс:</b> {balance_formatted}",
                "",
                "🔧 <b>ДЛЯ ВОССТАНОВЛЕНИЯ:</b>",
                "1. Пополните баланс",
                "2. Активируйте подписку в личном кабинете",
                "",
                f"💳 <b>Требуемая сумма:</b> {daily_price_formatted}"
            ]
        },
        'health_check': {
            'header': "🔔 <b>ПРОВЕРКА ПОДПИСКИ</b>",
            'emoji': '📊',
            'lines': [
                user_greeting,
                "",
                f"📦 <b>Подписка:</b> {subscription_name}",
                f"💎 <b>Баланс:</b> {balance_formatted}",
                f"💰 <b>Дневная стоимость:</b> {daily_price_formatted}",
                f"📅 <b>Осталось дней подписки:</b> {days_remaining}",
                "",
                f"⏳ <b>Баланса хватит еще на:</b> {int(days_can_pay)} дней",
                f"📈 <b>Статус:</b> {'✅ Активна' if days_remaining > 0 else '❌ Истекла'}"
            ]
        }
    }

    if notification_type not in notification_templates:
        return None, None

    template = notification_templates[notification_type]

    # Собираем сообщение
    message_lines = []
    message_lines.append(template['header'])
    message_lines.append("")
    message_lines.extend(template['lines'])

    # Создаем inline клавиатуру
    keyboard = []

    # Для уведомлений о деактивации добавляем кнопку "Продлить"
    if notification_type == 'subscription_deactivated':
        keyboard.append([
            InlineKeyboardButton("🔄 Продлить подписку", callback_data="renew_subscription"),
            InlineKeyboardButton("👤 Профиль", url="http://192.168.3.15:8000/profile/")
        ])
    # Для уведомлений о низком балансе добавляем кнопку "Пополнить"
    elif notification_type == 'low_balance_warning':
        keyboard.append([
            InlineKeyboardButton("💰 Пополнить баланс", callback_data="topup_balance"),
            InlineKeyboardButton("👤 Профиль", url="http://192.168.3.15:8000/profile/")
        ])
    # Для остальных уведомлений стандартные кнопки
    else:
        keyboard.append([
            InlineKeyboardButton("📊 Статистика", callback_data="show_stats"),
            InlineKeyboardButton("👤 Профиль", url="http://192.168.3.15:8000/profile/")
        ])

    # Добавляем кнопку "Подробнее" для всех типов
    keyboard.append([
        InlineKeyboardButton("ℹ️ Подробнее", url="http://192.168.3.15:8000/profile/")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    return "\n".join(message_lines), reply_markup


def send_subscription_notification(user, notification_type, data=None):
    """
    Отправляет красивые уведомления о списаниях в личный чат пользователя с inline кнопками
    """
    try:
        import logging

        logger = logging.getLogger('subscriptions')

        # Получаем профиль пользователя
        from ..models import UserProfile
        try:
            profile = UserProfile.objects.get(user=user)

            # Проверяем привязку Telegram
            if not profile.telegram_chat_id or not profile.telegram_verified:
                logger.info(f"📱 Пользователь {user.username} не привязал Telegram, уведомление не отправлено")
                return False

            chat_id = profile.telegram_chat_id
            telegram_username = profile.telegram_username or user.username

            logger.info(f"📱 Отправка уведомления пользователю {user.username} (Chat ID: {chat_id})")

        except UserProfile.DoesNotExist:
            logger.warning(f"📱 Профиль пользователя {user.username} не найден")
            return False

        # Форматируем красивое сообщение и получаем клавиатуру
        message, reply_markup = _format_subscription_message(notification_type, data or {}, user.username,
                                                             telegram_username)

        if not message:
            logger.error(f"❌ Не удалось сформировать сообщение для типа: {notification_type}")
            return False

        # Отправляем уведомление в личный чат пользователя с кнопками
        success = send_telegram_notification(chat_id, message, reply_markup)

        if success:
            logger.info(
                f"✅ Уведомление {notification_type} с кнопками отправлено пользователю {user.username} (Chat ID: {chat_id})")
        else:
            logger.error(
                f"❌ Ошибка отправки уведомления {notification_type} пользователю {user.username} (Chat ID: {chat_id})")

        return success

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в send_subscription_notification: {e}")
        return False

def send_test_subscription_notification(user, notification_type='successful_charge'):
    """
    Функция для тестирования уведомлений
    """
    try:
        from ..models import UserProfile
        import random

        # Тестовые данные
        test_data = {
            'amount': 116.67,
            'daily_price': 116.67,
            'current_balance': random.uniform(100, 2000),
            'subscription_name': 'PRO Тариф',
            'days_remaining': random.randint(1, 30),
            'days_can_pay': random.randint(1, 20),
            'missing_amount': random.uniform(10, 100),
            'required_amount': 116.67
        }

        return send_subscription_notification(user, notification_type, test_data)

    except Exception as e:
        logger.error(f"❌ Ошибка тестового уведомления: {e}")
        return False


def deduct_daily_payments():
    """
    Ежедневное списание платежей за подписки с уведомлениями
    Возвращает True если списание прошло успешно
    """
    try:
        from django.contrib.auth.models import User
        from ..models import UserSubscription, UserProfile, Transaction
        from django.utils import timezone
        from datetime import timedelta

        logger.info("💰 === НАЧАЛО ЕЖЕДНЕВНОГО СПИСАНИЯ ===")

        # Находим активные подписки
        active_subscriptions = UserSubscription.objects.filter(
            is_active=True,
            end_date__gte=timezone.now()
        ).select_related('user', 'plan')

        logger.info(f"💰 Найдено активных подписок: {active_subscriptions.count()}")

        successful_charges = 0
        deactivated_subscriptions = 0
        errors = 0
        notifications_to_send = []

        for subscription in active_subscriptions:
            try:
                user = subscription.user
                profile = UserProfile.objects.get(user=user)
                daily_price = subscription.plan.daily_price
                days_remaining = (subscription.end_date - timezone.now()).days
                days_can_pay = int(profile.balance / daily_price) if daily_price > 0 else 0
                next_charge = (timezone.now() + timedelta(days=1)).strftime('%d.%m.%Y в 00:01')

                # Проверяем достаточно ли средств
                if profile.balance >= daily_price:
                    # Списание средств
                    old_balance = profile.balance
                    profile.balance -= daily_price
                    profile.save()

                    # Создаем запись о транзакции
                    Transaction.objects.create(
                        user=user,
                        amount=-daily_price,
                        description=f"💰 Ежедневное списание за подписку \"{subscription.plan.name}\""
                    )

                    successful_charges += 1
                    logger.info(f"✅ Списано {daily_price}₽ с {user.username} (остаток: {profile.balance:.2f}₽)")

                    # Добавляем уведомление об успешном списании
                    notifications_to_send.append({
                        'user': user,
                        'type': 'successful_charge',
                        'data': {
                            'amount': daily_price,
                            'subscription_name': subscription.plan.name,
                            'current_balance': profile.balance,
                            'days_remaining': days_remaining,
                            'days_can_pay': days_can_pay
                        }
                    })

                else:
                    # Недостаточно средств - деактивируем подписку
                    old_balance = profile.balance
                    subscription.is_active = False
                    subscription.save()
                    deactivated_subscriptions += 1
                    logger.warning(f"❌ Недостаточно средств у {user.username}. Подписка деактивирована.")

                    # Добавляем уведомление о деактивации
                    notifications_to_send.append({
                        'user': user,
                        'type': 'subscription_deactivated',
                        'data': {
                            'subscription_name': subscription.plan.name,
                            'missing_amount': daily_price - old_balance,
                            'required_amount': daily_price,
                            'current_balance': old_balance
                        }
                    })

            except Exception as e:
                errors += 1
                logger.error(f"❌ Ошибка списания для {subscription.user.username}: {e}")

        # Отправляем все уведомления
        notification_results = {'sent': 0, 'failed': 0}
        for notification in notifications_to_send:
            success = send_subscription_notification(
                user=notification['user'],
                notification_type=notification['type'],
                data=notification['data']
            )

            if success:
                notification_results['sent'] += 1
            else:
                notification_results['failed'] += 1

        logger.info(
            f"📱 Уведомления: отправлено {notification_results['sent']}, ошибок {notification_results['failed']}")

        logger.info("💰 === ЕЖЕДНЕВНОЕ СПИСАНИЕ ЗАВЕРШЕНО ===")
        logger.info(f"✅ Успешных списаний: {successful_charges}")
        logger.info(f"❌ Деактивировано подписок: {deactivated_subscriptions}")
        logger.info(f"⚠️ Ошибок: {errors}")

        return successful_charges > 0 or deactivated_subscriptions > 0

    except Exception as e:
        logger.error(f"❌ Критическая ошибка списания: {e}")
        return False


def check_subscription_health():
    """Проверка здоровья подписок с уведомлениями"""
    try:
        from django.contrib.auth.models import User
        from ..models import UserSubscription, UserProfile

        logger.info("🔧 === ПРОВЕРКА ЗДОРОВЬЯ ПОДПИСОК ===")

        notifications_to_send = []

        # Проверяем подписки с истекающим сроком (менее 3 дней)
        warning_date = timezone.now() + timezone.timedelta(days=3)
        expiring_subscriptions = UserSubscription.objects.filter(
            is_active=True,
            end_date__lte=warning_date,
            end_date__gte=timezone.now()
        ).select_related('user', 'plan')

        logger.info(f"🔧 Подписки истекают в течение 3 дней: {expiring_subscriptions.count()}")

        for subscription in expiring_subscriptions:
            days_remaining = (subscription.end_date - timezone.now()).days
            logger.warning(f"⚠️ Подписка {subscription.user.username} истекает через {days_remaining} дней")

        # Проверяем подписки с низким балансом
        low_balance_users = []
        active_subscriptions = UserSubscription.objects.filter(
            is_active=True,
            end_date__gte=timezone.now()
        ).select_related('user', 'plan')

        for subscription in active_subscriptions:
            try:
                profile = UserProfile.objects.get(user=subscription.user)
                daily_price = subscription.plan.daily_price
                days_remaining = (subscription.end_date - timezone.now()).days

                # Если баланса хватит меньше чем на 5 дней
                if profile.balance < daily_price * 5:
                    days_can_pay = int(profile.balance / daily_price) if daily_price > 0 else 0
                    user_info = {
                        'user': subscription.user.username,
                        'balance': profile.balance,
                        'daily_price': daily_price,
                        'days_remaining': days_remaining,
                        'days_can_pay': days_can_pay
                    }
                    low_balance_users.append(user_info)

                    # Добавляем уведомление о низком балансе
                    notifications_to_send.append({
                        'user': subscription.user,
                        'type': 'low_balance_warning',
                        'data': {
                            'current_balance': profile.balance,
                            'required_amount': daily_price,
                            'subscription_name': subscription.plan.name,
                            'days_remaining': days_remaining,
                            'days_can_pay': days_can_pay
                        }
                    })

            except Exception as e:
                logger.error(f"❌ Ошибка проверки баланса для {subscription.user.username}: {e}")

        logger.info(f"🔧 Пользователи с низким балансом: {len(low_balance_users)}")

        for user_info in low_balance_users:
            logger.warning(f"⚠️ Низкий баланс: {user_info['user']} - {user_info['balance']:.2f}₽ "
                           f"(хватит на {user_info['days_can_pay']} дней)")

        # Отправляем уведомления о низком балансе
        notification_results = {'sent': 0, 'failed': 0}
        for notification in notifications_to_send:
            success = send_subscription_notification(
                user=notification['user'],
                notification_type=notification['type'],
                data=notification['data']
            )

            if success:
                notification_results['sent'] += 1
            else:
                notification_results['failed'] += 1

        logger.info(
            f"📱 Уведомления о низком балансе: отправлено {notification_results['sent']}, ошибок {notification_results['failed']}")

        # Проверяем просроченные подписки
        expired_subscriptions = UserSubscription.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        )

        if expired_subscriptions.exists():
            logger.warning(f"🔧 Найдено просроченных подписок: {expired_subscriptions.count()}")
            for subscription in expired_subscriptions:
                logger.warning(f"❌ Просроченная подписка: {subscription.user.username}")

        logger.info("🔧 === ПРОВЕРКА ЗДОРОВЬЯ ЗАВЕРШЕНА ===")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка проверки здоровья подписок: {e}")
        return False