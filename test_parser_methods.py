import sys
sys.path.append('.')

from apps.parsing.utils.selenium_parser import SeleniumAvitoParser

# Создаем парсер
parser = SeleniumAvitoParser()

print("🔍 Методы SeleniumAvitoParser:")
methods = [m for m in dir(parser) if not m.startswith('_') and callable(getattr(parser, m))]
for method in methods:
    print(f"  • {method}")

print("\n🔧 Проверяем start_system:")
if hasattr(parser, 'start_system'):
    print("✅ Есть метод start_system")
    import inspect
    sig = inspect.signature(parser.start_system)
    print(f"✅ Сигнатура: {sig}")
else:
    print("❌ НЕТ метода start_system")

print("\n🔧 Проверяем start:")
if hasattr(parser, 'start'):
    print("✅ Есть метод start")
    sig = inspect.signature(parser.start)
    print(f"✅ Сигнатура: {sig}")

print("\n🔧 Проверяем start_with_settings:")
if hasattr(parser, 'start_with_settings'):
    print("✅ Есть метод start_with_settings")
    sig = inspect.signature(parser.start_with_settings)
    print(f"✅ Сигнатура: {sig}")