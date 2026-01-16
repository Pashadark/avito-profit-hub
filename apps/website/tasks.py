from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task
def smart_daily_charge_task():
    """Задача для умного ежедневного списания за подписки"""
    try:
        from django.core.management import call_command
        call_command('deduct_daily_payments')
        logger.info("✅ Умное ежедневное списание выполнено успешно")
        return "Умное списание завершено"
    except Exception as e:
        logger.error(f"❌ Ошибка умного списания: {e}")
        return f"Ошибка: {e}"


@shared_task
def subscription_health_check_task():
    """Задача для проверки здоровья подписок"""
    try:
        from dashboard.models import UserSubscription
        from django.utils import timezone

        # Деактивируем просроченные подписки
        expired_count = UserSubscription.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        ).update(is_active=False)

        if expired_count > 0:
            logger.warning(f"🔧 Деактивировано {expired_count} просроченных подписок")

        logger.info(f"✅ Проверка здоровья подписок выполнена")
        return f"Проверка здоровья: {expired_count} деактивировано"

    except Exception as e:
        logger.error(f"❌ Ошибка проверки здоровья подписок: {e}")
        return f"Ошибка: {e}"

@shared_task
def daily_backup_task():
    """Задача для ежедневного бэкапа"""
    try:
        call_command('daily_backup')
        logger.info("✅ Ежедневный бэкап выполнен успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка ежедневного бэкапа: {e}")


@shared_task
def clean_old_backups_task():
    """Задача для очистки старых бэкапов"""
    try:
        call_command('daily_backup', '--keep-days', '7')
        logger.info("✅ Очистка старых бэкапов выполнена")
    except Exception as e:
        logger.error(f"❌ Ошибка очистки бэкапов: {e}")


@shared_task
def database_replication_task():
    """Задача для репликации базы данных"""
    try:
        from dashboard.database_replication import DatabaseReplication

        replicator = DatabaseReplication()
        if replicator.sync_databases():
            logger.info("✅ Репликация базы данных выполнена")
        else:
            logger.error("❌ Ошибка репликации базы данных")
    except Exception as e:
        logger.error(f"❌ Ошибка репликации: {e}")