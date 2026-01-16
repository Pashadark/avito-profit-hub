from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect

def safe_console_log(message):
    """Безопасное логирование до инициализации Django"""
    try:
        from dashboard.console_manager import add_to_console
        add_to_console(message)
    except:
        print(f"[SAFE_LOG] {message}")

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from datetime import timedelta

from .models import (
    UserProfile, SubscriptionPlan, UserSubscription, Transaction,
    SearchQuery, FoundItem, ParserSettings, TrackedProduct, TradeDeal,
    ProductCategory, PriceHistory, UserSettings, ParserStats, NotificationCache
)

# Inline для профиля пользователя
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ('balance', 'telegram_chat_id', 'telegram_notifications', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

# Кастомный UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_balance', 'get_subscription', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_balance(self, obj):
        try:
            profile = obj.userprofile
            return f"{profile.balance} ₽"
        except UserProfile.DoesNotExist:
            return "0 ₽"

    get_balance.short_description = 'Баланс'
    get_balance.admin_order_field = 'userprofile__balance'

    def get_subscription(self, obj):
        try:
            subscription = UserSubscription.objects.filter(user=obj, is_active=True).first()
            if subscription and subscription.end_date >= timezone.now():
                return f"{subscription.plan.name} (до {subscription.end_date.strftime('%d.%m.%Y')})"
            return "Не активна"
        except:
            return "Ошибка"

    get_subscription.short_description = 'Подписка'

# Admin для UserProfile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_display', 'telegram_connected', 'created_at')
    list_filter = ('telegram_notifications', 'created_at')
    search_fields = ('user__username', 'user__email', 'telegram_chat_id')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['add_balance', 'reset_balance']

    def balance_display(self, obj):
        return f"{obj.balance} ₽"

    balance_display.short_description = 'Баланс'
    balance_display.admin_order_field = 'balance'

    def telegram_connected(self, obj):
        if obj.telegram_chat_id:
            return "✅ Подключен"
        return "❌ Не подключен"

    telegram_connected.short_description = 'Telegram'

    def add_balance(self, request, queryset):
        if 'apply' in request.POST:
            amount = request.POST.get('amount', 0)
            try:
                amount = float(amount)
                for profile in queryset:
                    profile.balance += amount
                    profile.save()

                    # Создаем транзакцию
                    Transaction.objects.create(
                        user=profile.user,
                        amount=amount,
                        transaction_type='topup',
                        status='completed',
                        description=f"Пополнение баланса администратором. +{amount} ₽"
                    )

                self.message_user(request, f"Баланс пополнен на {amount} ₽ для {queryset.count()} пользователей")
                return HttpResponseRedirect(request.get_full_path())
            except ValueError:
                self.message_user(request, "Неверная сумма", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())

        return render(request, 'admin/add_balance.html', context={
            'users': queryset,
            'action': 'add_balance'
        })

    add_balance.short_description = "Пополнить баланс"

    def reset_balance(self, request, queryset):
        for profile in queryset:
            old_balance = profile.balance
            profile.balance = 0
            profile.save()

            Transaction.objects.create(
                user=profile.user,
                amount=-old_balance,
                transaction_type='refund',
                status='completed',
                description=f"Сброс баланса администратором"
            )

        self.message_user(request, f"Баланс сброшен для {queryset.count()} пользователей")

    reset_balance.short_description = "Сбросить баланс"

# Admin для тарифных планов
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price_display', 'is_active', 'created_at')
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name',)

    def price_display(self, obj):
        return f"{obj.price} ₽/мес"

    price_display.short_description = 'Цена'

# Admin для кэша уведомлений
@admin.register(NotificationCache)
class NotificationCacheAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'product_name', 'sent_at', 'expires_at']
    list_filter = ['sent_at', 'expires_at']
    search_fields = ['product_id', 'product_name', 'normalized_url']
    readonly_fields = ['sent_at']

    def has_add_permission(self, request):
        return False  # Запрещаем ручное добавление

# Admin для подписок пользователей
@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active', 'auto_renew', 'days_remaining')
    list_filter = ('is_active', 'auto_renew', 'plan', 'start_date')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)
    actions = ['activate_subscriptions', 'deactivate_subscriptions', 'extend_subscriptions']

    def days_remaining(self, obj):
        if obj.end_date and obj.is_active:
            remaining = (obj.end_date - timezone.now()).days
            if remaining > 0:
                return f"{remaining} дней"
            return "Истекла"
        return "-"

    days_remaining.short_description = 'Осталось дней'

    def activate_subscriptions(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} подписок активировано")

    activate_subscriptions.short_description = "Активировать подписки"

    def deactivate_subscriptions(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} подписок деактивировано")

    deactivate_subscriptions.short_description = "Деактивировать подписки"

    def extend_subscriptions(self, request, queryset):
        if 'apply' in request.POST:
            days = int(request.POST.get('days', 30))
            for subscription in queryset:
                subscription.end_date += timedelta(days=days)
                subscription.save()

            self.message_user(request, f"Подписки продлены на {days} дней для {queryset.count()} пользователей")
            return HttpResponseRedirect(request.get_full_path())

        return render(request, 'admin/extend_subscriptions.html', context={
            'subscriptions': queryset,
            'action': 'extend_subscriptions'
        })

    extend_subscriptions.short_description = "Продлить подписки"

# Admin для транзакций
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'transaction_type', 'status', 'created_at', 'description_short')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def amount_display(self, obj):
        if obj.amount > 0:
            return format_html('<span style="color: green;">+{} ₽</span>', obj.amount)
        else:
            return format_html('<span style="color: red;">{} ₽</span>', obj.amount)

    amount_display.short_description = 'Сумма'
    amount_display.admin_order_field = 'amount'

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description

    description_short.short_description = 'Описание'

# Admin для поисковых запросов
@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'category', 'min_price', 'max_price', 'target_price', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('user__username', 'name', 'category')
    readonly_fields = ('created_at', 'updated_at')

# Admin для найденных товаров
@admin.register(FoundItem)
class FoundItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price_display', 'search_query_user', 'city', 'found_at', 'profit_display')
    list_filter = ('city', 'found_at', 'is_notified')
    search_fields = ('title', 'search_query__user__username', 'city')
    readonly_fields = ('found_at',)
    date_hierarchy = 'found_at'

    def price_display(self, obj):
        return f"{obj.price} ₽"

    price_display.short_description = 'Цена'

    def search_query_user(self, obj):
        return obj.search_query.user.username

    search_query_user.short_description = 'Пользователь'

    def profit_display(self, obj):
        if obj.profit > 0:
            return format_html('<span style="color: green;">+{} ₽</span>', obj.profit)
        else:
            return f"{obj.profit} ₽"

    profit_display.short_description = 'Прибыль'

# Admin для настроек парсера
@admin.register(ParserSettings)
class ParserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'keywords_short', 'min_price', 'max_price', 'is_active', 'is_default', 'created_at')
    list_filter = ('is_active', 'is_default', 'seller_type', 'created_at')
    search_fields = ('user__username', 'name', 'keywords')
    readonly_fields = ('created_at', 'updated_at')

    def keywords_short(self, obj):
        return obj.keywords[:50] + '...' if len(obj.keywords) > 50 else obj.keywords

    keywords_short.short_description = 'Ключевые слова'

# Admin для отслеживаемых товаров
@admin.register(TrackedProduct)
class TrackedProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_price_display', 'target_buy_price_display', 'target_sell_price_display',
                    'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'avito_id')

    def current_price_display(self, obj):
        return f"{obj.current_price} ₽"

    current_price_display.short_description = 'Текущая цена'

    def target_buy_price_display(self, obj):
        return f"{obj.target_buy_price} ₽"

    target_buy_price_display.short_description = 'Цена покупки'

    def target_sell_price_display(self, obj):
        return f"{obj.target_sell_price} ₽"

    target_sell_price_display.short_description = 'Цена продажи'

# Admin для статистики парсера
@admin.register(ParserStats)
class ParserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_searches', 'successful_searches', 'items_found', 'good_deals_found', 'duplicates_blocked', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

# Admin для категорий товаров
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'avito_code')
    search_fields = ('name',)

# Admin для торговых сделок
@admin.register(TradeDeal)
class TradeDealAdmin(admin.ModelAdmin):
    list_display = ('product', 'status', 'purchase_price', 'sale_price', 'profit')
    list_filter = ('status',)
    search_fields = ('product__name',)

# Admin для настроек пользователей
@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'profit_margin', 'receive_notifications')
    search_fields = ('user__username',)

# Admin для истории цен
@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('product__name',)
    readonly_fields = ('recorded_at',)
    date_hierarchy = 'recorded_at'

# Перерегистрируем User с кастомным админом
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Кастомный заголовок админки
admin.site.site_header = "Profit Hub Administration"
admin.site.site_title = "Profit Hub Admin"
admin.site.index_title = "Добро пожаловать в панель управления Селибри!"