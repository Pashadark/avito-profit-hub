import re


class ProductAnalyzer:
    def __init__(self):
        # Менее строгий черный список
        self.blacklist_keywords = [
            'магазин', 'интернет-магазин', 'оптом', 'розница',
            'wholesale', 'retail', 'shop', 'store', 'купить оптом'
        ]

        self.suspicious_patterns = [
            r'\d{8,}',  # Очень длинные цифровые последовательности
            r'[A-Z0-9]{10,}',  # Длинные артикулы
        ]

    def is_suspicious_product(self, product):
        """Проверяет, не является ли товар магазинным (менее строгая проверка)"""
        title = product.get('name', '').lower()
        description = product.get('description', '').lower()

        # Пропускаем проверку если нет данных
        if not title:
            return False

        # Проверка по черному списку ключевых слов (только явные совпадения)
        for keyword in self.blacklist_keywords:
            if f' {keyword} ' in f' {title} ' or f' {keyword} ' in f' {description} ':
                return True

        # Более мягкая проверка паттернов
        for pattern in self.suspicious_patterns:
            if re.search(pattern, title):
                return True

        return False

    def calculate_profit_score(self, product):
        """Рассчитывает оценку выгодности товара"""
        price = product.get('price', 0)
        target_price = product.get('target_price', 0)

        if price <= 0 or target_price <= 0:
            return 0

        # Процент экономии - основной фактор
        economy = target_price - price
        if economy <= 0:
            return 0

        economy_percent = (economy / target_price) * 100

        # СНИЖАЕМ порог выгодности
        score = economy_percent * 0.8  # 80% веса у экономии в процентах

        # Добавляем бонус за абсолютную экономию
        absolute_bonus = min(economy / 1000, 10)  # до 10 баллов за каждую 1000р экономии
        score += absolute_bonus

        return round(score, 2)