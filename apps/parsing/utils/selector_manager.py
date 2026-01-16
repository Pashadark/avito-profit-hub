from selenium.webdriver.common.by import By


class SelectorManager:
    def __init__(self):
        self.selectors = {
            'item': [
                '[data-marker="item"]',
                '.iva-item-root-_lk9K',
                '.items-items-kAJAg',
                '.item',
                '.js-item'
            ],
            'title': [
                '[data-marker="item-title"] h3',
                '[itemprop="name"]',
                '.iva-item-titleStep-_CxvN',
                '.title-root-zZCwT',
                'h3[itemprop="name"]'
            ],
            'price': [
                '[data-marker="item-price"]',
                '[itemprop="price"]',
                '.price-price-_P9LN',
                '.iva-item-priceStep-U3B7L',
                'meta[itemprop="price"]'
            ],
            'link': [
                '[data-marker="item-title"]',
                'a[href*="/moskva/"]',
                '.iva-item-titleStep-_CxvN a',
                'a.link-link[href*="/moskva/"]'
            ]
        }

        self.current_selectors = {}

    def test_selectors(self, driver):
        """Тестирует доступные селекторы и выбирает лучший"""
        print("🧪 Тестируем селекторы...")

        for element_type, selectors in self.selectors.items():
            for selector in selectors:
                try:
                    if element_type == 'item':
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            self.current_selectors[element_type] = selector
                            print(
                                f"✅ Найден рабочий селектор для {element_type}: {selector} ({len(elements)} элементов)")
                            break
                    else:
                        element = driver.find_element(By.CSS_SELECTOR, selector)
                        if element and element.is_displayed():
                            self.current_selectors[element_type] = selector
                            add_to_console(f"✅ Найден рабочий селектор для {element_type}: {selector}")
                            break
                except Exception as e:
                    continue

        # Устанавливаем значения по умолчанию если не нашли
        defaults = {
            'item': '[data-marker="item"]',
            'title': '[data-marker="item-title"] h3',
            'price': '[data-marker="item-price"]',
            'link': '[data-marker="item-title"]'
        }

        for element_type, default_selector in defaults.items():
            if element_type not in self.current_selectors:
                self.current_selectors[element_type] = default_selector
                add_to_console(f"⚠️ Используем селектор по умолчанию для {element_type}: {default_selector}")

    def get_selector(self, element_type):
        """Возвращает лучший селектор для элемента"""
        return self.current_selectors.get(element_type, '')

    def update_selectors(self):
        """Автоматически обновляет селекторы (может быть расширено)"""
        pass