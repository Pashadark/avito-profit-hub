from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import logging
from apps.website.models import UserProfile, UserSubscription, Transaction, SubscriptionPlan

logger = logging.getLogger('subscriptions')


class Command(BaseCommand):
    help = 'Ежедневное списание средств за активные подписки'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет списано без реального списания',
        )
        parser.add_argument(
            '--details', '-d',
            action='store_true',
            help='Подробный вывод (детали по каждой подписке)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        details = options.get('details', False)

        # Начало процесса
        logger.info("=" * 60)
        logger.info("💰  ЕЖЕДНЕВНОЕ СПИСАНИЕ ЗА ПОДПИСКИ")
        logger.info("=" * 60)

        if dry_run:
            logger.info("🔍 РЕЖИМ ПРОСМОТРА (без реального списания)")

        today = timezone.now()

        # Находим активные подписки
        active_subscriptions = UserSubscription.objects.filter(
            is_active=True,
            end_date__gte=today
        ).select_related('plan', 'user')

        total_subs = active_subscriptions.count()

        # Детальная статистика
        logger.info("📊 СТАТИСТИКА:")
        logger.info(f"   • 📋 Всего подписок: {total_subs}")

        # Группировка по планам
        plan_stats = {}
        for sub in active_subscriptions:
            plan_name = sub.plan.name
            plan_stats[plan_name] = plan_stats.get(plan_name, 0) + 1

        for plan_name, count in plan_stats.items():
            logger.info(f"   • 📝 {plan_name}: {count}")

        charged_count = 0
        deactivated_count = 0
        errors_count = 0
        total_charged = Decimal('0')
        users_processed = []

        # Обработка каждой подписки
        logger.info("🔄 ОБРАБОТКА ПОДПИСОК:")

        for subscription in active_subscriptions:
            try:
                with transaction.atomic():
                    user_profile = UserProfile.objects.select_for_update().get(
                        user=subscription.user
                    )

                    plan = subscription.plan
                    daily_price = plan.daily_price
                    user = subscription.user.username

                    # Для details режима
                    if details:
                        logger.info(f"   👤 {user}: {plan.name} - {daily_price}₽/день (баланс: {user_profile.balance}₽)")

                    if dry_run:
                        status = "✅ ДОСТАТОЧНО" if user_profile.balance >= daily_price else "❌ НЕДОСТАТОЧНО"
                        logger.info(f"   💰 ПРОВЕРКА: {user} - {status}")
                        continue

                    # Проверяем достаточно ли средств
                    if user_profile.balance >= daily_price:
                        # Списание средств
                        user_profile.balance -= daily_price
                        user_profile.save()

                        # Создаем запись о транзакции
                        Transaction.objects.create(
                            user=subscription.user,
                            amount=daily_price,
                            transaction_type='daily_charge',
                            status='completed',
                            description=f'💰 Ежедневное списание за подписку "{plan.name}"'
                        )

                        charged_count += 1
                        total_charged += daily_price
                        users_processed.append(f"✅ {user}: -{daily_price}₽ (остаток: {user_profile.balance}₽)")

                        if details:
                            logger.info(f"   ✅ {user}: списано {daily_price}₽")

                    else:
                        # Недостаточно средств - деактивируем подписку
                        subscription.is_active = False
                        subscription.save()

                        # Создаем запись о деактивации
                        Transaction.objects.create(
                            user=subscription.user,
                            amount=0,
                            transaction_type='subscription',
                            status='failed',
                            description=f'❌ Подписка "{plan.name}" деактивирована - недостаточно средств'
                        )

                        deactivated_count += 1
                        users_processed.append(
                            f"❌ {user}: подписка отключена (баланс: {user_profile.balance}₽ < {daily_price}₽)")

                        if details:
                            logger.warning(f"   ⚠️ {user}: недостаточно средств, подписка отключена")

            except UserProfile.DoesNotExist:
                errors_count += 1
                error_msg = f"❌ {subscription.user.username}: профиль не найден"
                logger.error(error_msg)
                users_processed.append(error_msg)
            except Exception as e:
                errors_count += 1
                error_msg = f"❌ {subscription.user.username}: ошибка - {str(e)}"
                logger.error(error_msg)
                users_processed.append(error_msg)

        # Итоговый отчет
        logger.info("=" * 60)
        logger.info("📈 ИТОГОВАЯ СТАТИСТИКА:")
        logger.info("=" * 60)

        if dry_run:
            logger.info("📋 РЕЗУЛЬТАТ ПРОВЕРКИ:")
            logger.info(f"   • 🔍 Проверено подписок: {total_subs}")

            # Анализ финансов
            sufficient = 0
            insufficient = 0

            for sub in active_subscriptions:
                user_profile = UserProfile.objects.filter(user=sub.user).first()
                if user_profile and user_profile.balance >= sub.plan.daily_price:
                    sufficient += 1
                else:
                    insufficient += 1

            logger.info(f"   • ✅ Достаточно средств: {sufficient}")
            logger.info(f"   • ❌ Недостаточно средств: {insufficient}")

            if insufficient > 0:
                logger.warning(f"   ⚠️ {insufficient} подписок будут отключены при реальном списании")
        else:
            logger.info("💰 ФИНАНСОВЫЕ РЕЗУЛЬТАТЫ:")
            logger.info(f"   • ✅ Успешных списаний: {charged_count}")
            if charged_count > 0:
                logger.info(f"   • 💸 Общая сумма: {total_charged}₽")
            logger.info(f"   • ❌ Деактивировано подписок: {deactivated_count}")
            logger.info(f"   • ⚠️ Ошибок обработки: {errors_count}")

            # Дополнительная аналитика
            if users_processed and details:
                logger.info("📋 ДЕТАЛИ ПО ПОЛЬЗОВАТЕЛЯМ:")
                for user_info in users_processed:
                    logger.info(f"   • {user_info}")

            # Сводка
            logger.info("🎯 СВОДКА:")
            success_rate = (charged_count / total_subs * 100) if total_subs > 0 else 0
            logger.info(f"   • 📊 Успешность: {success_rate:.1f}% ({charged_count}/{total_subs})")

            if deactivated_count > 0:
                logger.warning(f"   ⚠️ {deactivated_count} пользователей потеряют доступ к парсеру")

        logger.info("=" * 60)

        if not dry_run:
            if errors_count == 0 and deactivated_count == 0:
                logger.info("🎉 ВСЕ СПИСАНИЯ УСПЕШНО ВЫПОЛНЕНЫ!")
            elif deactivated_count > 0:
                logger.warning("⚠️ НЕКОТОРЫЕ ПОДПИСКИ БЫЛИ ОТКЛЮЧЕНЫ")
            else:
                logger.info("✅ ПРОЦЕСС ЗАВЕРШЕН")

        logger.info("=" * 60)