#!/usr/bin/env python3
"""
ProfitHub Telegram Bot - Ядро
"""
import os
import sys
import logging
import asyncio
import threading
import time
from datetime import timedelta

logger = logging.getLogger('bot.telegram')

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from telegram.error import TelegramError, NetworkError
from telegram.constants import ParseMode
from asgiref.sync import sync_to_async
import base64

from shared.utils.config import get_bot_token, get_chat_id

# Импорты обработчиков
from .handlers.main_handlers import MainHandlers
from .handlers.profile_handlers import ProfileHandlers
from .handlers.parser_handlers import ParserHandlers
from .handlers.settings_handlers import SettingsHandlers
from .handlers.todo_handlers import TodoHandlers
from .handlers.registration_handlers import RegistrationHandlers


class ProfitHubBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        self.bot = None
        self.is_running = False

        # Инициализация обработчиков
        self.main_handlers = None
        self.profile_handlers = None
        self.parser_handlers = None
        self.settings_handlers = None
        self.todo_handlers = None
        self.registration_handlers = None

        self._initialize_bot()

    def _initialize_bot(self):
        """Инициализация бота"""
        try:
            self.application = Application.builder().token(self.token).build()
            self.bot = self.application.bot

            # Инициализация всех обработчиков
            self._initialize_handlers()

            logger.info("✅ Бот @infopnz58_bot инициализирован успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            raise

    def _initialize_handlers(self):
        """Инициализация всех обработчиков"""
        # Создаем экземпляры обработчиков
        self.main_handlers = MainHandlers(self)
        self.profile_handlers = ProfileHandlers(self)
        self.parser_handlers = ParserHandlers(self)
        self.settings_handlers = SettingsHandlers(self)
        self.todo_handlers = TodoHandlers(self)
        self.registration_handlers = RegistrationHandlers(self)

        # Регистрируем обработчики
        self.main_handlers.register_handlers(self.application)
        self.profile_handlers.register_handlers(self.application)
        self.parser_handlers.register_handlers(self.application)
        self.settings_handlers.register_handlers(self.application)
        self.todo_handlers.register_handlers(self.application)
        self.registration_handlers.register_handlers(self.application)

        logger.info("✅ Все обработчики зарегистрированы")

    # ========== МЕТОДЫ ОТПРАВКИ УВЕДОМЛЕНИЙ ==========

    async def send_notification(self, message: str, image_data: str = None,
                                button_text: str = "", button_url: str = ""):
        """Отправка уведомления в чат"""
        try:
            chat_id = get_chat_id()
            if not chat_id:
                logger.error("❌ TELEGRAM_CHAT_ID не установен")
                return False

            # Создаем клавиатуру если есть кнопка
            keyboard = []
            if button_url:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [[InlineKeyboardButton(button_text, url=button_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            else:
                reply_markup = None

            # Отправляем сообщение
            if image_data and self.is_valid_image_data(image_data):
                return await self._send_photo_notification(chat_id, message, image_data, reply_markup)
            else:
                return await self._send_text_notification(chat_id, message, reply_markup)

        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
            return False

    def is_valid_image_data(self, image_data):
        """Проверка валидности данных изображения"""
        if not image_data:
            return False

        try:
            if 'base64,' in image_data:
                base64_str = image_data.split('base64,')[1]
            else:
                base64_str = image_data

            decoded = base64.b64decode(base64_str)
            return len(decoded) > 100
        except:
            return False

    async def _send_photo_notification(self, chat_id, message, image_data, reply_markup=None):
        """Отправка фото-уведомления"""
        try:
            if 'base64,' in image_data:
                base64_str = image_data.split('base64,')[1]
            else:
                base64_str = image_data

            image_bytes = base64.b64decode(base64_str)

            if len(image_bytes) > 10 * 1024 * 1024:
                logger.warning("⚠️ Изображение слишком большое, отправляем без фото")
                return await self._send_text_notification(chat_id, message, reply_markup)

            caption = message[:1024] if len(message) > 1024 else message

            await self.bot.send_photo(
                chat_id=chat_id,
                photo=image_bytes,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            logger.info("✅ Уведомление с фото отправлено")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки фото: {e}")
            return await self._send_text_notification(chat_id, message, reply_markup)

    async def _send_text_notification(self, chat_id, message, reply_markup=None):
        """Отправка текстового уведомления"""
        try:
            if len(message) > 4096:
                parts = [message[i:i + 4096] for i in range(0, len(message), 4096)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1 and reply_markup:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            reply_markup=reply_markup,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

            logger.info("✅ Текстовое уведомление отправлено")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка отправки текста: {e}")
            return False

    # ========== УПРАВЛЕНИЕ БОТОМ ==========

    def start_polling(self):
        """Запуск бота в отдельном потоке"""
        try:
            logger.info("🚀 Запуск Telegram бота...")

            def run_bot():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    def handle_exception(loop, context):
                        logger.error(f"Ошибка в event loop: {context}")

                    loop.set_exception_handler(handle_exception)

                    try:
                        logger.info("🔄 Запуск запросов бота...")
                        loop.run_until_complete(self.application.run_polling(
                            drop_pending_updates=True,
                            allowed_updates=Update.ALL_TYPES,
                            close_loop=False
                        ))
                    except KeyboardInterrupt:
                        logger.info("⏹️ Бот остановлен по запросу пользователя")
                    except Exception as e:
                        logger.error(f"❌ Ошибка в потоке бота: {e}")
                    finally:
                        if not loop.is_closed():
                            loop.close()

                except Exception as e:
                    logger.error(f"❌ Критическая ошибка в потоке бота: {e}")

            bot_thread = threading.Thread(
                target=run_bot,
                daemon=True,
                name="ProfitHubBotThread"
            )
            bot_thread.start()

            time.sleep(3)
            self.is_running = True
            logger.info("✅ Бот запущен в отдельном потоке")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            self.is_running = False
            return False

    def stop_polling(self):
        """Остановка бота"""
        try:
            if self.is_running and self.application:
                self.application.stop()
                self.is_running = False
                logger.info("✅ Бот остановлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка остановки бота: {e}")
            return False


# ========== ГЛОБАЛЬНЫЕ ФУНКЦИИ ==========

bot_instance = None


def initialize_bot():
    """Инициализация и запуск бота"""
    from shared.utils.config import get_bot_token

    token = get_bot_token()
    if not token:
        logger.error("❌ Токен бота не найден!")
        return False

    logger.info(f"🤖 Инициализация бота с токеном: {token[:10]}...")

    try:
        global bot_instance
        bot_instance = ProfitHubBot(token)

        logger.info("✅ Бот инициализирован успешно!")
        logger.info("🚀 Запускаем бота в отдельном потоке...")

        success = bot_instance.start_polling()

        if success:
            logger.info("✅ Бот успешно запущен!")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Остановка бота по запросу пользователя...")
                bot_instance.stop_polling()
                return True
        else:
            print("❌ Не удалось запустить бота")
            return False

    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Основная функция запуска бота"""
    from shared.utils.config import get_bot_token
    token = get_bot_token()

    if not token or token == 'ваш_токен_бота':
        logger.error("❌ ТОКЕН БОТА НЕ НАЙДЕН!")
        logger.error("👉 Установите TELEGRAM_BOT_TOKEN в настройках Django")
        return False

    logger.info(f"✅ Токен найден: {token[:10]}...")
    logger.info("🔧 Инициализация бота...")

    return initialize_bot()


if __name__ == "__main__":
    success = main()

    if success:
        print("\n" + "=" * 60)
        print("✅ Бот успешно завершил работу")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Бот завершил работу с ошибкой")
        print("=" * 60)
        sys.exit(1)