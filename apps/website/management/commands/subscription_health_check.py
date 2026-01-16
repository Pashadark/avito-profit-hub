from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import UserSubscription
from dashboard.utils.subscription_utils import SubscriptionManager
from django.contrib.auth.models import User
import logging

logger = logging.getLogger('subscription_health')


class Command(BaseCommand):
    help = 'Проверка здоровья подписок и уведомления'

    def handle(self, *args, **options):
        logger.info("🔧 === ПРОВЕРКА ЗДОРОВЬЯ ПОДПИСОК ===")

        # 1. Деактивируем просроченные подписки
        expired_count = UserSubscription.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        ).update(is_active=False)

        if expired_count > 0:
            logger.warning(f"🔧 Деактивировано {expired_count} просроченных подписок")

        # 2. Проверяем пользователей с низким балансом
        low_balance_users = []
        for user in User.objects.filter(subscriptions__is_active=True).distinct():
            info = SubscriptionManager.get_user_subscription_info(user)
            if info['has_active_subscription']:
                days_left = info['balance'] / info['daily_price'] if info['daily_price'] > 0 else 0

                if days_left < 3:
                    low_balance_users.append({
                        'username': user.username,
                        'balance': info['balance'],
                        'days_left': round(days_left, 1)
                    })
                    logger.warning(f"💰 Низкий баланс: {user.username} - {days_left:.1f} дней")

        # 3. Отчет
        self.stdout.write(self.style.SUCCESS(
            f"🔧 Проверка здоровья завершена: "
            f"{expired_count} просрочено, "
            f"{len(low_balance_users)} с низким балансом"
        ))

        if low_balance_users:
            self.stdout.write(self.style.WARNING("Пользователи с низким балансом:"))
            for user in low_balance_users:
                self.stdout.write(f"  👤 {user['username']}: {user['balance']}₽ ({user['days_left']} дней)")