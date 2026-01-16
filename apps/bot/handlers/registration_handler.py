# bot/handlers/registration_handler.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
GETTING_PHONE, GETTING_EMAIL, CONFIRMATION = range(3)

# Временное хранилище для данных регистрации (в продакшене используйте БД)
registration_data = {}


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации через бота"""
    user = update.effective_user
    message = update.message

    await message.reply_text(
        "👋 Добро пожаловать в регистрацию Profit Hub!\n\n"
        "Я помогу вам создать аккаунт за 2 минуты.\n\n"
        "📱 Для начала, поделитесь вашим номером телефона:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

    # Сохраняем базовые данные пользователя
    context.user_data['telegram_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['first_name'] = user.first_name
    context.user_data['last_name'] = user.last_name

    return GETTING_PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем номер телефона"""
    message = update.message

    phone = None

    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        # Простая валидация номера телефона
        phone_text = message.text.strip()
        if any(char.isdigit() for char in phone_text) and len(phone_text) >= 10:
            phone = phone_text

    if not phone:
        await message.reply_text(
            "❌ Пожалуйста, поделитесь номером телефона используя кнопку ниже или введите номер вручную:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return GETTING_PHONE

    # Форматируем номер телефона
    formatted_phone = format_phone_number(phone)
    context.user_data['phone'] = formatted_phone

    await message.reply_text(
        f"✅ Номер получен: {formatted_phone}\n\n"
        f"📧 Теперь введите ваш email:",
        reply_markup=ReplyKeyboardRemove()
    )

    return GETTING_EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем email"""
    message = update.message
    email = message.text.strip().lower()

    # Простая валидация email
    if '@' not in email or '.' not in email or len(email) < 5:
        await message.reply_text("❌ Пожалуйста, введите корректный email адрес:")
        return GETTING_EMAIL

    context.user_data['email'] = email

    # Показываем сводку данных
    summary = f"""
📋 <b>Проверьте ваши данные:</b>

👤 <b>Имя:</b> {context.user_data.get('first_name', 'Не указано')}
📱 <b>Телефон:</b> {context.user_data.get('phone', 'Не указан')}
📧 <b>Email:</b> {email}

<b>Всё верно?</b>
    """

    await message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Да, всё верно", "❌ Нет, исправить"]],
            resize_keyboard=True,
            one_time_keyboard=True
        ),
        parse_mode='HTML'
    )

    return CONFIRMATION


async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение данных и создание пользователя"""
    message = update.message
    choice = message.text

    if choice == "❌ Нет, исправить":
        await message.reply_text(
            "📱 Введите ваш номер телефона заново:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return GETTING_PHONE

    try:
        # Генерируем код подтверждения
        confirmation_code = str(random.randint(100000, 999999))

        # Сохраняем данные регистрации
        user_data = {
            'telegram_id': context.user_data.get('telegram_id'),
            'username': context.user_data.get('username'),
            'first_name': context.user_data.get('first_name'),
            'last_name': context.user_data.get('last_name'),
            'phone': context.user_data.get('phone'),
            'email': context.user_data.get('email'),
            'confirmation_code': confirmation_code,
            'created_at': datetime.now().isoformat(),
            'chat_id': message.chat_id
        }

        # Сохраняем во временное хранилище (в продакшене используйте БД)
        registration_key = f"reg_{context.user_data['telegram_id']}"
        registration_data[registration_key] = user_data

        # Отправляем код подтверждения
        await message.reply_text(
            f"🎉 <b>Регистрация почти завершена!</b>\n\n"
            f"🔐 <b>Ваш код подтверждения:</b>\n"
            f"<code>{confirmation_code}</code>\n\n"
            f"📝 <b>Что делать дальше:</b>\n"
            f"1. Перейдите на сайт Profit Hub\n"
            f"2. Введите этот код в форме подтверждения\n"
            f"3. Ваш аккаунт будет активирован\n\n"
            f"⏳ <i>Код действителен 30 минут</i>",
            parse_mode='HTML'
        )

        # Также отправляем инструкцию
        await message.reply_text(
            "🌐 <b>Ссылка для подтверждения:</b>\n"
            "http://ваш-сайт.com/confirm-registration/\n\n"
            "💡 <i>Если у вас возникли проблемы, обратитесь в поддержку</i>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )

        logger.info(f"✅ Пользователь {user_data['email']} начал регистрацию. Код: {confirmation_code}")

    except Exception as e:
        logger.error(f"❌ Ошибка завершения регистрации: {e}")
        await message.reply_text(
            "❌ Произошла ошибка при создании аккаунта. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

    # Завершаем диалог
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации"""
    await update.message.reply_text(
        "❌ Регистрация отменена.\n\n"
        "Если передумаете - просто напишите /start",
        reply_markup=ReplyKeyboardRemove()
    )

    # Очищаем данные
    context.user_data.clear()

    return ConversationHandler.END


def format_phone_number(phone):
    """Форматирует номер телефона"""
    # Убираем все нецифровые символы
    cleaned = ''.join(filter(str.isdigit, phone))

    # Форматируем в российский формат
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '7' + cleaned[1:]
    elif cleaned.startswith('+7') and len(cleaned) == 12:
        cleaned = cleaned[1:]

    return f"+{cleaned}"


def get_registration_data(telegram_id):
    """Получает данные регистрации по Telegram ID"""
    registration_key = f"reg_{telegram_id}"
    return registration_data.get(registration_key)


def delete_registration_data(telegram_id):
    """Удаляет данные регистрации после подтверждения"""
    registration_key = f"reg_{telegram_id}"
    if registration_key in registration_data:
        del registration_data[registration_key]


def setup_handlers(application):
    """Настройка обработчиков регистрации"""

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_registration)],
        states={
            GETTING_PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
            GETTING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)
            ],
            CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_data)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)]
    )

    application.add_handler(conv_handler)
    logger.info("✅ Обработчики регистрации настроены для @infopnz58_bot")