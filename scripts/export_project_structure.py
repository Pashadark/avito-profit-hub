#!/usr/bin/env python3
"""
Скрипт для отображения текущей структуры проекта с фильтрацией
"""

import os
import sys
from pathlib import Path
from colorama import init, Fore, Style

init(autoreset=True)


class ProjectAnalyzer:
    def __init__(self):
        # Поднимаемся на уровень выше scripts/ в корень проекта
        self.project_root = Path.cwd().parent
        self.show_all = False
        self.show_media = False
        self.verbose = False

    def show_menu(self):
        """Показывает меню выбора отображения"""
        print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════╗")
        print(f"║      {Fore.YELLOW}📁 ВЫБОР РЕЖИМА ОТОБРАЖЕНИЯ{Fore.CYAN}       ║")
        print(f"╠═══════════════════════════════════════════╣")
        print(f"║ 1. {Fore.GREEN}Только структура + Python файлы{Fore.CYAN}    ║")
        print(f"║ 2. {Fore.YELLOW}+ Конфиги и README{Fore.CYAN}                ║")
        print(f"║ 3. {Fore.LIGHTBLUE_EX}+ Docker и зависимости{Fore.CYAN}          ║")
        print(f"║ 4. {Fore.MAGENTA}Показать все файлы{Fore.CYAN}               ║")
        print(f"║ 5. {Fore.LIGHTCYAN_EX}Только структура директорий{Fore.CYAN}      ║")
        print(f"║ 0. {Fore.LIGHTRED_EX}Выйти{Fore.CYAN}                            ║")
        print(f"╚═══════════════════════════════════════════╝{Style.RESET_ALL}")

        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Выберите режим (0-5): {Style.RESET_ALL}").strip()
                if choice in ['0', '1', '2', '3', '4', '5']:
                    return int(choice)
                else:
                    print(f"{Fore.RED}❌ Введите число от 0 до 5!{Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}👋 Выход...{Style.RESET_ALL}")
                sys.exit(0)

    def analyze_structure(self, mode=1):
        """Анализирует текущую структуру проекта"""
        print(f"\n{Fore.YELLOW}🔍 АНАЛИЗ СТРУКТУРЫ ПРОЕКТА{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'═' * 60}{Style.RESET_ALL}")

        # Настраиваем фильтры в зависимости от режима
        if mode == 1:
            print(f"{Fore.CYAN}📋 Режим: Только структура + Python файлы{Style.RESET_ALL}")
            self.show_all = False
            self.show_media = False
            self.verbose = False
        elif mode == 2:
            print(f"{Fore.CYAN}📋 Режим: + Конфиги и README{Style.RESET_ALL}")
            self.show_all = False
            self.show_media = False
            self.verbose = True
        elif mode == 3:
            print(f"{Fore.CYAN}📋 Режим: + Docker и зависимости{Style.RESET_ALL}")
            self.show_all = False
            self.show_media = False
            self.verbose = True
        elif mode == 4:
            print(f"{Fore.CYAN}📋 Режим: Показать все файлы{Style.RESET_ALL}")
            self.show_all = True
            self.show_media = True
            self.verbose = True
        elif mode == 5:
            print(f"{Fore.CYAN}📋 Режим: Только структура директорий{Style.RESET_ALL}")
            self.show_all = False
            self.show_media = False
            self.verbose = False

        print(f"{Fore.LIGHTCYAN_EX}📂 Корень: {self.project_root}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}📁 {self.project_root.name}/{Style.RESET_ALL}")

        # Получаем все файлы и папки
        items = list(self.project_root.iterdir())
        items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

        for item in items:
            self._print_item(item, "", 0, mode)

    def _should_show_file(self, path, mode):
        """Определяет, нужно ли показывать файл в текущем режиме"""
        name = path.name.lower()
        ext = path.suffix.lower()

        # Всегда показываем .env и .gitignore
        if name in ['.env', '.gitignore', '.env.example']:
            return True

        # Пропускаем служебные файлы
        if name in ['thumbs.db', '.ds_store'] or name.startswith('~$'):
            return False

        # Пропускаем скомпилированные файлы
        if name.endswith(('.pyc', '.pyo', '.pyd', '.so')):
            return False

        # Пропускаем логи
        if name.endswith('.log') or name.startswith('log'):
            return False

        # Проверяем режимы
        if mode == 1:  # Только Python файлы
            if ext in ['.py', '.pyi']:
                return True
            return path.is_dir()

        elif mode == 2:  # Python + конфиги
            if ext in ['.py', '.pyi']:
                return True
            if name in ['requirements.txt', 'pyproject.toml', 'setup.py',
                        'setup.cfg', 'manifest.in', 'pytest.ini', 'tox.ini']:
                return True
            if name.endswith(('.yml', '.yaml', '.json', '.toml', '.cfg', '.ini')):
                return True
            if name in ['readme.md', 'readme.rst', 'readme.txt', 'license',
                        'license.txt', 'license.md', 'contributing.md']:
                return True
            return path.is_dir()

        elif mode == 3:  # Python + конфиги + Docker
            if ext in ['.py', '.pyi']:
                return True
            if any(keyword in name for keyword in [
                'docker', 'dockerfile', 'docker-compose', 'requirements',
                'pyproject', 'setup', 'manifest', 'pytest', 'tox'
            ]):
                return True
            if name.endswith(('.yml', '.yaml', '.json', '.toml', '.cfg', '.ini')):
                return True
            if name in ['readme.md', 'readme.rst', 'readme.txt', 'license']:
                return True
            return path.is_dir()

        elif mode == 5:  # Только директории
            return path.is_dir()

        # Для режима 4 (все файлы) и по умолчанию
        return True

    def _should_show_dir(self, path):
        """Определяет, нужно ли показывать директорию"""
        name = path.name.lower()

        # Пропускаем служебные директории
        skip_dirs = [
            '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
            '.coverage', '.tox', '.eggs', '.venv', 'venv', '.env',
            '.git', '.hg', '.svn', '.idea', '.vscode', '__pycache__',
            'node_modules', 'dist', 'build', '.next', '.nuxt', '.output',
            'target', 'out', '.gradle', '.settings', 'bin', 'obj', 'packages',
            '.ipynb_checkpoints', '.virtual_documents'
        ]

        return name not in skip_dirs

    def _print_item(self, path, prefix, level, mode):
        """Рекурсивно печатает элемент"""
        name = path.name
        is_dir = path.is_dir()

        # Для директорий
        if is_dir:
            if not self._should_show_dir(path):
                return

            icon, color = self._get_icon_and_color(path)

            if level == 0:
                connector = "├── "
            else:
                connector = "├── "

            print(f"{prefix}{connector}{icon} {color}{name}{Style.RESET_ALL}")

            # Если это директория, рекурсивно анализируем
            try:
                sub_items = list(path.iterdir())
                sub_items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

                for i, sub_item in enumerate(sub_items):
                    is_last = (i == len(sub_items) - 1)
                    new_prefix = prefix + ("    " if is_last else "│   ")

                    if sub_item.is_dir() or self._should_show_file(sub_item, mode):
                        if level < 5:  # Ограничение глубины рекурсии
                            self._print_item(sub_item, new_prefix, level + 1, mode)
            except (PermissionError, OSError) as e:
                if self.verbose:
                    print(f"{prefix}    └── 🔒 {Fore.RED}[Permission Denied]{Style.RESET_ALL}")

        # Для файлов
        else:
            if not self._should_show_file(path, mode):
                return

            icon, color = self._get_icon_and_color(path)
            connector = "├── "

            # Добавляем информацию о размере в verbose режиме
            size_info = ""
            if self.verbose:
                try:
                    size = path.stat().st_size
                    if size > 1024 * 1024:
                        size_info = f" {Fore.LIGHTBLACK_EX}({size / 1024 / 1024:.1f} MB){Style.RESET_ALL}"
                    elif size > 1024:
                        size_info = f" {Fore.LIGHTBLACK_EX}({size / 1024:.1f} KB){Style.RESET_ALL}"
                    else:
                        size_info = f" {Fore.LIGHTBLACK_EX}({size} B){Style.RESET_ALL}"
                except:
                    size_info = f" {Fore.LIGHTBLACK_EX}(? B){Style.RESET_ALL}"

            print(f"{prefix}{connector}{icon} {color}{name}{Style.RESET_ALL}{size_info}")

    def _get_icon_and_color(self, path):
        """Определяет иконку и цвет для элемента"""
        name = path.name
        is_dir = path.is_dir()

        if is_dir:
            # Директории
            dir_icons = {
                'apps': "📦", 'app': "📱", 'src': "📦", 'source': "📦",
                'scripts': "🔧", 'tools': "🔧", 'utils': "🛠️",
                'config': "⚙️", 'configuration': "⚙️", 'settings': "⚙️",
                'database': "🗄️", 'db': "🗄️", 'data': "🗄️",
                'website': "🌐", 'web': "🌐", 'frontend': "🌐",
                'services': "⚙️", 'service': "⚙️",
                'shared': "🤝", 'common': "🤝", 'core': "🤝",
                'infrastructure': "🏗️", 'infra': "🏗️",
                'static': "🎨", 'assets': "🎨", 'resources': "🎨",
                'templates': "📝", 'views': "📝", 'pages': "📝",
                'migrations': "🔄", 'migration': "🔄",
                'tests': "🧪", 'test': "🧪", 'testing': "🧪",
                'docs': "📚", 'documentation': "📚",
                'api': "🔌", 'rest': "🔌", 'graphql': "🔌",
                'models': "📊", 'schemas': "📊",
                'controllers': "🎮", 'views': "👁️",
                'middleware': "🔗", 'middlewares': "🔗",
                'routers': "🛣️", 'routes': "🛣️",
                'helpers': "🆘", 'utilities': "🛠️",
            }

            for key, icon in dir_icons.items():
                if name.lower() == key or name.lower().startswith(key):
                    return icon, Fore.CYAN

            return "📁", Fore.CYAN

        else:
            # Файлы
            if name.endswith('.py'):
                return "🐍", Fore.GREEN
            elif name.endswith(('.pyi', '.pyd')):
                return "🐍", Fore.LIGHTGREEN_EX
            elif 'docker' in name.lower() or name == 'Dockerfile':
                return "🐳", Fore.LIGHTCYAN_EX
            elif name.startswith('.env'):
                return "🔐", Fore.LIGHTRED_EX
            elif name in ['.gitignore', '.gitattributes', '.gitmodules']:
                return "🔧", Fore.LIGHTBLACK_EX
            elif name == 'requirements.txt':
                return "📦", Fore.LIGHTGREEN_EX
            elif name == 'pyproject.toml':
                return "📦", Fore.GREEN
            elif name in ['setup.py', 'setup.cfg']:
                return "📦", Fore.YELLOW
            elif name == 'manage.py':
                return "⚙️", Fore.LIGHTCYAN_EX
            elif name.lower().startswith('readme'):
                return "📖", Fore.LIGHTBLUE_EX
            elif name.lower().startswith('license'):
                return "⚖️", Fore.LIGHTYELLOW_EX
            elif name.endswith(('.yml', '.yaml')):
                return "📋", Fore.LIGHTMAGENTA_EX
            elif name.endswith('.json'):
                return "📋", Fore.YELLOW
            elif name.endswith(('.toml', '.cfg', '.ini')):
                return "⚙️", Fore.LIGHTCYAN_EX
            elif name.endswith('.md'):
                return "📝", Fore.LIGHTBLUE_EX
            elif name.endswith('.sql'):
                return "🗄️", Fore.LIGHTBLUE_EX
            elif name.endswith('.txt'):
                return "📄", Fore.LIGHTWHITE_EX
            elif name.endswith('.sh'):
                return "🐚", Fore.LIGHTGREEN_EX
            elif name.endswith('.bat', '.cmd'):
                return "🪟", Fore.LIGHTBLUE_EX
            elif name.endswith('.ps1'):
                return "💻", Fore.LIGHTBLUE_EX
            else:
                if self.show_all:
                    return "📄", Fore.LIGHTBLACK_EX
                else:
                    return "📄", Fore.WHITE

    def show_statistics(self, mode):
        """Показывает статистику проекта"""
        print(f"\n{Fore.YELLOW}📊 СТАТИСТИКА ПРОЕКТА{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'─' * 40}{Style.RESET_ALL}")

        stats = {
            'total_dirs': 0,
            'total_files': 0,
            'python_files': 0,
            'config_files': 0,
            'docker_files': 0,
            'doc_files': 0,
            'other_files': 0,
            'skipped_dirs': 0,
            'skipped_files': 0,
        }

        skip_dirs = [
            '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
            '.coverage', '.tox', '.eggs', '.venv', 'venv', '.env',
            '.git', '.hg', '.svn', '.idea', '.vscode',
            'node_modules', 'dist', 'build', '.next', '.nuxt',
            '.output', 'target', 'out', '.gradle'
        ]

        for root, dirs, files in os.walk(self.project_root):
            # Убираем служебные директории из обхода
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            stats['total_dirs'] += len(dirs)
            stats['skipped_dirs'] += len([d for d in dirs if d in skip_dirs])

            for file in files:
                stats['total_files'] += 1

                filepath = Path(root) / file
                name = file.lower()
                ext = filepath.suffix.lower()

                # Проверяем, нужно ли показывать файл
                if not self._should_show_file(filepath, mode):
                    stats['skipped_files'] += 1
                    continue

                if ext in ['.py', '.pyi']:
                    stats['python_files'] += 1
                elif any(keyword in name for keyword in [
                    'docker', 'dockerfile', 'docker-compose'
                ]):
                    stats['docker_files'] += 1
                elif name.endswith(('.yml', '.yaml', '.json', '.toml', '.cfg', '.ini')):
                    stats['config_files'] += 1
                elif name.startswith(('readme', 'license', 'contributing')) or name.endswith('.md'):
                    stats['doc_files'] += 1
                else:
                    stats['other_files'] += 1

        # Выводим статистику в зависимости от режима
        print(f"📁 Директорий: {stats['total_dirs']}")

        if mode == 5:
            print(f"📄 Файлов: {Fore.YELLOW}показаны только директории{Style.RESET_ALL}")
        else:
            print(f"📄 Файлов: {stats['total_files']}")

            if mode == 1:
                print(f"🐍 Python файлов: {stats['python_files']}")
            elif mode == 2:
                print(f"🐍 Python файлов: {stats['python_files']}")
                print(f"⚙️  Конфигурационных файлов: {stats['config_files']}")
                print(f"📚 Документации: {stats['doc_files']}")
            elif mode == 3:
                print(f"🐍 Python файлов: {stats['python_files']}")
                print(f"⚙️  Конфигурационных файлов: {stats['config_files']}")
                print(f"🐳 Docker файлов: {stats['docker_files']}")
                print(f"📚 Документации: {stats['doc_files']}")
            elif mode == 4:
                print(f"🐍 Python файлов: {stats['python_files']}")
                print(f"⚙️  Конфигурационных файлов: {stats['config_files']}")
                print(f"🐳 Docker файлов: {stats['docker_files']}")
                print(f"📚 Документации: {stats['doc_files']}")
                print(f"📄 Прочих файлов: {stats['other_files']}")

        if stats['skipped_dirs'] > 0 or stats['skipped_files'] > 0:
            print(f"\n{Fore.YELLOW}⚠️  ПРОПУЩЕНО:{Style.RESET_ALL}")
            if stats['skipped_dirs'] > 0:
                print(f"• Директорий: {stats['skipped_dirs']}")
            if stats['skipped_files'] > 0 and mode != 5:
                print(f"• Файлов: {stats['skipped_files']}")


def main():
    """Основная функция"""
    analyzer = ProjectAnalyzer()

    print(f"\n{Fore.CYAN}📍 Текущая директория скрипта: {Path.cwd()}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📍 Корень проекта: {analyzer.project_root}{Style.RESET_ALL}")

    while True:
        try:
            mode = analyzer.show_menu()

            if mode == 0:
                print(f"\n{Fore.GREEN}👋 Выходим...{Style.RESET_ALL}")
                break

            analyzer.analyze_structure(mode)
            analyzer.show_statistics(mode)

            print(f"\n{Fore.GREEN}✅ Анализ завершен!{Style.RESET_ALL}")

            # Спрашиваем, не хочет ли Паштет пивка?
            if mode != 0:
                print(
                    f"\n{Fore.LIGHTYELLOW_EX}🍻 Паштет, может пивка покапаем код? Или сразу к следующему делу?{Style.RESET_ALL}")
                input(f"{Fore.LIGHTBLACK_EX}Нажми Enter чтобы продолжить...{Style.RESET_ALL}")

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Выход...{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"\n{Fore.RED}❌ Ошибка: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}🔄 Пробуем снова...{Style.RESET_ALL}")


if __name__ == "__main__":
    main()