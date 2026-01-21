import os
import logging

# ✅ Создаем логгер для менеджера настроек
logger = logging.getLogger('settings.system')


# Временная заглушка для add_to_console в settings_manager
def add_to_console(message, level="INFO", color=None):
    logger.info(f"[SETTINGS] {message}")


class SettingsManager:
    """Менеджер настроек парсера"""

    def __init__(self):
        self.search_queries = []
        self.exclude_keywords = []
        self.browser_windows = 1
        self.min_price = 0
        self.max_price = 100000
        self.min_rating = 4.0
        self.seller_type = 'all'
        self.city = "Москва"  # ← ДОБАВЬТЕ ЭТУ СТРОКУ!

        # Не загружаем настройки автоматически - будет загружено позже
        logger.info("✅ Менеджер настроек инициализирован (настройки загрузятся позже)")

    # В методе load_initial_settings добавь город:
    def load_initial_settings(self):
        """Загружает начальные настройки после инициализации Django (СИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import ParserSettings
            from django.contrib.auth.models import User

            user = User.objects.first()
            if user:
                parser_settings = ParserSettings.objects.filter(user=user, is_default=True).first()
                if not parser_settings:
                    parser_settings = ParserSettings.objects.filter(user=user).first()

                if parser_settings:
                    self.search_queries = [keyword.strip() for keyword in parser_settings.keywords.split(',') if
                                           keyword.strip()]
                    self.exclude_keywords = [keyword.strip() for keyword in parser_settings.exclude_keywords.split(',')
                                             if keyword.strip()] if parser_settings.exclude_keywords else []
                    self.browser_windows = parser_settings.browser_windows or 1
                    self.min_price = parser_settings.min_price
                    self.max_price = parser_settings.max_price
                    self.min_rating = parser_settings.min_rating
                    self.seller_type = parser_settings.seller_type
                    # 🔥 ДОБАВИЛ ГОРОД
                    self.city = parser_settings.city or 'Москва'

                    logger.info(f"✅ ЗАГРУЖЕНЫ НАСТРОЙКИ: {self.search_queries}")
                    logger.info(f"✅ Город: {self.city}")
                    logger.info(f"✅ Исключаемые слова: {self.exclude_keywords}")
                else:
                    self.search_queries = self.get_default_queries()
                    self.city = 'Москва'  # 🔥 Значение по умолчанию
                    logger.warning(f"⚠️ НАСТРОЙКИ НЕ НАЙДЕНЫ, ИСПОЛЬЗУЮТСЯ: {self.search_queries}")
            else:
                self.search_queries = self.get_default_queries()
                self.city = 'Москва'  # 🔥 Значение по умолчанию
                logger.warning(f"⚠️ ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН: {self.search_queries}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки начальных настроек: {e}")
            self.search_queries = self.get_default_queries()
            self.city = 'Москва'

    def get_default_queries(self):
        """Возвращает default запросы"""
        return ["Видеокарта 16", "iphone 16 бу", "be quiet винтелятор"]

    def load_search_queries(self):
        """Загружает поисковые запросы из базы данных (СИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import ParserSettings
            from django.contrib.auth.models import User

            user = User.objects.first()
            if not user:
                logger.warning("⚠️ Пользователи не найдены")
                return self.get_default_queries()

            try:
                settings = ParserSettings.objects.get(user=user)
                if settings.keywords:
                    keywords = [keyword.strip() for keyword in settings.keywords.split(',') if keyword.strip()]
                    exclude_keywords = [keyword.strip() for keyword in settings.exclude_keywords.split(',') if
                                        keyword.strip()] if settings.exclude_keywords else []

                    logger.info(f"✅ Загружены ключевые слова из базы: {keywords}")
                    logger.info(f"✅ Исключаемые слова: {exclude_keywords}")

                    self.min_price = settings.min_price
                    self.max_price = settings.max_price
                    self.min_rating = settings.min_rating
                    self.seller_type = settings.seller_type
                    self.exclude_keywords = exclude_keywords
                    self.browser_windows = settings.browser_windows or 1

                    return keywords
                else:
                    return self.get_default_queries()

            except ParserSettings.DoesNotExist:
                logger.warning("⚠️ Настройки парсера не найдены, создаем стандартные...")
                settings = ParserSettings.objects.create(
                    user=user,
                    keywords="Видеокарта, iPhone, кроссовки",
                    exclude_keywords="б/у, сломан, нерабочий",
                    min_price=0,
                    max_price=100000,
                    min_rating=4.0,
                    seller_type='all',
                    check_interval=30,
                    max_items_per_hour=10,
                    browser_windows=1,
                    is_active=True
                )
                return ["Видеокарта", "iPhone", "кроссовки"]

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки настроек из базы: {e}")
            return self.get_default_queries()

    def update_settings(self, settings_data):
        """Обновляет настройки парсера в реальном времени (СИНХРОННАЯ ВЕРСИЯ)"""
        logger.info(f"🔧 ВЫЗВАН update_settings с данными: {settings_data}")

        try:
            from apps.website.models import ParserSettings
            from django.contrib.auth.models import User

            user = User.objects.first()
            if user:
                try:
                    parser_settings = ParserSettings.objects.filter(user=user).first()
                    if not parser_settings:
                        logger.info("❌ Настройки не найдены, создаем новые...")
                        parser_settings = ParserSettings.objects.create(
                            user=user,
                            keywords=settings_data.get('keywords', ''),
                            exclude_keywords=settings_data.get('exclude_keywords', ''),
                            min_price=settings_data.get('min_price', 0),
                            max_price=settings_data.get('max_price', 100000),
                            min_rating=settings_data.get('min_rating', 4.0),
                            seller_type=settings_data.get('seller_type', 'all'),
                            check_interval=settings_data.get('check_interval', 30),
                            max_items_per_hour=settings_data.get('max_items_per_hour', 10),
                            browser_windows=settings_data.get('browser_windows', 1),
                            # 🔥 ДОБАВИЛ ГОРОД
                            city=settings_data.get('city', 'Москва'),
                            is_active=settings_data.get('is_active', True)
                        )
                        logger.info(f"✅ Созданы новые настройки в базе: {parser_settings.keywords}")
                    else:
                        logger.info(f"🔧 Найдены существующие настройки: {parser_settings.keywords}")

                    # 🔥 ОБНОВЛЕНИЕ ВСЕХ ПОЛЕЙ (включая город)
                    update_fields = [
                        'keywords', 'exclude_keywords', 'min_price', 'max_price',
                        'min_rating', 'seller_type', 'check_interval',
                        'max_items_per_hour', 'browser_windows', 'city', 'is_active'
                    ]

                    for field in update_fields:
                        if field in settings_data:
                            setattr(parser_settings, field, settings_data[field])
                            logger.info(f"   Обновлено поле {field}: {settings_data[field]}")

                    parser_settings.save()
                    logger.info(f"✅ Настройки сохранены в базу: {parser_settings.keywords}")

                except Exception as e:
                    logger.error(f"❌ Ошибка работы с настройками: {e}")
                    import traceback
                    traceback.print_exc()

            # Обновляем текущие настройки в памяти
            if 'keywords' in settings_data and settings_data['keywords']:
                self.search_queries = [keyword.strip() for keyword in settings_data['keywords'].split(',') if
                                       keyword.strip()]
                logger.info(f"✅ Поисковые запросы обновлены: {self.search_queries}")

            if 'exclude_keywords' in settings_data:
                self.exclude_keywords = [keyword.strip() for keyword in settings_data['exclude_keywords'].split(',') if
                                         keyword.strip()]
                logger.info(f"✅ Исключаемые слова обновлены: {self.exclude_keywords}")

            if 'browser_windows' in settings_data:
                self.browser_windows = settings_data['browser_windows']
                logger.info(f"✅ Количество окон браузера: {self.browser_windows}")

            # 🔥 ОБНОВЛЯЕМ ГОРОД
            if 'city' in settings_data:
                self.city = settings_data['city'] or 'Москва'
                logger.info(f"🌆 Город обновлен: {self.city}")

            if 'min_price' in settings_data:
                self.min_price = settings_data['min_price']
                logger.info(f"💰 Минимальная цена: {self.min_price}")

            if 'max_price' in settings_data:
                self.max_price = settings_data['max_price']
                logger.info(f"💰 Максимальная цена: {self.max_price}")

            logger.info("🔄 Новые настройки применены")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка в update_settings: {e}")
            import traceback
            traceback.print_exc()
            return False

    def reload_settings_from_db(self):
        """Перезагружает настройки из базы данных (СИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import ParserSettings
            from django.contrib.auth.models import User

            user = User.objects.first()
            if user:
                # ИСПРАВЛЕНИЕ: Берем первый найденный объект
                settings = ParserSettings.objects.filter(user=user).first()
                if settings:
                    if settings.keywords:
                        self.search_queries = [keyword.strip() for keyword in settings.keywords.split(',') if
                                               keyword.strip()]
                        logger.info(f"🔄 Перезагружены ключевые слова: {self.search_queries}")

                    if settings.exclude_keywords:
                        self.exclude_keywords = [keyword.strip() for keyword in settings.exclude_keywords.split(',') if
                                                 keyword.strip()]
                        logger.info(f"🔄 Перезагружены исключаемые слова: {self.exclude_keywords}")

                    self.min_price = settings.min_price
                    self.max_price = settings.max_price
                    self.min_rating = settings.min_rating
                    self.seller_type = settings.seller_type
                    self.browser_windows = settings.browser_windows or 1

                    logger.info("🔄 Настройки перезагружены из базы")
                    return True
                else:
                    logger.warning("⚠️ Настройки не найдены в базе")
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки настроек: {e}")
            return False

    def update_settings_for_user(self, user, settings_data):
        """Обновляет настройки для конкретного пользователя (СИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import ParserSettings

            parser_settings, created = ParserSettings.objects.get_or_create(
                user=user,
                defaults={
                    'keywords': settings_data.get('keywords', ''),
                    'exclude_keywords': settings_data.get('exclude_keywords', ''),
                    'min_price': settings_data.get('min_price', 0),
                    'max_price': settings_data.get('max_price', 100000),
                    'min_rating': settings_data.get('min_rating', 4.0),
                    'seller_type': settings_data.get('seller_type', 'all'),
                    'check_interval': settings_data.get('check_interval', 30),
                    'max_items_per_hour': settings_data.get('max_items_per_hour', 10),
                    'browser_windows': settings_data.get('browser_windows', 1),
                    'is_active': settings_data.get('is_active', True)
                }
            )

            if not created:
                if 'keywords' in settings_data:
                    parser_settings.keywords = settings_data['keywords']
                if 'exclude_keywords' in settings_data:
                    parser_settings.exclude_keywords = settings_data['exclude_keywords']
                if 'min_price' in settings_data:
                    parser_settings.min_price = settings_data['min_price']
                if 'max_price' in settings_data:
                    parser_settings.max_price = settings_data['max_price']
                if 'min_rating' in settings_data:
                    parser_settings.min_rating = settings_data['min_rating']
                if 'seller_type' in settings_data:
                    parser_settings.seller_type = settings_data['seller_type']
                if 'check_interval' in settings_data:
                    parser_settings.check_interval = settings_data['check_interval']
                if 'max_items_per_hour' in settings_data:
                    parser_settings.max_items_per_hour = settings_data['max_items_per_hour']
                if 'browser_windows' in settings_data:
                    parser_settings.browser_windows = settings_data['browser_windows']
                if 'is_active' in settings_data:
                    parser_settings.is_active = settings_data['is_active']

                parser_settings.save()

            logger.info(f"✅ Настройки пользователя {user.username} обновлены")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления настроек пользователя: {e}")
            return False

    def get_settings_for_user(self, user):
        """Получает настройки для конкретного пользователя (СИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import ParserSettings

            parser_settings = ParserSettings.objects.filter(user=user).first()
            if parser_settings:
                return {
                    'keywords': parser_settings.keywords,
                    'exclude_keywords': parser_settings.exclude_keywords,
                    'min_price': parser_settings.min_price,
                    'max_price': parser_settings.max_price,
                    'min_rating': parser_settings.min_rating,
                    'seller_type': parser_settings.seller_type,
                    'check_interval': parser_settings.check_interval,
                    'max_items_per_hour': parser_settings.max_items_per_hour,
                    'browser_windows': parser_settings.browser_windows,
                    'is_active': parser_settings.is_active
                }
            else:
                logger.warning(f"⚠️ Настройки для пользователя {user.username} не найдены")
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения настроек пользователя: {e}")
            return None

    def cleanup_duplicates(self):
        """Очищает дублирующиеся настройки (СИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import ParserSettings
            from django.contrib.auth.models import User
            from django.db.models import Count

            # Находим пользователей с дублирующимися настройками
            duplicate_users = ParserSettings.objects.values('user').annotate(
                count=Count('id')
            ).filter(count__gt=1)

            for user_data in duplicate_users:
                user_id = user_data['user']
                user_settings = ParserSettings.objects.filter(user_id=user_id).order_by('-id')

                # Оставляем только последние настройки
                if user_settings.count() > 1:
                    # Удаляем все кроме последней записи
                    for settings in user_settings[1:]:
                        settings.delete()

                    logger.info(f"🧹 Очищены дублирующиеся настройки для пользователя {user_id}")

            logger.info("✅ Очистка дублирующихся настроек завершена")

        except Exception as e:
            logger.error(f"❌ Ошибка очистка дублирующихся настроек: {e}")

    # Синхронные методы для быстрого доступа к настройкам в памяти
    def get_current_settings(self):
        """Возвращает текущие настройки из памяти (синхронный)"""
        return {
            'search_queries': self.search_queries,
            'exclude_keywords': self.exclude_keywords,
            'browser_windows': self.browser_windows,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'min_rating': self.min_rating,
            'seller_type': self.seller_type
        }

    def get_search_queries_count(self):
        """Возвращает количество поисковых запросов (синхронный)"""
        return len(self.search_queries)

    def format_parallel_processing_info(self):
        """Форматирует информацию о параллельной обработке в стиле парсера"""
        queries_count = len(self.search_queries)
        windows_count = self.browser_windows
        return f"🎯 ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА: {queries_count} запросов × {windows_count} окон"


# Глобальный экземпляр
settings_manager = SettingsManager()