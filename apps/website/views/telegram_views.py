from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth import get_user_model
import json
import logging
import asyncio
import random
from datetime import timedelta
from telegram import Bot
from telegram.error import TelegramError

from apps.website.models import UserProfile
from apps.website.console_manager import add_to_console
from shared.utils.config import get_bot_token, get_chat_id

logger = logging.getLogger(__name__)


# ========== TELEGRAM ИНТЕГРАЦИЯ ==========

@require_POST
@csrf_exempt
def test_bot_connection(request):
    """🤖 Тестирование соединения с Telegram ботом

    🔧 Проверка настроек токена и chat_id
    📨 Отправка тестового сообщения в группу
    ✅ Верификация доступности бота
    """
    try:
        logger.info("🔄 Начало теста бота...")

        token = get_bot_token()
        chat_id = get_chat_id()

        logger.info(f"🔧 Токен: {token[:10]}...")
        logger.info(f"🔧 Chat ID: {chat_id}")

        if not token or token == 'ваш_токен_бота':
            logger.error("❌ Токен бота не настроен")
            return JsonResponse({
                'status': 'error',
                'message': 'Токен бота не настроен. Проверьте utils/config.py'
            })

        if not chat_id:
            logger.error("❌ Chat ID не настроен")
            return JsonResponse({
                'status': 'error',
                'message': 'Chat ID не настроен. Проверьте utils/config.py'
            })

        async def send_telegram_message():
            try:
                bot = Bot(token=token)

                bot_info = await bot.get_me()
                logger.info(f"✅ Бот: {bot_info.first_name} (@{bot_info.username})")

                message = "🎉 Ура мы работаем! Тестовое сообщение связи пришло!"
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )

                logger.info("✅ Сообщение отправлено в Telegram!")
                return True

            except TelegramError as e:
                logger.error(f"❌ Ошибка Telegram: {e}")
                return False
            except Exception as e:
                logger.error(f"❌ Ошибка отправки: {e}")
                return False

        success = asyncio.run(send_telegram_message())
        logger.info(f"✅ Результат отправки: {success}")

        if success:
            logger.info("✅ Тест бота завершен успешно")
            return JsonResponse({
                'status': 'success',
                'message': 'Тестовое сообщение отправлено в группу!'
            })
        else:
            logger.error("❌ Тест бота завершен с ошибкой")
            return JsonResponse({
                'status': 'error',
                'message': 'Ошибка отправки сообщения. Проверьте настройки бота.'
            })

    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка: {str(e)}'
        })


@login_required
def save_telegram_settings(request):
    """💾 Сохранение настроек Telegram

    💬 Сохранение chat_id для уведомлений
    🔔 Включение/отключение уведомлений
    """
    if request.method == 'POST':
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_profile.telegram_chat_id = request.POST.get('telegram_chat_id', '')
        user_profile.telegram_notifications = request.POST.get('telegram_notifications') == 'on'
        user_profile.save()
        messages.success(request, 'Настройки Telegram сохранены!')
    return redirect('settings')


@require_POST
@csrf_exempt
@login_required
def generate_telegram_code(request):
    """🔢 Генерация нового кода для привязки Telegram

    🎲 Генерация 6-значного кода
    ⏰ Срок действия 10 минут
    💾 Сохранение во временный профиль
    """
    try:
        temp_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'telegram_verified': False}
        )

        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        temp_profile.telegram_verification_code = code
        temp_profile.telegram_verification_expires = timezone.now() + timedelta(minutes=10)
        temp_profile.telegram_verified = False
        temp_profile.save()

        return JsonResponse({
            'status': 'success',
            'code': code,
            'expires_in': '10 минут'
        })

    except Exception as e:
        logger.error(f"Ошибка генерации кода Telegram: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_exempt
@login_required
def verify_telegram_code(request):
    """✅ Верификация кода Telegram из веб-интерфейса

    🔍 Поиск профиля с активным кодом
    ⏰ Проверка срока действия кода
    🔗 Привязка Telegram к аккаунту
    """
    try:
        data = json.loads(request.body)
        code = data.get('code')

        if not code:
            return JsonResponse({'status': 'error', 'message': 'Код не указан'})

        from django.db import transaction

        with transaction.atomic():
            profile = UserProfile.objects.filter(
                telegram_verification_code=code,
                telegram_verification_expires__gte=timezone.now()
            ).first()

            if profile:
                if profile.verify_telegram_code(code):
                    if profile.user != request.user:
                        new_profile, created = UserProfile.objects.get_or_create(user=request.user)
                        new_profile.telegram_user_id = profile.telegram_user_id
                        new_profile.telegram_username = profile.telegram_username
                        new_profile.telegram_verified = True
                        new_profile.telegram_notifications = True
                        new_profile.save()

                        profile.delete()
                    else:
                        new_profile = profile

                    return JsonResponse({
                        'status': 'success',
                        'message': 'Telegram успешно привязан!',
                        'telegram_user_id': new_profile.telegram_user_id,
                        'telegram_username': new_profile.telegram_username
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': 'Неверный код верификации'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Код не найден или устарел'})

    except Exception as e:
        logger.error(f"Ошибка верификации кода: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ошибка сервера: {str(e)}'})


@require_GET
@login_required
def get_telegram_status(request):
    """📱 Получение статуса привязки Telegram

    🔍 Проверка верификации Telegram
    👤 Возвращает данные привязанного аккаунта
    """
    try:
        user_profile = UserProfile.objects.filter(user=request.user).first()

        if user_profile and user_profile.telegram_verified:
            return JsonResponse({
                'status': 'success',
                'telegram_verified': True,
                'telegram_user_id': user_profile.telegram_user_id,
                'telegram_username': user_profile.telegram_username,
                'telegram_chat_id': user_profile.telegram_chat_id
            })
        else:
            return JsonResponse({
                'status': 'success',
                'telegram_verified': False,
                'message': 'Telegram не привязан'
            })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_POST
@csrf_exempt
@login_required
def unlink_telegram(request):
    """🔗 Отвязка Telegram от аккаунта

    🗑️ Очистка всех Telegram данных
    🔄 Сброс статуса верификации
    """
    try:
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile:
            user_profile.telegram_user_id = None
            user_profile.telegram_username = None
            user_profile.telegram_verified = False
            user_profile.telegram_verification_code = None
            user_profile.telegram_verification_expires = None
            user_profile.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Telegram успешно отвязан'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Профиль не найден'
            })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def create_user_from_telegram(user_data, chat_id):
    """🤖 Создает пользователя из данных Telegram

    🎲 Генерация случайного пароля
    🔢 Создание кода подтверждения
    💾 Сохранение в кэш на 10 минут
    """
    try:
        User = get_user_model()

        password = User.objects.make_random_password()

        user = User.objects.create_user(
            username=user_data.get('email'),
            email=user_data.get('email'),
            password=password,
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            phone=user_data.get('phone')
        )

        confirmation_code = str(random.randint(100000, 999999))

        from django.core.cache import cache
        cache_key = f"reg_code_{user.id}"
        cache.set(cache_key, {
            'code': confirmation_code,
            'user_id': user.id,
            'created_at': timezone.now().isoformat()
        }, 600)

        logger.info(f"✅ Создан пользователь {user.email}, код: {confirmation_code}")

        return user, confirmation_code

    except IntegrityError as e:
        logger.error(f"❌ Ошибка целостности при создании пользователя: {e}")
        return None, None
    except Exception as e:
        logger.error(f"❌ Ошибка создания пользователя: {e}")
        return None, None