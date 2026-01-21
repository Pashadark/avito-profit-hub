# 🔥 ПРОСТАЯ ЛОГИКА ЗАПРОСОВ (без AI оптимизации)
# Этот файл заменяет query_optimizer.py

def get_simple_queries(keywords, max_queries=10):
    """
    🎯 Простая обработка ключевых слов
    Использует ТОЛЬКО то что указал пользователь в настройках
    """
    if not keywords:
        return ["iphone"]  # фолбэк

    # Если keywords это строка - разбиваем по запятым
    if isinstance(keywords, str):
        queries = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    else:
        queries = list(keywords)

    # Ограничиваем количество
    queries = queries[:max_queries]

    print(f"🎯 Используем {len(queries)} простых запросов:")
    for q in queries:
        print(f"   - '{q}'")

    return queries
