import os
from datetime import timezone

import django
import logging

# ✅ Создаем логгер для команды списания
logger = logging.getLogger('dashboard.management.commands.deduct_daily_payments')


class Command(BaseCommand):
    help = 'Ежедневное списание за подписки'

    def handle(self, *args, **options):
        logger.info("💵 Начало ежедневного списания!")

        try:
            # Получаем текущий месяц и количество дней в нем
            today = timezone.now().date()
            days_in_month = self.get_days_in_month(today.year, today.month)

            # Находим активные подписки
            active_subscriptions = UserSubscription.objects.filter(
                is_active=True,
                end_date__gte=today
            )

            logger.info(f"💵 Найдено активных подписок: {active_subscriptions.count()}")

            charged_count = 0
            failed_count = 0

            for subscription in active_subscriptions:
                try:
                    # Получаем профиль пользователя
                    user_profile = UserProfile.objects.get(user=subscription.user)

                    # Рассчитываем дневную стоимость
                    daily_price = subscription.plan.calculate_daily_price(days_in_month)

                    # Проверяем достаточно ли средств
                    if user_profile.balance >= daily_price:
                        # Списание средств
                        user_profile.balance -= daily_price
                        user_profile.save()

                        # Создаем запись в истории операций
                        Transaction.objects.create(
                            user=subscription.user,
                            amount=-daily_price,
                            transaction_type='daily_charge',
                            status='completed',
                            description=f'💵 Ежедневное списание за подписку "{subscription.plan.name}"'
                        )

                        charged_count += 1
                        logger.info(f"💵 Списано {daily_price} руб. с пользователя {subscription.user.username}")

                    else:
                        # Недостаточно средств - деактивируем подписку
                        subscription.is_active = False
                        subscription.save()

                        Transaction.objects.create(
                            user=subscription.user,
                            amount=0,
                            transaction_type='subscription',
                            status='failed',
                            description=f'❌ Подписка "{subscription.plan.name}" деактивирована из-за недостатка средств'
                        )

                        failed_count += 1
                        logger.warning(f"❌ Недостаточно средств у {subscription.user.username}. Подписка деактивирована.")

                except UserProfile.DoesNotExist:
                    logger.error(f"❌ Профиль не найден для пользователя {subscription.user.username}")
                    continue
                except Exception as e:
                    logger.error(f"❌ Ошибка при списании с {subscription.user.username}: {str(e)}")
                    continue

            logger.info(f"💵 Ежедневное списание завершено. Успешно: {charged_count}, Ошибок: {failed_count} ")

            self.stdout.write(
                self.style.SUCCESS(
                    f'💵 Ежедневное списание завершено. Успешно: {charged_count}, Ошибок: {failed_count}'
                )
            )

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при выполнении списания: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'❌ Критическая ошибка: {str(e)}')
            )

    def get_days_in_month(self, year, month):
        """Возвращает количество дней в месяце"""
        if month == 12:
            return (timezone.datetime(year + 1, 1, 1) - timezone.datetime(year, month, 1)).days
        else:
            return (timezone.datetime(year, month + 1, 1) - timezone.datetime(year, month, 1)).days