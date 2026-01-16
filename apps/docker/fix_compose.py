# fix_compose.py
import yaml
import os


def fix_docker_compose():
    compose_file = 'docker-compose.yml'
    backup_file = 'docker-compose.yml.backup'

    print(f"🔧 Исправление {compose_file}...")

    # Создаем backup
    if os.path.exists(compose_file):
        import shutil
        shutil.copy2(compose_file, backup_file)
        print(f"✅ Backup создан: {backup_file}")

    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Вручную исправляем структуру (проще чем парсить YAML с ошибками)
        lines = content.split('\n')
        fixed_lines = []
        in_django = False
        command_count = 0

        for line in lines:
            stripped = line.strip()

            # Начало секции django
            if 'django:' in stripped and not stripped.startswith('#'):
                in_django = True
                fixed_lines.append(line)
                continue

            # Конец секции django
            if in_django and stripped and not stripped.startswith(' ') and not stripped.startswith('\t'):
                in_django = False

            # Внутри секции django
            if in_django:
                # Убираем дублирующиеся command
                if stripped.startswith('command:'):
                    command_count += 1
                    if command_count == 1:
                        # Оставляем первый command
                        fixed_lines.append(line)
                    else:
                        # Пропускаем дубликаты
                        print(f"⚠️ Удалён дубликат command: {line}")
                    continue

                # Добавляем недостающие environment переменные
                if stripped.startswith('environment:'):
                    fixed_lines.append(line)
                    # Проверяем следующие строки
                    continue

            fixed_lines.append(line)

        # Теперь добавляем environment если его нет
        result = '\n'.join(fixed_lines)

        # Добавляем environment секцию после command если её нет
        if 'environment:' not in result or 'django:' not in result:
            # Находим позицию после command в секции django
            lines = result.split('\n')
            new_lines = []
            in_django = False
            command_found = False

            for i, line in enumerate(lines):
                stripped = line.strip()
                new_lines.append(line)

                # Начало секции django
                if 'django:' in stripped and not stripped.startswith('#'):
                    in_django = True
                    continue

                # Конец секции django
                if in_django and stripped and not stripped.startswith(' ') and not stripped.startswith('\t'):
                    in_django = False

                # После command добавляем environment
                if in_django and stripped.startswith('command:'):
                    command_found = True
                    # Проверяем следующие строки на наличие environment
                    has_environment = False
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if lines[j].strip().startswith('environment:'):
                            has_environment = True
                            break

                    if not has_environment:
                        # Добавляем environment
                        new_lines.append('    environment:')
                        new_lines.append('      - PYTHONPATH=/app:/app/apps')
                        new_lines.append('      - DJANGO_SETTINGS_MODULE=core.settings')
                        new_lines.append(
                            '      - DATABASE_URL=postgres://avito_user:avito_password@postgres:5432/avito_db')
                        print("✅ Добавлены environment переменные")

            result = '\n'.join(new_lines)

        # Записываем исправленный файл
        with open(compose_file, 'w', encoding='utf-8') as f:
            f.write(result)

        print("✅ docker-compose.yml исправлен")

        # Покажем исправленную секцию django
        print("\n📋 Секция django после исправлений:")
        print("-" * 40)
        lines = result.split('\n')
        in_django = False
        for line in lines:
            stripped = line.strip()
            if 'django:' in stripped and not stripped.startswith('#'):
                in_django = True

            if in_django and line.strip() and not line.strip().startswith(' ') and not line.strip().startswith(
                    '\t') and not 'django:' in line:
                in_django = False

            if in_django:
                print(line)
        print("-" * 40)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

        # Восстанавливаем из backup
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, compose_file)
            print(f"⚠️ Восстановлен из backup: {backup_file}")


if __name__ == '__main__':
    fix_docker_compose()