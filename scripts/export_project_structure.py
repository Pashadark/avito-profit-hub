#!/usr/bin/env python3
"""
Скрипт для отображения текущей структуры проекта
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

        # Если хотите быть уверенным, можно указать явный путь:
        # self.project_root = Path(r"C:\Users\pasahdark\PycharmProjects\avito_profit_hub")

    def analyze_structure(self):
        """Анализирует текущую структуру проекта"""
        print(f"\n{Fore.YELLOW}🔍 АНАЛИЗ ТЕКУЩЕЙ СТРУКТУРЫ ПРОЕКТА{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'═' * 60}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}📁 {self.project_root.name}/{Style.RESET_ALL}")

        # Получаем все файлы и папки
        items = list(self.project_root.iterdir())
        items.sort(key=lambda x: (not x.is_dir(), x.name))

        for item in items:
            self._print_item(item, "", 0)

    def _print_item(self, path, prefix, level):
        """Рекурсивно печатает элемент"""
        if path.name.startswith('.') and path.name not in ['.env', '.gitignore']:
            return

        is_dir = path.is_dir()

        # Определяем иконку и цвет
        icon, color = self._get_icon_and_color(path)

        # Пропускаем служебные папки
        if is_dir and path.name in ['__pycache__', 'venv', '.venv', '.git', '.idea', 'node_modules']:
            return

        # Печатаем текущий элемент
        if level == 0:
            connector = "├── "
        else:
            connector = "├── "

        print(f"{prefix}{connector}{icon} {color}{path.name}{Style.RESET_ALL}")

        # Если это директория, рекурсивно анализируем
        if is_dir:
            try:
                sub_items = list(path.iterdir())
                sub_items.sort(key=lambda x: (not x.is_dir(), x.name))

                for i, sub_item in enumerate(sub_items):
                    is_last = (i == len(sub_items) - 1)
                    new_prefix = prefix + ("    " if is_last else "│   ")

                    # Пропускаем ТОЛЬКО pycache
                    if sub_item.is_dir() and sub_item.name == '__pycache__':
                        continue

                    # Ограничиваем глубину (увеличил для apps)
                    if level < 4:  # Был 3, теперь 4
                        self._print_item(sub_item, new_prefix, level + 1)
            except PermissionError:
                pass

    def _get_icon_and_color(self, path):
        """Определяет иконку и цвет для элемента"""
        name = path.name
        is_dir = path.is_dir()

        if is_dir:
            # Директории
            if name == 'apps':
                return "📦", Fore.CYAN
            elif name == 'app':
                return "📱", Fore.GREEN
            elif name == 'scripts':
                return "🔧", Fore.YELLOW
            elif name == 'config':
                return "⚙️", Fore.LIGHTCYAN_EX
            elif name == 'database':
                return "🗄️", Fore.LIGHTBLUE_EX
            elif name == 'website':
                return "🌐", Fore.BLUE
            elif name == 'services':
                return "⚙️", Fore.GREEN
            elif name == 'shared':
                return "🤝", Fore.MAGENTA
            elif name == 'infrastructure':
                return "🏗️", Fore.YELLOW
            elif name == 'static':
                return "🎨", Fore.LIGHTMAGENTA_EX
            elif name == 'templates':
                return "📝", Fore.LIGHTYELLOW_EX
            elif name == 'migrations':
                return "🔄", Fore.LIGHTBLUE_EX
            else:
                return "📁", Fore.CYAN
        else:
            # Файлы
            if name.endswith('.py'):
                return "🐍", Fore.GREEN
            elif name.endswith('.html'):
                return "🌐", Fore.YELLOW
            elif name.endswith(('.css', '.scss', '.less')):
                return "🎨", Fore.MAGENTA
            elif name.endswith(('.js', '.jsx', '.ts', '.tsx')):
                return "⚡", Fore.BLUE
            elif name.endswith(('.json', '.yaml', '.yml')):
                return "📋", Fore.LIGHTYELLOW_EX
            elif 'docker' in name:
                return "🐳", Fore.LIGHTCYAN_EX
            elif name.startswith('.env'):
                return "🔐", Fore.LIGHTRED_EX
            elif name == 'requirements.txt':
                return "📦", Fore.LIGHTGREEN_EX
            elif name == 'manage.py':
                return "⚙️", Fore.LIGHTCYAN_EX
            elif name == 'README.md':
                return "📖", Fore.LIGHTBLUE_EX
            else:
                return "📄", Fore.WHITE

    def show_statistics(self):
        """Показывает статистику проекта"""
        print(f"\n{Fore.YELLOW}📊 СТАТИСТИКА ПРОЕКТА{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'─' * 40}{Style.RESET_ALL}")

        stats = {
            'total_files': 0,
            'python_files': 0,
            'html_files': 0,
            'css_files': 0,
            'js_files': 0,
            'dirs': 0,
        }

        for root, dirs, files in os.walk(self.project_root):
            # Пропускаем служебные папки
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', '.venv']]

            stats['dirs'] += len(dirs)

            for file in files:
                if file.startswith('.'):
                    continue

                stats['total_files'] += 1

                if file.endswith('.py'):
                    stats['python_files'] += 1
                elif file.endswith('.html'):
                    stats['html_files'] += 1
                elif file.endswith(('.css', '.scss', '.less')):
                    stats['css_files'] += 1
                elif file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    stats['js_files'] += 1

        print(f"📁 Директорий: {stats['dirs']}")
        print(f"📄 Всего файлов: {stats['total_files']}")
        print(f"🐍 Python файлов: {stats['python_files']}")
        print(f"🌐 HTML файлов: {stats['html_files']}")
        print(f"🎨 CSS файлов: {stats['css_files']}")
        print(f"⚡ JS файлов: {stats['js_files']}")

        # Показываем пропущенные папки
        print(f"\n{Fore.YELLOW}⚠️  ПРОПУЩЕНЫ СЛУЖЕБНЫЕ ПАПКИ:{Style.RESET_ALL}")
        print(f"• __pycache__")
        print(f"• venv/.venv")
        print(f"• .git")
        print(f"• node_modules")


def main():
    analyzer = ProjectAnalyzer()

    print(f"\n{Fore.CYAN}📍 Текущая директория скрипта: {Path.cwd()}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📍 Анализируем проект: {analyzer.project_root}{Style.RESET_ALL}")

    analyzer.analyze_structure()
    analyzer.show_statistics()

    print(f"\n{Fore.GREEN}✅ Анализ завершен!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()