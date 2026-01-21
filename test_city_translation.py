import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

print("🚀 Тест перевода города 'Пенза'")

try:
    from parsing.parser.utils.city_translator import CityTranslator
    translator = CityTranslator()
    slug = translator.get_slug('Пенза')
    print(f"✅ 'Пенза' -> '{slug}'")

    if slug == 'penza':
        print("🎉 Перевод правильный!")
    else:
        print(f"⚠️  Ожидалось 'penza', получили '{slug}'")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
