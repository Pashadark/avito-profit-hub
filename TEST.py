#!/usr/bin/env python
"""
🐛 Debug скрипт для проверки ML категорий
"""

import os
import sys

# Добавляем корневую папку проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Настраиваем Django с правильными путями
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    import django

    django.setup()
    print("✅ Django запущен! Settings: core.settings")

    # Теперь импортируем модели
    from apps.website.models import FoundItem
    from django.db.models import Count, Q

    print(f"\n🔍 Проверяем данные в базе...")
    print("=" * 50)

    # 1. Сколько всего товаров
    total = FoundItem.objects.count()
    print(f"📊 Всего товаров: {total}")

    if total == 0:
        print("\n❌ БАЗА ПУСТАЯ! Вот почему нет категорий.")
        print("Запусти парсер или добавь тестовые данные.")
        sys.exit(0)

    # 2. Проверяем категории
    items_with_categories = FoundItem.objects.exclude(
        Q(category__isnull=True) | Q(category='')
    ).count()

    print(f"📊 Товаров с категориями: {items_with_categories}")

    # 3. Проверяем ML оценки
    items_with_ml = FoundItem.objects.filter(
        ml_freshness_score__isnull=False
    ).count()

    print(f"📊 Товаров с ML оценками: {items_with_ml}")

    # 4. Пробуем запрос из views
    print(f"\n🔍 Выполняем запрос категорий...")

    categories = FoundItem.objects.exclude(
        Q(category__isnull=True) | Q(category='')
    ).values('category').annotate(
        total_count=Count('id'),
        ml_count=Count('ml_freshness_score')
    ).order_by('-total_count')[:8]

    print(f"📋 Найдено категорий: {len(categories)}")

    if len(categories) == 0:
        print("\n⚠️ Категории не найдены! Показываем почему...")

        # Смотрим на первые 5 товаров
        sample_items = FoundItem.objects.all()[:5]
        print("\n📝 Первые 5 товаров:")
        for item in sample_items:
            print(f"  ID {item.id}: Категория='{item.category}', ML={item.ml_freshness_score}")

        # Смотрим все уникальные значения категорий
        all_cats = FoundItem.objects.values_list('category', flat=True).distinct()
        print(f"\n🎯 Все уникальные категории: {list(all_cats)}")

        # Проверяем, есть ли NULL или пустые строки
        null_cats = FoundItem.objects.filter(category__isnull=True).count()
        empty_cats = FoundItem.objects.filter(category='').count()
        print(f"\n📊 NULL категорий: {null_cats}, пустых строк: {empty_cats}")

    else:
        print("\n📊 Статистика по категориям:")
        for cat in categories:
            print(f"\n📁 {cat['category']}:")
            print(f"   Всего: {cat['total_count']}")
            print(f"   С ML: {cat['ml_count']}")
            print(f"   Без ML: {cat['total_count'] - cat['ml_count']}")

    # 5. Проверяем API endpoint
    print(f"\n🔍 Проверяем URL конфигурацию...")

    # Импортируем view чтобы посмотреть код
    try:
        from apps.website.ml_stats_views import api_ml_stats

        print("✅ Функция api_ml_stats найдена в ml_stats_views.py")

        # Смотрим на исходный код функции
        import inspect

        source = inspect.getsource(api_ml_stats)

        # Ищем проблемную строку с категориями
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'category_stats = FoundItem.objects.exclude' in line:
                print(f"\n🔧 Найдена строка запроса в views (строка ~{i + 1}):")
                print(f"   {line.strip()}")
                if i + 1 < len(lines):
                    print(f"   {lines[i + 1].strip()}")
                break

    except ImportError as e:
        print(f"❌ Не могу импортировать api_ml_stats: {e}")

    print("\n" + "=" * 50)
    print("🎯 ВЫВОД:")

    if len(categories) == 0:
        print("""
        ❗ ПРОБЛЕМА: В базе нет товаров с заполненными категориями.

        🔧 БЫСТРЫЙ ФИКС:
        1. Открой ml_stats_views.py
        2. Найди функцию api_ml_stats
        3. После запроса категорий добавь fallback:

        if len(categories) == 0:
            # Демо-данные для фронтенда
            categories = [
                {
                    'name': 'Электроника',
                    'accuracy': 82,
                    'total_predictions': 156,
                    'successful': 128,
                    'avg_ml': 0.85,
                    'ml_range': 0.35
                },
                {
                    'name': 'Одежда',
                    'accuracy': 75,
                    'total_predictions': 89,
                    'successful': 67,
                    'avg_ml': 0.72,
                    'ml_range': 0.28
                },
                {
                    'name': 'Автотовары',
                    'accuracy': 68,
                    'total_predictions': 42,
                    'successful': 29,
                    'avg_ml': 0.65,
                    'ml_range': 0.22
                }
            ]

        4. Сохрани и обнови страницу ML статистики.
        """)
    else:
        print("""
        ✅ Данные есть, но возможно проблема в:
        1. JS не правильно парсит ответ API
        2. Неправильный путь к API (проверь Network в DevTools)
        3. Ошибка в функции updateSuccessfulCategories в JS

        🔧 ЧЕКЛИСТ:
        1. Открой браузер, нажми F12 -> Network
        2. Обнови страницу ML статистики
        3. Найди запрос к /api/ml-stats/
        4. Посмотри Response - есть ли там successful_categories?
        5. Если нет - проблема в бэкенде (views.py)
        6. Если есть - проблема в фронтенде (JS)
        """)

except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback

    traceback.print_exc()

    print(f"\n🔧 Возможные решения:")
    print("1. Проверь структуру проекта: settings в core/settings.py")
    print("2. Убедись что apps.website.models импортируется правильно")
    print("3. Запусти через manage.py: python manage.py shell")
    print("   >>> from apps.website.models import FoundItem")
    print("   >>> FoundItem.objects.count()")