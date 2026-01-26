from django.urls import reverse

# 1. Проверим namespace
try:
    print("1. С namespace 'website':", reverse('website:found_items'))
except Exception as e:
    print("1. Ошибка с namespace:", e)

# 2. Проверим без namespace
try:
    print("2. Без namespace:", reverse('found_items'))
except Exception as e:
    print("2. Ошибка без namespace:", e)

# 3. Полный список всех URL
from django.urls import get_resolver

urls = []
for pattern in get_resolver().url_patterns:
    if hasattr(pattern, 'name') and pattern.name:
        urls.append(pattern.name)

print("\n3. Все зарегистрированные URL names:", set(urls)[:20])