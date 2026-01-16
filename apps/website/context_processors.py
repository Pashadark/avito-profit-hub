# dashboard/context_processors.py
from .models import UserProfile

def user_profile(request):
    """Добавляет user_profile в контекст всех шаблонов"""
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return {'user_profile': user_profile}
        except UserProfile.DoesNotExist:
            # Создаем профиль если его нет с ПРАВИЛЬНЫМИ значениями по умолчанию
            user_profile = UserProfile.objects.create(
                user=request.user,
                balance=0,  # ✅ БАЛАНС 0, а не 36427,66
                telegram_chat_id=None,  # ✅ Telegram None, а не -1002580459963
                telegram_notifications=False,
                telegram_verified=False
            )
            return {'user_profile': user_profile}
    return {'user_profile': None}