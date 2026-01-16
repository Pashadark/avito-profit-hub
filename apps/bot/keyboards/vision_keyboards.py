from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class VisionKeyboards:
    """Клавиатуры для системы обратной связи компьютерного зрения"""

    @staticmethod
    def get_feedback_keyboard(product_url: str) -> InlineKeyboardMarkup:
        """Базовая клавиатура для обратной связи"""
        url_suffix = product_url[-10:]  # Берем последние 10 символов URL

        keyboard = [
            [
                InlineKeyboardButton("✅ ДА, соответствует", callback_data=f"vision_yes_{url_suffix}"),
                InlineKeyboardButton("❌ НЕТ, не соответствует", callback_data=f"vision_no_{url_suffix}")
            ],
            [
                InlineKeyboardButton("🤷 СЛОЖНО СКАЗАТЬ", callback_data=f"vision_unsure_{url_suffix}")
            ],
            [
                InlineKeyboardButton("📝 РУЧНОЕ ОПИСАНИЕ", callback_data=f"vision_describe_{url_suffix}")
            ],
            [
                InlineKeyboardButton("📱 Перейти к объявлению", url=product_url)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_enhanced_feedback_keyboard(product_url: str) -> InlineKeyboardMarkup:
        """Расширенная клавиатура для обучения"""
        url_suffix = product_url[-10:]

        keyboard = [
            [
                InlineKeyboardButton("✅ ТОЧНО В ТЕМУ", callback_data=f"learn_perfect_{url_suffix}"),
                InlineKeyboardButton("⚠️ ЧАСТИЧНО", callback_data=f"learn_partial_{url_suffix}")
            ],
            [
                InlineKeyboardButton("❌ СОВСЕМ НЕ ТО", callback_data=f"learn_wrong_{url_suffix}")
            ],
            [
                InlineKeyboardButton("📁 УКАЗАТЬ КАТЕГОРИЮ", callback_data=f"learn_category_{url_suffix}"),
                InlineKeyboardButton("🎨 ОПИСАТЬ ВНЕШНОСТЬ", callback_data=f"learn_appearance_{url_suffix}")
            ],
            [
                InlineKeyboardButton("🔍 Посмотреть товар", url=product_url)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)