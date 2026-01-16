import logging
from typing import Dict, Any, Optional
from telegram import Bot, InlineKeyboardMarkup
from shared.utils.config import get_bot_token, get_chat_id

logger = logging.getLogger('bot.services.vision_service')

class VisionFeedbackService:
    """Сервис для обработки обратной связи по компьютерному зрению"""

    def __init__(self):
        self.bot = None
        self._initialize_bot()

    def _initialize_bot(self):
        """Инициализирует бота"""
        try:
            token = get_bot_token()
            self.bot = Bot(token=token)
            logger.info("✅ Vision service бот инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота для vision service: {e}")

    async def send_vision_feedback_request(
            self,
            product_title: str,
            search_query: str,
            vision_analysis: Dict[str, Any]
    ) -> bool:
        """Отправляет запрос на обратную связь по компьютерному зрению - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # 🔥 ПРОВЕРЯЕМ ТИПЫ ДАННЫХ
            if not isinstance(vision_analysis, dict):
                logger.error(f"❌ Некорректный тип vision_analysis: {type(vision_analysis)}")
                return False

            chat_id = get_chat_id()
            if not self.bot or not chat_id:
                logger.error("❌ Бот или chat_id не инициализирован")
                return False

            # Формируем сообщение
            message = self._format_vision_message(product_title, vision_analysis, search_query)

            # 🔥 СОЗДАЕМ КОРРЕКТНУЮ INLINE КЛАВИАТУРУ
            try:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                # Создаем корректную inline клавиатуру с callback_data
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ ДА", callback_data=f"vision_yes:{product_title[:30]}"),
                        InlineKeyboardButton("❌ НЕТ", callback_data=f"vision_no:{product_title[:30]}")
                    ]
                ])

                logger.info("🎹 Создана корректная inline клавиатура для обратной связи")

            except ImportError:
                logger.warning("⚠️ Не удалось создать inline клавиатуру, отправляем без клавиатуры")
                keyboard = None

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=keyboard,  # Может быть None, это допустимо
                parse_mode='HTML'
            )

            logger.info("📝 Запрос обратной связи по компьютерному зрению отправлен")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки запроса обратной связи: {e}")
            return False

    async def send_enhanced_feedback_request(
            self,
            product: Dict[str, Any],
            vision_data: Dict[str, Any],
            query: str
    ) -> bool:
        """Отправляет расширенный запрос обратной связи"""
        try:
            from apps.bot.keyboards.vision_keyboards import VisionKeyboards

            chat_id = get_chat_id()
            if not self.bot or not chat_id:
                return False

            message = self._format_enhanced_vision_message(product, vision_data, query)
            keyboard = VisionKeyboards.get_enhanced_feedback_keyboard(product['url'])

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

            logger.info("🎯 Расширенный запрос обратной связи отправлен")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки расширенного запроса: {e}")
            return False

    def _format_vision_message(
            self,
            product_title: str,
            vision_analysis: Dict[str, Any],
            query: str
    ) -> str:
        """Форматирует сообщение с данными компьютерного зрения - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        vision_text = self._format_vision_details(vision_analysis)

        return f"""🤖 <b>ЗАПРОС ОБРАТНОЙ СВЯЗИ ПО КОМПЬЮТЕРНОМУ ЗРЕНИЮ</b>

    📦 <b>Товар:</b> {product_title[:80]}
    🔍 <b>Запрос:</b> '{query}'

    {vision_text}

    ❓ <b>Вопрос:</b> Соответствует ли товар запросу '{query}'?

    💡 <b>Ответьте ДА или НЕТ чтобы помочь ИИ учиться!</b>"""

    def _format_enhanced_vision_message(
            self,
            product: Dict[str, Any],
            vision_data: Dict[str, Any],
            query: str
    ) -> str:
        """Форматирует расширенное сообщение для обучения"""
        vision_text = self._format_vision_details(vision_data)

        return f"""🤖 ОБУЧЕНИЕ КОМПЬЮТЕРНОГО ЗРЕНИЯ

📦 Товар: {product.get('name', 'N/A')[:80]}
🔍 Запрос: '{query}'

{vision_text}

🎯 Помогите улучшить распознавание:"""

    def _format_vision_details(self, vision_data: Dict[str, Any]) -> str:
        """Форматирует данные компьютерного зрения - ИСПРАВЛЕННАЯ ВЕРСИЯ С РЕАЛЬНЫМИ ЦВЕТАМИ"""
        lines = []

        # 🔥 ОТОБРАЖАЕМ РЕАЛЬНЫЕ ЦВЕТА
        colors = vision_data.get('colors', [])
        detected_colors = vision_data.get('detected_colors', [])

        # Приоритет: detected_colors > colors > значения по умолчанию
        if detected_colors and isinstance(detected_colors, list) and detected_colors:
            real_colors = detected_colors
        elif colors and isinstance(colors, list) and colors and colors != ['разноцветный', 'нейтральные тона']:
            real_colors = colors
        else:
            real_colors = ['разноцветный', 'нейтральные тона']

        lines.append(f"🎨 <b>Цвета:</b> {', '.join(real_colors[:3])}")

        # 🔥 ОТОБРАЖАЕМ РЕАЛЬНЫЕ ОБЪЕКТЫ
        objects = vision_data.get('objects', [])
        if objects and objects != ['объект', 'компактный дизайн']:
            lines.append(f"📋 <b>Объекты:</b> {', '.join(objects[:3])}")
        else:
            lines.append(f"📋 <b>Объекты:</b> {', '.join(objects[:3]) if objects else 'не определены'}")

        # 🔥 ОТОБРАЖАЕМ РЕАЛЬНЫЕ МАТЕРИАЛЫ
        materials = vision_data.get('materials', [])
        if materials and materials != ['пластик', 'металл']:
            lines.append(f"⚙️ <b>Материалы:</b> {', '.join(materials[:2])}")
        else:
            lines.append(f"⚙️ <b>Материалы:</b> {', '.join(materials[:2]) if materials else 'не определены'}")

        # Остальные поля
        if vision_data.get('condition'):
            lines.append(f"📝 <b>Состояние:</b> {vision_data['condition']}")

        if vision_data.get('background'):
            lines.append(f"🖼️ <b>Фон:</b> {vision_data['background']}")

        if vision_data.get('confidence'):
            lines.append(f"📊 <b>Уверенность:</b> {vision_data['confidence']:.2f}")

        if vision_data.get('result'):
            lines.append(f"✅ <b>Результат:</b> {vision_data['result']}")

        return '\n'.join(lines) if lines else "📊 <b>Данные анализа недоступны</b>"


# Создаем глобальный экземпляр сервиса
vision_service = VisionFeedbackService()