# dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
from datetime import datetime, timedelta
import re


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    avito_code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = "website"
        verbose_name = "Категория товаров"
        verbose_name_plural = "Категории товаров"


class SearchQuery(models.Model):
    """Модель для хранения поисковых запросов"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, default=1000000)
    min_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    seller_type = models.CharField(max_length=20, default='all')
    check_interval = models.IntegerField(default=30)
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_items_per_hour = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        app_label = "website"
        verbose_name = "Поисковый запрос"
        verbose_name_plural = "Поисковые запросы"
        ordering = ['-created_at']


class FoundItem(models.Model):
    # 🔥 ПОЛЕ ИСТОЧНИКА
    SOURCE_CHOICES = [
        ('avito', 'Avito'),
        ('auto_ru', 'Auto.ru'),
    ]

    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default='avito',
        verbose_name="Источник объявления"
    )

    search_query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name='found_items')
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField(unique=True)
    image_url = models.URLField(blank=True, null=True)
    image_urls = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True, null=True)
    seller_name = models.CharField(max_length=100, blank=True, null=True)
    seller_rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    reviews_count = models.IntegerField(default=0)
    category = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    posted_date = models.CharField(max_length=50, blank=True, null=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit_percent = models.IntegerField(default=0)
    found_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False, verbose_name='В избранном')
    views_count = models.IntegerField(default=0, verbose_name="Количество просмотров")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Цвет")
    condition = models.CharField(max_length=50, default='Не указано', verbose_name='Состояние')
    metro_stations = models.JSONField(default=list, blank=True, verbose_name="Станции метро", help_text="Список станций метро с цветами")
    address = models.TextField(blank=True, null=True, verbose_name="Адрес", help_text="Полный адрес местоположения")
    full_location = models.TextField(blank=True, null=True, verbose_name="Полное местоположение", help_text="Метро + адрес")
    year = models.IntegerField(null=True, blank=True, verbose_name="Год выпуска")
    mileage = models.CharField(max_length=50, blank=True, null=True, verbose_name="Пробег")
    owners = models.CharField(max_length=50, blank=True, null=True, verbose_name="Количество владельцев")
    pts = models.CharField(max_length=50, blank=True, null=True, verbose_name="ПТС")
    ml_freshness_score = models.FloatField(
        default=0.5,
        verbose_name="ML оценка свежести",
        help_text="Предсказание модели MLFreshnessPredictor (0.0-1.0)"
    )

    priority_score = models.FloatField(
        default=50.0,
        verbose_name="Приоритет сортировки",
        help_text="Чем выше - тем раньше показывать"
    )

    is_good_deal = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Хорошая сделка",
        help_text="True - хорошая, False - плохая, null - не размечено"
    )

    freshness_category = models.CharField(
        max_length=50,
        default='unknown',
        verbose_name="Категория свежести",
        help_text="🔥 ОЧЕНЬ СВЕЖИЙ, ✅ СВЕЖИЙ и т.д."
    )
    seller_type = models.CharField(
        max_length=50,
        default='Не указано',
        verbose_name='Тип продавца',
        help_text='Частное лицо или компания',
        blank=True,
        null=True
    )

    seller_avatar = models.URLField(blank=True, null=True, verbose_name="Аватар продавца",
                                    help_text="URL аватарки продавца")

    # 🔥 ДОБАВЛЕНО: Ссылка на профиль продавца
    seller_profile_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Профиль продавца",
        help_text="Ссылка на профиль продавца на Avito"
    )

    # 🔥 ДОБАВЛЕНО: Кто запустил парсер для этого товара
    parsed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кем спарсено",
        related_name='parsed_items',
        help_text="Пользователь, который запустил парсер"
    )

    # Технические характеристики
    engine = models.CharField(max_length=100, blank=True, null=True, verbose_name="Двигатель")
    engine_volume = models.CharField(max_length=20, blank=True, null=True, verbose_name="Объем двигателя")
    engine_power = models.CharField(max_length=20, blank=True, null=True, verbose_name="Мощность двигателя")
    transmission = models.CharField(max_length=50, blank=True, null=True, verbose_name="Коробка передач")
    drive = models.CharField(max_length=50, blank=True, null=True, verbose_name="Привод")
    steering = models.CharField(max_length=50, blank=True, null=True, verbose_name="Руль")
    body = models.CharField(max_length=100, blank=True, null=True, verbose_name="Тип кузова")

    # Дополнительные характеристики
    package = models.CharField(max_length=200, blank=True, null=True, verbose_name="Комплектация")
    tax = models.CharField(max_length=50, blank=True, null=True, verbose_name="Налог")
    customs = models.CharField(max_length=100, blank=True, null=True, verbose_name="Таможня")

    # Идентификаторы
    product_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID объявления")
    price_status = models.CharField(max_length=50, blank=True, null=True, verbose_name="Статус цены")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         verbose_name="Цена со скидкой")

    # Статистика просмотров
    views_today = models.IntegerField(default=0, verbose_name="Просмотров сегодня")

    def __str__(self):
        return self.title

    def clean(self):
        """🛡️ ВАЛИДАЦИЯ ЦЕН - ЗАЩИТА ОТ АСТРОНОМИЧЕСКИХ ЧИСЕЛ"""
        from decimal import Decimal, InvalidOperation

        # Максимально допустимая цена - 10 миллионов рублей
        MAX_PRICE = Decimal('10000000')

        # Функция для безопасной проверки
        def validate_price(value, field_name):
            if value is None or value == '':
                return Decimal('0')

            try:
                decimal_value = Decimal(str(value))
                if decimal_value > MAX_PRICE:
                    print(f"🚨 ЗАЩИТА: Исправлена астрономическая {field_name}: {decimal_value} -> 0")
                    return Decimal('0')
                if decimal_value < Decimal('0'):
                    print(f"🚨 ЗАЩИТА: Исправлена отрицательная {field_name}: {decimal_value} -> 0")
                    return Decimal('0')
                return decimal_value
            except (InvalidOperation, TypeError, ValueError):
                print(f"🚨 ЗАЩИТА: Исправлена некорректная {field_name}: {value} -> 0")
                return Decimal('0')

        # Применяем ко всем ценовым полям
        self.price = validate_price(self.price, 'цена')
        self.target_price = validate_price(self.target_price, 'целевая цена')
        self.profit = validate_price(self.profit, 'прибыль')
        # Также защищаем discount_price
        if self.discount_price:
            self.discount_price = validate_price(self.discount_price, 'цена со скидкой')

    def save(self, *args, **kwargs):
        """Автоматически определяем источник и ВАЛИДИРУЕМ данные перед сохранением"""
        if not self.source:
            if 'auto.ru' in self.url.lower():
                self.source = 'auto_ru'
            else:
                self.source = 'avito'

        # 🛡️ ВСЕГДА вызываем валидацию перед сохранением
        self.clean()
        super().save(*args, **kwargs)

    def get_images(self):
        """Возвращает список всех URL изображений"""
        return self.image_urls if self.image_urls else []

    def get_search_time_display(self):
        """Рассчитывает время поиска - УПРОЩЕННАЯ ВЕРСИЯ"""
        try:
            if not self.posted_date or self.posted_date in ['Дата не указана', 'Не указана', 'None', '']:
                return "Неизвестно"

            if "Сентября" in self.posted_date:
                return "18 д"
            elif "Октября" in self.posted_date:
                return "2 д"
            elif "Вчера" in self.posted_date:
                return "1 д"
            elif "Сегодня" in self.posted_date:
                return "2 ч"
            else:
                return "1 д"

        except Exception:
            return "Неизвестно"

    def get_metro_stations_display(self):
        """Форматирует станции метро для отображения в HTML"""
        if not self.metro_stations:
            return ""

        stations_html = []
        for station in self.metro_stations:
            if isinstance(station, dict):
                name = station.get('name', '')
                color = station.get('color', '#666')
                circle_color = station.get('circle_color', '#fff')

                stations_html.append(
                    f'<span class="metro-station-badge" style="background: {color};">'
                    f'<span class="metro-circle" style="background-color: {circle_color};"></span>'
                    f'{name}'
                    f'</span>'
                )
            else:
                stations_html.append(
                    f'<span class="metro-station-badge">'
                    f'<span class="metro-circle" style="background-color: #fff;"></span>'
                    f'{station}'
                    f'</span>'
                )

        return " ".join(stations_html)

    def get_location_display(self):
        """Форматирует полное местоположение для отображения"""
        if self.full_location:
            return self.full_location

        location_parts = []
        if self.metro_stations:
            metro_names = [station.get('name', '') for station in self.metro_stations]
            location_parts.extend(metro_names)

        if self.address:
            location_parts.append(self.address)

        return " | ".join(location_parts) if location_parts else "Местоположение не указано"

    # 🔥 НОВЫЕ МЕТОДЫ ДЛЯ AUTO.RU
    def is_auto_ru(self):
        """Проверяет, является ли объявление с Auto.ru"""
        return self.source == 'auto_ru' or 'auto.ru' in self.url.lower() if self.url else False

    def is_avito(self):
        """Проверяет, является ли объявление с Avito"""
        return self.source == 'avito' or 'avito.ru' in self.url.lower() if self.url else False

    def get_source_display_name(self):
        """Возвращает отображаемое имя источника"""
        if self.is_auto_ru():
            return "Auto.ru"
        elif self.is_avito():
            return "Avito"
        else:
            return "Неизвестно"

    def get_source_icon(self):
        """Возвращает иконку для источника"""
        if self.is_auto_ru():
            return "ri-steering-2-line"  # Иконка руля для авто
        elif self.is_avito():
            return "ri-shopping-bag-line"  # Иконка покупок для авито
        else:
            return "ri-question-line"

    def has_car_specifications(self):
        """Проверяет, есть ли характеристики автомобиля"""
        return any([
            self.year,
            self.mileage,
            self.engine,
            self.transmission,
            self.drive,
            self.body,
            self.owners,
            self.pts
        ])

    def get_car_specifications(self):
        """Возвращает словарь с характеристиками автомобиля"""
        return {
            'year': self.year,
            'mileage': self.mileage,
            'engine': self.engine,
            'transmission': self.transmission,
            'drive': self.drive,
            'body': self.body,
            'color': self.color,
            'owners': self.owners,
            'condition': self.condition,
            'pts': self.pts,
            'package': self.package,
            'steering': self.steering,
            'tax': self.tax,
            'customs': self.customs
        }

    def get_car_specifications_display(self):
        """🔥 Возвращает отформатированные характеристики автомобиля для отображения"""
        specs = []

        # Основные характеристики
        if self.year:
            specs.append(f"Год: {self.year}")
        if self.mileage:
            specs.append(f"Пробег: {self.mileage}")
        if self.owners:
            specs.append(f"Владельцы: {self.owners}")
        if self.pts:
            specs.append(f"ПТС: {self.pts}")

        # Технические характеристики
        if self.engine:
            specs.append(f"Двигатель: {self.engine}")
        if self.transmission:
            specs.append(f"КПП: {self.transmission}")
        if self.drive:
            specs.append(f"Привод: {self.drive}")
        if self.steering:
            specs.append(f"Руль: {self.steering}")

        # Кузов и комплектация
        if self.body:
            specs.append(f"Кузов: {self.body}")
        if self.package:
            specs.append(f"Комплектация: {self.package}")

        # Дополнительные
        if self.color:
            specs.append(f"Цвет: {self.color}")
        if self.condition and self.condition != 'Не указано':
            specs.append(f"Состояние: {self.condition}")
        if self.tax:
            specs.append(f"Налог: {self.tax}")
        if self.customs:
            specs.append(f"Таможня: {self.customs}")

        return specs

    def get_short_specifications(self):
        """🔥 Возвращает краткие основные характеристики"""
        specs = []
        if self.year:
            specs.append(str(self.year))
        if self.mileage:
            specs.append(self.mileage)
        if self.engine:
            # Берем только объем двигателя если есть
            engine_match = re.search(r'(\d+\.\d+ л)', self.engine)
            if engine_match:
                specs.append(engine_match.group(1))
            else:
                specs.append(self.engine.split(',')[0] if ',' in self.engine else self.engine)
        if self.transmission:
            specs.append(self.transmission)
        return " • ".join(specs)

    class Meta:
        app_label = "website"
        ordering = ['-found_at']
        verbose_name = "Найденный товар"
        verbose_name_plural = "Найденные товары"
        indexes = [
            models.Index(fields=['url']),
            models.Index(fields=['found_at']),
            models.Index(fields=['source']),
            models.Index(fields=['product_id']),
            models.Index(fields=['year']),
            models.Index(fields=['body']),
            models.Index(fields=['package']),
            models.Index(fields=['engine']),
            models.Index(fields=['transmission']),
            models.Index(fields=['source', 'year']),
            models.Index(fields=['source', 'body']),
        ]

class ParserStats(models.Model):
    """Модель для хранения статистики парсера"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_searches = models.IntegerField(default=0)
    successful_searches = models.IntegerField(default=0)
    items_found = models.IntegerField(default=0)
    good_deals_found = models.IntegerField(default=0)
    duplicates_blocked = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    active_queries = models.IntegerField(default=0)
    avg_cycle_time = models.FloatField(default=0.0)
    uptime_seconds = models.IntegerField(default=0)
    last_reset = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def success_rate(self):
        return round((self.successful_searches / self.total_searches * 100) if self.total_searches > 0 else 0, 1)

    def efficiency_rate(self):
        return round((self.good_deals_found / self.items_found * 100) if self.items_found > 0 else 0, 1)

    def duplicate_rate(self):
        """Процент заблокированных дубликатов"""
        total_processed = self.items_found + self.duplicates_blocked
        return round((self.duplicates_blocked / total_processed * 100) if total_processed > 0 else 0, 1)

    def get_uptime_display(self):
        """Форматирует время работы"""
        hours = self.uptime_seconds // 3600
        minutes = (self.uptime_seconds % 3600) // 60
        return f"{hours}ч {minutes}м"

    def get_avg_cycle_time_display(self):
        """Форматирует среднее время цикла"""
        return f"{self.avg_cycle_time:.1f}с"

    def __str__(self):
        return f"Статистика {self.user.username} - {self.created_at.strftime('%d.%m.%Y %H:%M')}"

    class Meta:
        app_label = "website"
        verbose_name = "Статистика парсера"
        verbose_name_plural = "Статистика парсера"
        ordering = ['-created_at']


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Мужской'), ('female', 'Женский')], blank=True,
                              null=True)

    telegram_user_id = models.BigIntegerField(unique=True, blank=True, null=True, db_index=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)

    telegram_verified = models.BooleanField(default=False)
    telegram_verification_code = models.CharField(max_length=10, blank=True, null=True)
    telegram_verification_expires = models.DateTimeField(blank=True, null=True)

    notification_enabled = models.BooleanField(default=True)
    telegram_notifications = models.BooleanField(default=True)

    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def avatar_upload_path(instance, filename):
        """Путь для сохранения аватаров в static/avatars/"""
        ext = filename.split('.')[-1]
        filename = f"user_{instance.user.id}_{int(timezone.now().timestamp())}.{ext}"
        return os.path.join('../../static/avatars', filename)

    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
        verbose_name='Аватар'
    )

    def __str__(self):
        return f"{self.user.username} Profile"

    def save(self, *args, **kwargs):
        """При сохранении удаляем старый аватар если загружается новый"""
        if self.pk:
            try:
                old_avatar = UserProfile.objects.get(pk=self.pk).avatar
                if old_avatar and old_avatar != self.avatar:
                    if os.path.isfile(old_avatar.path):
                        os.remove(old_avatar.path)
            except UserProfile.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete_avatar(self):
        """Удаляет файл аватара"""
        if self.avatar:
            if os.path.isfile(self.avatar.path):
                os.remove(self.avatar.path)
            self.avatar = None
            self.save()

    def generate_verification_code(self):
        """Генерация кода верификации"""
        import random
        import string
        from django.utils import timezone

        code = ''.join(random.choices(string.digits, k=6))
        self.telegram_verification_code = code
        self.telegram_verification_expires = timezone.now() + timezone.timedelta(minutes=10)
        self.telegram_verified = False
        self.save()
        return code

    def verify_telegram_code(self, code):
        """Проверка кода верификации"""
        from django.utils import timezone

        if (self.telegram_verification_code == code and
                self.telegram_verification_expires and
                timezone.now() < self.telegram_verification_expires):
            self.telegram_verified = True
            self.telegram_verification_code = None
            self.telegram_verification_expires = None
            self.save()
            return True
        return False

    @classmethod
    def get_by_telegram_id(cls, telegram_user_id):
        """Получение профиля по Telegram ID"""
        try:
            return cls.objects.get(telegram_user_id=telegram_user_id, telegram_verified=True)
        except cls.DoesNotExist:
            return None

    @classmethod
    def link_telegram_account(cls, user, telegram_user_id, telegram_username=None):
        """Привязка Telegram аккаунта к пользователю Django"""
        profile, created = cls.objects.get_or_create(user=user)
        profile.telegram_user_id = telegram_user_id
        profile.telegram_username = telegram_username
        profile.telegram_verified = True
        profile.save()
        return profile

    @classmethod
    def get_by_verification_code(cls, code):
        """Получение профиля по коду верификации"""
        from django.utils import timezone
        try:
            return cls.objects.get(
                telegram_verification_code=code,
                telegram_verification_expires__gte=timezone.now()
            )
        except cls.DoesNotExist:
            return None

    class Meta:
        app_label = "website"
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ('Базовый', 'Базовый'),
        ('Стандарт', 'Стандарт'),
        ('Профи', 'Профи'),
    ]

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    daily_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.price}₽/мес"

    def save(self, *args, **kwargs):
        if not self.daily_price or self.daily_price == 0:
            self.daily_price = self.calculate_daily_price()
        super().save(*args, **kwargs)

    def calculate_daily_price(self, days_in_month=30):
        """Рассчитывает дневную стоимость в зависимости от дней в месяце"""
        return round(float(self.price) / days_in_month, 2)

    class Meta:
        app_label = "website"
        verbose_name = "Тарифный план"
        verbose_name_plural = "Тарифные планы"


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

    @property
    def days_remaining(self):
        """Количество оставшихся дней подписки"""
        if self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0

    @property
    def is_expired(self):
        """Проверяет истекла ли подписка"""
        return self.end_date < timezone.now()

    def activate(self, duration_days=30):
        """Активирует подписку"""
        self.start_date = timezone.now()
        self.end_date = timezone.now() + timedelta(days=duration_days)
        self.is_active = True
        self.save()

    def deactivate(self):
        """Деактивирует подписку"""
        self.is_active = False
        self.save()

    class Meta:
        app_label = "website"
        verbose_name = "Подписка пользователя"
        verbose_name_plural = "Подписки пользователей"
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['end_date']),
        ]


class VisionFeedback(models.Model):
    FEEDBACK_TYPES = [
        ('positive', 'Положительный'),
        ('negative', 'Отрицательный'),
        ('unsure', 'Не уверен'),
        ('learn_perfect', 'Обучение - отлично'),
        ('learn_partial', 'Обучение - частично'),
        ('learn_wrong', 'Обучение - ошибка'),
        ('manual_description', 'Ручное описание'),
    ]

    user_id = models.BigIntegerField(verbose_name="ID пользователя Telegram")
    item_url = models.CharField(max_length=500, verbose_name="URL товара")
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    description = models.TextField(blank=True, null=True, verbose_name="Описание пользователя")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "website"
        verbose_name = "Обратная связь Vision"
        verbose_name_plural = "Обратная связь Vision"
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['item_url']),
            models.Index(fields=['created_at']),
            models.Index(fields=['feedback_type']),
        ]

    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.item_url}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]

    TYPE_CHOICES = [
        ('topup', 'Пополнение'),
        ('subscription', 'Подписка'),
        ('refund', 'Возврат'),
        ('daily_charge', 'Ежедневное списание'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.update_user_balance()
        super().save(*args, **kwargs)

    def update_user_balance(self):
        """Обновляет баланс пользователя на основе транзакции"""
        try:
            user_profile, created = UserProfile.objects.get_or_create(user=self.user)

            if self.transaction_type in ['topup', 'refund']:
                user_profile.balance += self.amount
            elif self.transaction_type in ['subscription', 'daily_charge']:
                user_profile.balance -= abs(self.amount)

            user_profile.save()

        except Exception as e:
            print(f"Ошибка обновления баланса: {e}")

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.transaction_type}"

    class Meta:
        app_label = "website"
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"


class TrackedProduct(models.Model):
    name = models.CharField(max_length=255)
    avito_id = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True)
    image_url = models.URLField(blank=True, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    target_buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    target_sell_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = "website"
        verbose_name = "Отслеживаемый товар"
        verbose_name_plural = "Отслеживаемые товары"


class ParserSettings(models.Model):
    SELLER_TYPES = [
        ('all', 'Все продавцы'),
        ('private', 'Частные лица'),
        ('reseller', 'Перекупщики'),
    ]

    SITE_CHOICES = [
        ('avito', 'Avito'),
        ('auto.ru', 'Auto.ru'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField('Название настроек', max_length=100, default='Основные настройки')
    keywords = models.TextField('Ключевые слова')
    exclude_keywords = models.TextField('Исключить слова', blank=True, null=True)
    min_price = models.IntegerField('Минимальная цена', default=0)
    max_price = models.IntegerField('Максимальная цена', default=100000)
    min_rating = models.FloatField('Минимальный рейтинг', default=4.0)
    seller_type = models.CharField('Тип продавца', max_length=10, choices=SELLER_TYPES, default='all')
    check_interval = models.IntegerField('Интервал проверки (минуты)', default=30)
    max_items_per_hour = models.IntegerField('Максимум товаров в час', default=10)
    browser_windows = models.IntegerField('Количество окон браузера', default=1)
    is_active = models.BooleanField('Автопоиск активен', default=True)
    is_default = models.BooleanField('По умолчанию', default=False)
    site = models.CharField('Сайт для поиска', max_length=20, choices=SITE_CHOICES, default='avito')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    city = models.CharField(max_length=100, default='Москва', verbose_name='Город поиска', help_text='Город для поиска товаров (например: Москва, Санкт-Петербург, Краснодар)', blank=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            if self.pk:
                ParserSettings.objects.filter(
                    user=self.user,
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
            else:
                ParserSettings.objects.filter(
                    user=self.user,
                    is_default=True
                ).update(is_default=False)
        super().save(*args, **kwargs)

    class Meta:
        app_label = "website"
        verbose_name = "Настройки парсера"
        verbose_name_plural = "Настройки парсера"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_per_user'
            )
        ]

    def __str__(self):
        return f'{self.name} - {self.user.username}'

    @property
    def keywords_list(self):
        if self.keywords:
            return [k.strip() for k in self.keywords.split(',') if k.strip()]
        return []

    @property
    def exclude_keywords_list(self):
        if self.exclude_keywords:
            return [k.strip() for k in self.exclude_keywords.split(',') if k.strip()]
        return []

    # 🔥 ДОБАВЛЕН НОВЫЙ МЕТОД ДЛЯ УДОБСТВА
    @property
    def site_display_name(self):
        """Возвращает отображаемое имя сайта"""
        return dict(self.SITE_CHOICES).get(self.site, 'Avito')


class TradeDeal(models.Model):
    STATUS_CHOICES = [
        ('monitoring', 'Мониторинг'),
        ('purchased', 'Куплено'),
        ('listed', 'Выставлено'),
        ('sold', 'Продано'),
        ('cancelled', 'Отменено'),
    ]

    product = models.ForeignKey(TrackedProduct, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='monitoring')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    profit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_profit(self):
        if self.purchase_price and self.sale_price:
            self.profit = self.sale_price - self.purchase_price
            self.save()

    def __str__(self):
        return f"{self.product.name} - {self.get_status_display()}"

    class Meta:
        app_label = "website"
        verbose_name = "Торговая сделка"
        verbose_name_plural = "Торговые сделки"


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=20.0)
    max_item_price = models.DecimalField(max_digits=10, decimal_places=2, default=10000.0)
    min_item_price = models.DecimalField(max_digits=10, decimal_places=2, default=100.0)
    update_frequency = models.IntegerField(default=3600)
    receive_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Настройки {self.user.username}"

    class Meta:
        app_label = "website"
        verbose_name = "Настройки пользователя"
        verbose_name_plural = "Настройки пользователей"


class PriceHistory(models.Model):
    product = models.ForeignKey(TrackedProduct, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "website"
        verbose_name = "История цен"
        verbose_name_plural = "История цен"
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.product.name} - {self.price} руб."


class TodoBoard(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        app_label = "website"
        verbose_name = "Доска задач"
        verbose_name_plural = "Доски задач"


class NotificationCache(models.Model):
    """Модель для хранения кэша отправленных уведомлений"""
    product_id = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="ID товара")
    normalized_url = models.CharField(max_length=500, db_index=True, verbose_name="Нормализованный URL")
    product_name = models.CharField(max_length=255, verbose_name="Название товара")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Время отправки")
    expires_at = models.DateTimeField(verbose_name="Истекает в", help_text="Кэш очищается через 24 часа")

    class Meta:
        app_label = "website"
        verbose_name = "Кэш уведомлений"
        verbose_name_plural = "Кэш уведомлений"
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['normalized_url']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.product_name} ({self.product_id})"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @classmethod
    def is_duplicate(cls, product_id, normalized_url):
        """Проверяет дубликат по ID товара и URL"""
        from django.utils import timezone
        cls.clean_expired()
        return cls.objects.filter(
            models.Q(product_id=product_id) | models.Q(normalized_url=normalized_url),
            expires_at__gt=timezone.now()
        ).exists()

    @classmethod
    def add_to_cache(cls, product_id, normalized_url, product_name):
        """Добавляет запись в кэш"""
        from django.utils import timezone
        cls.objects.filter(
            models.Q(product_id=product_id) | models.Q(normalized_url=normalized_url)
        ).delete()
        return cls.objects.create(
            product_id=product_id,
            normalized_url=normalized_url,
            product_name=product_name
        )

    @classmethod
    def clean_expired(cls):
        """Очищает устаревшие записи"""
        from django.utils import timezone
        expired_count = cls.objects.filter(expires_at__lte=timezone.now()).delete()[0]
        if expired_count > 0:
            print(f"🧹 Очищено {expired_count} устаревших записей кэша")

    @classmethod
    def get_cache_stats(cls):
        """Возвращает статистику кэша"""
        from django.utils import timezone
        total = cls.objects.count()
        active = cls.objects.filter(expires_at__gt=timezone.now()).count()
        expired = total - active
        return {
            'total': total,
            'active': active,
            'expired': expired
        }


class TodoCard(models.Model):
    STATUS_CHOICES = [
        ('todo', 'К выполнению'),
        ('in_progress', 'В процессе'),
        ('done', 'Выполнено'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    board = models.ForeignKey(TodoBoard, on_delete=models.CASCADE, related_name='cards')
    due_date = models.DateTimeField(blank=True, null=True)
    labels = models.JSONField(default=list, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_todos')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_todos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    time_in_progress = models.DurationField(blank=True, null=True)
    card_order = models.IntegerField(default=0)

    class Meta:
        app_label = "website"
        verbose_name = "Карточка задачи"
        verbose_name_plural = "Карточки задач"
        ordering = ['card_order', 'created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == 'in_progress' and not self.started_at:
            self.started_at = timezone.now()

        if self.status == 'done' and self.started_at and not self.completed_at:
            self.completed_at = timezone.now()
            if self.started_at:
                self.time_in_progress = self.completed_at - self.started_at

        if self.status != 'in_progress' and self.started_at and not self.completed_at:
            current_time_in_progress = timezone.now() - self.started_at
            if self.time_in_progress:
                self.time_in_progress += current_time_in_progress
            else:
                self.time_in_progress = current_time_in_progress
            self.started_at = None

        super().save(*args, **kwargs)

    def get_completion_time(self):
        """Возвращает общее время выполнения задачи"""
        if self.status == 'done' and self.time_in_progress:
            return self.format_duration(self.time_in_progress)

        if self.status == 'in_progress' and self.started_at:
            current_duration = timezone.now() - self.started_at
            if self.time_in_progress:
                current_duration += self.time_in_progress
            return f"В работе: {self.format_duration(current_duration)}"

        return None

    def get_current_time_in_progress(self):
        """Возвращает текущее время в статусе 'В процессе'"""
        if self.status == 'in_progress' and self.started_at:
            current_duration = timezone.now() - self.started_at
            if self.time_in_progress:
                current_duration += self.time_in_progress
            return current_duration
        return self.time_in_progress

    def format_duration(self, duration):
        """Форматирует duration в читаемый вид"""
        total_seconds = int(duration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if days > 0:
            return f"{days}д {hours}ч {minutes}м"
        elif hours > 0:
            return f"{hours}ч {minutes}м {seconds}с"
        elif minutes > 0:
            return f"{minutes}м {seconds}с"
        else:
            return f"{seconds}с"

    @property
    def is_overdue(self):
        """Просрочена ли задача"""
        if self.due_date and timezone.now() > self.due_date and self.status != 'done':
            return True
        return False


# ============================================================================
# 🔥 МОДЕЛЬ ДЛЯ ПРОВЕРКИ ДУБЛИКАТОВ (ТЕХНИЧЕСКАЯ)
# ============================================================================

class Deal(models.Model):
    """
    🎯 УЛЬТРА-ЛЕГКАЯ модель ТОЛЬКО для проверки дубликатов.
    Не содержит лишних данных - только ID и метаданные для парсера.
    """

    STATUS_CHOICES = [
        ('fresh', 'Свежий'),
        ('processing', 'В обработке'),
        ('processed', 'Обработан'),
        ('error', 'Ошибка'),
        ('duplicate', 'Дубликат'),
    ]

    # 🔥 ОСНОВНОЙ ИДЕНТИФИКАТОР
    avito_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="ID объявления на Avito"
    )

    # 🔥 URL для быстрой проверки
    url = models.CharField(
        max_length=500,
        db_index=True,
        verbose_name="URL объявления"
    )

    # 🔥 СТАТУС обработки
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='fresh',
        verbose_name="Статус обработки"
    )

    # 🔥 ML СВЕЖЕСТЬ
    ml_freshness = models.FloatField(
        default=0.5,
        verbose_name="ML оценка свежести"
    )

    # 🔥 ПРИОРИТЕТ для сортировки
    priority = models.FloatField(
        default=50.0,
        verbose_name="Приоритет"
    )

    # 🔥 ВРЕМЕННЫЕ МЕТКИ
    first_seen = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время первого обнаружения"
    )

    last_seen = models.DateTimeField(
        auto_now=True,
        verbose_name="Время последней проверки"
    )

    # 🔥 СЧЕТЧИК повторных обнаружений
    seen_count = models.IntegerField(
        default=1,
        verbose_name="Сколько раз видели"
    )

    # 🔥 ТЕХНИЧЕСКИЕ ПОЛЯ
    source = models.CharField(
        max_length=10,
        choices=FoundItem.SOURCE_CHOICES,
        default='avito',
        verbose_name="Источник"
    )

    class Meta:
        app_label = "website"
        verbose_name = "Техническая сделка"
        verbose_name_plural = "Технические сделки"
        ordering = ['-first_seen']

    def __str__(self):
        return f"#{self.avito_id} [{self.status}]"

    @classmethod
    def is_duplicate(cls, avito_id: str) -> bool:
        """Быстрая проверка дубликата - любая запись с этим ID считается дубликатом"""
        return cls.objects.filter(avito_id=avito_id).exists()

    @classmethod
    def exists_in_db(cls, avito_id: str) -> bool:
        """Проверяет есть ли запись с таким ID (любой статус) - синоним для is_duplicate"""
        return cls.is_duplicate(avito_id)