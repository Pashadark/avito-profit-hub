from django.core.management.base import BaseCommand
from dashboard.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Инициализация тарифных планов'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Базовый',
                'plan_type': 'Базовый',
                'price': 1800.00,
                'features': [
                    'Неограниченное количество ключевых слов',
                    'Автоматический парсинг',
                    'Уведомления в Telegram',
                    'Базовая статистика'
                ]
            },
            {
                'name': 'Стандарт',
                'plan_type': 'Стандарт',
                'price': 2500.00,
                'features': [
                    'Все функции Базового тарифа',
                    'Приоритетная поддержка',
                    'Расширенная статистика',
                    'История поисков'
                ]
            },
            {
                'name': 'Профи',
                'plan_type': 'Профи',
                'price': 3500.00,
                'features': [
                    'Все функции Стандарт тарифа',
                    'Мультипоиск',
                    'API доступ',
                    'Персональный менеджер',
                    'Кастомные отчеты'
                ]
            }
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Создан план: {plan.name} - {plan.price}₽/мес')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'🔄 Обновлен план: {plan.name} - {plan.price}₽/мес')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎯 ИТОГ: Создано {created_count}, Обновлено {updated_count} тарифных планов'
            )
        )