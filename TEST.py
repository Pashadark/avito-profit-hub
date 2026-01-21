# fix_main_parser.py
import os
import re
import shutil


def fix_selenium_parser():
    """Фиксим главный парсер selenium_parser.py"""
    file_path = 'apps/parsing/utils/selenium_parser.py'

    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return False

    print(f"🔧 Исправляем: {file_path}")

    # Создаем бэкап
    backup_path = file_path + '.backup'
    shutil.copy2(file_path, backup_path)
    print(f"💾 Бэкап создан: {backup_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Комментируем импорты оптимизатора
    bad_imports = [
        'from apps.parsing.ai.query_optimizer import',
        'from apps.parsing.utils.freshness_query_optimizer import',
        'import QueryOptimizer',
        'import FreshnessQueryOptimizer'
    ]

    for bad_import in bad_imports:
        if bad_import in content:
            content = content.replace(bad_import, f'# УДАЛЕНО {bad_import}')
            print(f"❌ Закомментирован: {bad_import}")

    # 2. Добавляем импорт простого обработчика
    if 'simple_query_handler' not in content:
        # Находим куда вставить импорт
        import_match = re.search(r'^from apps\.parsing\.utils\..*?import', content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            simple_import = '\nfrom apps.parsing.utils.simple_query_handler import get_simple_queries  # Простая логика запросов'
            content = content[:insert_pos] + simple_import + content[insert_pos:]
            print("✅ Добавлен импорт simple_query_handler")

    # 3. Находим и фиксим вызовы оптимизатора
    # Ищем где используется оптимизация запросов
    optimizer_calls = [
        # Паттерны для поиска
        r'optimized_queries\s*=.*optimize_queries',
        r'await.*query_optimizer',
        r'🎯 AI-ОПТИМИЗИРОВАННЫЕ ЗАПРОСЫ',
        r'query_optimizer\.optimize_queries',
    ]

    replacements_made = 0

    # Заменяем оптимизацию на простые запросы
    for pattern in optimizer_calls:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            print(f"🔍 Найден вызов оптимизатора: {match.group()[:50]}...")

            # Простая замена
            if 'optimize_queries' in match.group():
                # Находим строку полностью
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.end())
                full_line = content[line_start:line_end]

                # Заменяем строку
                new_line = '# ' + full_line + '  # УДАЛЕНО - используем простые запросы\n' + \
                           '                optimized_queries = get_simple_queries(keywords)'

                content = content[:line_start] + new_line + content[line_end:]
                print(f"✅ Исправлена строка: {full_line[:50]}...")
                replacements_made += 1
                break  # Выходим после первой замены

    # 4. Если не нашли через паттерны, ищем вручную
    if replacements_made == 0:
        print("🔍 Ищем вручную строки с оптимизацией...")

        # Проходим по строкам
        lines = content.split('\n')
        new_lines = []

        for i, line in enumerate(lines):
            if 'optimize_queries' in line or 'query_optimizer' in line:
                print(f"🔧 Исправляем строку {i + 1}: {line[:60]}...")
                # Комментируем старую строку
                new_lines.append('# ' + line + '  # УДАЛЕНО - AI оптимизатор')
                # Добавляем новую строку
                new_lines.append('                optimized_queries = get_simple_queries(keywords)  # Простые запросы')
                replacements_made += 1
            else:
                new_lines.append(line)

        content = '\n'.join(new_lines)

    # 5. Заменяем AI оптимизированные на простые
    content = content.replace('🎯 AI-ОПТИМИЗИРОВАННЫЕ ЗАПРОСЫ', '🎯 ПРОСТЫЕ ЗАПРОСЫ')

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\n✅ Файл исправлен! Внесено изменений: {replacements_made}")
        print(f"💾 Бэкап сохранен: {backup_path}")

        # Показываем изменения
        print("\n📝 Пример исправления:")
        print("   БЫЛО: optimized_queries = await query_optimizer.optimize_queries(keywords)")
        print("   СТАЛО: optimized_queries = get_simple_queries(keywords)")
        return True
    else:
        print("ℹ️ Изменений не потребовалось")
        return False


def show_fixes():
    """Показываем что было исправлено"""
    print("\n" + "=" * 60)
    print("🎯 ИСПРАВЛЕНИЯ В SELENIUM_PARSER.PY:")
    print("=" * 60)

    print("1. ❌ Удалены импорты AI оптимизатора")
    print("2. ✅ Добавлен импорт simple_query_handler")
    print("3. 🔧 Заменены вызовы optimize_queries() на get_simple_queries()")
    print("4. 🎯 'AI-ОПТИМИЗИРОВАННЫЕ ЗАПРОСЫ' → 'ПРОСТЫЕ ЗАПРОСЫ'")

    print("\n📝 Теперь логи будут показывать:")
    print("   🎯 ПРОСТЫЕ ЗАПРОСЫ:")
    print("   - 'iphone 12'")
    print("   - 'iphone 13'")
    print("   - 'iphone 14'")
    print("\n   Вместо этого бреда:")
    print("   🎯 AI-ОПТИМИЗИРОВАННЫЕ ЗАПРОСЫ:")
    print("   - 'только что iphone 12'")
    print("   - 'дневная iphone 13'")
    print("   - 'сегодня iphone 14'")

    print("=" * 60)


if __name__ == "__main__":
    print("🔧 ФИКС ГЛАВНОГО ПАРСЕРА SELENIUM_PARSER.PY")
    print("=" * 60)

    success = fix_selenium_parser()

    if success:
        show_fixes()

        print("\n🚀 Запускай парсер и проверяй:")
        print("   cd C:\\Users\\pasahdark\\PycharmProjects\\avito_profit_hub")
        print("   .venv\\Scripts\\python.exe run.py")
        print("\nВыбери опцию 1 и смотри логи - не должно быть 'только что', 'сегодня'!")
    else:
        print("❌ Не удалось исправить файл")