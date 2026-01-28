"""
Скрипт для поиска конкретных проблемных строк из логов
"""

import re
from pathlib import Path

# Конкретные проблемные строки из твоего лога
PROBLEM_PATTERNS = [
    "⏰ Таймер-менеджер инициализирован",
    "✅ Менеджер настроек инициализирован",
    "🧠 МОЗГ СИСТЕМЫ инициализирован",
    "🧠 Инициализирован Advanced ML Predictor",
    "🚀 Инициализация ML модели",
    "🔄 Запуск полной инициализации моделей",
    "🕒 Предсказатель времени публикации инициализирован",
    "✅ FreshnessQueryOptimizer отключен",
    "🔔 Инициализирована умная система уведомлений",
    "🚀 Инициализирован расширенный кэш с AI-фичами",
    "❤️ Инициализирован монитор здоровья системы",
    "🚀 СУПЕР-ПАРСЕР С AI-ФИЧАМИ И ПРИОРИТЕТОМ СВЕЖЕСТИ ИНИЦИАЛИЗИРОВАН",
    "ℹ️ Парсер уже инициализирован",
    "🚀 Планировщик ежедневного списания запущен"
]

def search_patterns_in_file(filepath):
    """Ищет паттерны в файле"""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            for pattern in PROBLEM_PATTERNS:
                if pattern in line:
                    # Получаем контекст (5 строк до и после)
                    context_start = max(0, i - 6)
                    context_end = min(len(lines), i + 5)

                    context = []
                    for j in range(context_start, context_end):
                        prefix = ">>> " if j == i-1 else "    "
                        context.append(f"{prefix}{j+1}: {lines[j].rstrip()}")

                    issues.append({
                        'line': i,
                        'pattern': pattern,
                        'code': line.strip(),
                        'context': '\n'.join(context)
                    })
                    break  # Нашли один паттерн - выходим

    except Exception as e:
        print(f"❌ Ошибка чтения {filepath}: {e}")

    return issues

def analyze_file_structure(filepath, line_num):
    """Анализирует структуру файла вокруг проблемной строки"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    target_line = line_num - 1  # Переводим в 0-based индекс

    # Ищем класс, в котором находится строка
    current_class = None
    class_start = -1
    class_indent = 0

    for i in range(target_line, -1, -1):
        if lines[i].strip().startswith('class '):
            current_class = lines[i].strip().split(' ')[1].split('(')[0]
            class_start = i
            class_indent = len(lines[i]) - len(lines[i].lstrip())
            break

    if current_class:
        # Ищем методы внутри класса
        methods = []
        for i in range(class_start + 1, len(lines)):
            if lines[i].strip().startswith('def '):
                method_indent = len(lines[i]) - len(lines[i].lstrip())
                if method_indent > class_indent:
                    method_name = lines[i].strip().split(' ')[1].split('(')[0]
                    methods.append((i, method_name, method_indent))

        # Определяем, находится ли строка внутри метода
        in_method = None
        target_indent = len(lines[target_line]) - len(lines[target_line].lstrip())

        for method_line, method_name, method_indent in reversed(methods):
            if target_line > method_line and target_indent > method_indent:
                # Находим конец метода
                method_end = method_line
                for j in range(method_line + 1, len(lines)):
                    if lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) <= method_indent:
                        method_end = j
                        break

                if target_line < method_end:
                    in_method = method_name
                    break

        return {
            'class': current_class,
            'class_line': class_start + 1,
            'in_method': in_method,
            'target_indent': target_indent,
            'class_indent': class_indent,
            'is_class_level': in_method is None and target_indent == class_indent + 4
        }

    return {
        'class': None,
        'in_method': None,
        'is_class_level': False,
        'is_global': True
    }

def main():
    """Основная функция"""
    print("🔍 ПОИСК КОНКРЕТНЫХ ПРОБЛЕМНЫХ СТРОК")
    print("=" * 80)

    # Ищем во всех Python файлах
    project_root = Path.cwd()
    search_dirs = ['apps', 'parser', 'system']

    all_issues = []

    for search_dir in search_dirs:
        dir_path = project_root / search_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob('*.py'):
            issues = search_patterns_in_file(filepath)
            if issues:
                all_issues.extend([(filepath, issue) for issue in issues])

    print(f"\n📊 Найдено {len(all_issues)} проблемных строк")

    if all_issues:
        print("\n🚨 ПРОБЛЕМНЫЕ ФАЙЛЫ:")
        print("=" * 80)

        # Группируем по файлам
        issues_by_file = {}
        for filepath, issue in all_issues:
            rel_path = str(filepath.relative_to(project_root))
            if rel_path not in issues_by_file:
                issues_by_file[rel_path] = []
            issues_by_file[rel_path].append(issue)

        for filepath, issues in issues_by_file.items():
            print(f"\n📄 {filepath}:")

            for issue in issues:
                print(f"\n  ❌ Строка {issue['line']}:")
                print(f"     Паттерн: {issue['pattern']}")
                print(f"     Код: {issue['code']}")

                # Анализируем структуру
                structure = analyze_file_structure(Path(filepath), issue['line'])

                if structure['is_global']:
                    print(f"     ⚠️  ПРОБЛЕМА: Глобальная область видимости!")
                elif structure['is_class_level']:
                    print(f"     ⚠️  ПРОБЛЕМА: Уровень класса (вне методов)!")
                    print(f"     Класс: {structure['class']}")
                elif structure['in_method']:
                    print(f"     ✅ В методе: {structure['in_method']}")
                    print(f"     Класс: {structure['class']}")
                else:
                    print(f"     📍 Контекст: {structure}")

                print(f"\n     Контекст:")
                print(issue['context'])
                print()

    # Даем рекомендации
    print("\n" + "=" * 80)
    print("💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
    print("=" * 80)
    print("""
1. Для логов на уровне класса (вне методов):
   Переместите их в метод __init__ соответствующего класса
   
   БЫЛО:
   class TimerManager:
       logger.info("⏰ Таймер-менеджер инициализирован")
       
   СТАЛО:
   class TimerManager:
       def __init__(self):
           logger.info("⏰ Таймер-менеджер инициализирован")

2. Для глобальных логов:
   Создайте функцию инициализации или переместите в main()
   
3. Альтернатива - ленивая инициализация:
   class TimerManager:
       _initialized = False
       
       def __init__(self):
           if not self._initialized:
               logger.info("⏰ Таймер-менеджер инициализирован")
               self._initialized = True
    """)

if __name__ == "__main__":
    main()