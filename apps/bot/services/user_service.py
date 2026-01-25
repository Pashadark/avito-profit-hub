"""
Сервисные функции для работы с пользователями (исправленная версия)
"""
import logging

logger = logging.getLogger('bot.services.user')


class UserService:
    """Сервис для работы с пользователями с ленивой загрузкой моделей"""

    @staticmethod
    def _get_user_model():
        """Ленивая загрузка User модели"""
        from django.contrib.auth import get_user_model
        return get_user_model()

    @staticmethod
    def _get_user_profile_model():
        """Ленивая загрузка UserProfile"""
        from apps.website.models import UserProfile
        return UserProfile

    @staticmethod
    def _get_user_subscription_model():
        """Ленивая загрузка UserSubscription"""
        from apps.website.models import UserSubscription
        return UserSubscription

    @staticmethod
    def _get_found_item_model():
        """Ленивая загрузка FoundItem"""
        from apps.website.models import FoundItem
        return FoundItem

    @staticmethod
    def _get_transaction_model():
        """Ленивая загрузка Transaction"""
        from apps.website.models import Transaction
        return Transaction

    @staticmethod
    def get_user_profile(telegram_user_id):
        """Получить профиль пользователя по Telegram ID"""
        try:
            UserProfile = UserService._get_user_profile_model()
            return UserProfile.objects.filter(
                telegram_user_id=telegram_user_id,
                telegram_verified=True
            ).select_related('user').first()  # 🔥 ДОБАВИЛ select_related
        except Exception as e:
            logger.error(f"Ошибка получения профиля: {e}")
            return None

    @staticmethod
    def get_user_subscription(user):
        """Получить активную подписку пользователя"""
        try:
            UserSubscription = UserService._get_user_subscription_model()
            from django.utils import timezone
            return UserSubscription.objects.filter(
                user=user,
                is_active=True,
                end_date__gte=timezone.now()
            ).select_related('plan').first()
        except Exception as e:
            logger.error(f"Ошибка получения подписки: {e}")
            return None

    @staticmethod
    def get_user_items(user, limit=10):
        """Получить товары пользователя"""
        try:
            FoundItem = UserService._get_found_item_model()
            return FoundItem.objects.filter(
                search_query__user=user
            ).order_by('-found_at')[:limit]
        except Exception as e:
            logger.error(f"Ошибка получения товаров: {e}")
            return []

    @staticmethod
    def get_user_stats(user):
        """Получить статистику пользователя"""
        try:
            FoundItem = UserService._get_found_item_model()
            from django.utils import timezone
            from django.db.models import Avg, Max, Min

            total_items = FoundItem.objects.filter(search_query__user=user).count()
            good_deals = FoundItem.objects.filter(search_query__user=user, profit__gt=0).count()

            # Статистика за неделю
            week_ago = timezone.now() - timezone.timedelta(days=7)
            week_items = FoundItem.objects.filter(
                search_query__user=user,
                found_at__gte=week_ago
            ).count()

            # Статистика цен
            price_stats = FoundItem.objects.filter(search_query__user=user).aggregate(
                avg_price=Avg('price'),
                max_price=Max('price'),
                min_price=Min('price')
            )

            return {
                'total_items': total_items,
                'good_deals': good_deals,
                'week_items': week_items,
                'price_stats': price_stats,
                'efficiency': round((good_deals / total_items * 100) if total_items > 0 else 0, 1)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None

    @staticmethod
    def get_user_transactions(user, limit=5):
        """Получить транзакции пользователя"""
        try:
            Transaction = UserService._get_transaction_model()
            return Transaction.objects.filter(
                user=user,
                status='completed'
            ).order_by('-created_at')[:limit]
        except Exception as e:
            logger.error(f"Ошибка получения транзакций: {e}")
            return []

    @staticmethod
    def generate_verification_code(telegram_user_id):
        """Генерация кода верификации"""
        import random
        try:
            User = UserService._get_user_model()
            UserProfile = UserService._get_user_profile_model()
            from django.utils import timezone

            # Находим или создаем временный профиль
            temp_profile, created = UserProfile.objects.get_or_create(
                telegram_user_id=telegram_user_id,
                defaults={
                    'user': User.objects.first(),
                    'telegram_verified': False
                }
            )

            # Генерируем код
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            temp_profile.telegram_verification_code = code
            temp_profile.telegram_verification_expires = timezone.now() + timezone.timedelta(minutes=10)
            temp_profile.save()

            logger.info(f"✅ Сгенерирован код верификации {code} для user_id {telegram_user_id}")
            return code

        except Exception as e:
            logger.error(f"Ошибка генерации кода: {e}")
            return "000000"

    @staticmethod
    def link_telegram_account(django_username, telegram_user_id, telegram_username):
        """Привязать Telegram к аккаунту Django"""
        try:
            User = UserService._get_user_model()
            UserProfile = UserService._get_user_profile_model()

            # Находим пользователя Django
            django_user = User.objects.get(username=django_username)

            # Создаем или обновляем профиль
            profile, created = UserProfile.objects.get_or_create(
                user=django_user,
                defaults={
                    'telegram_user_id': telegram_user_id,
                    'telegram_username': telegram_username,
                    'telegram_verified': True
                }
            )

            if not created:
                # Обновляем существующий профиль
                profile.telegram_user_id = telegram_user_id
                profile.telegram_username = telegram_username
                profile.telegram_verified = True
                profile.save()

            logger.info(f"✅ Привязан Telegram {telegram_user_id} к Django {django_username}")
            return profile

        except User.DoesNotExist:
            logger.error(f"Пользователь Django не найден: {django_username}")
            return None
        except Exception as e:
            logger.error(f"Ошибка привязки аккаунта: {e}")
            return None