import random
import logging
import asyncio
import time
from asgiref.sync import sync_to_async
from urllib.parse import urlparse
import hashlib
import base64
import aiohttp
from html import escape
import re
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Bot, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from shared.utils.config import get_bot_token, get_chat_id

logger = logging.getLogger('bot.notifications')


class NotificationSender:
    """УНИВЕРСАЛЬНЫЙ ОТПРАВЩИК УВЕДОМЛЕНИЙ С ТРЕКИНГОМ ВРЕМЕНИ"""

    def __init__(self):
        self.retry_count = 0
        self.max_retries = 3

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Форматирует время в читаемый вид ММ:СС"""
        seconds = int(seconds)

        if seconds < 60:
            return f"0:{seconds:02d}"

        minutes = seconds // 60
        remaining_seconds = seconds % 60

        return f"{minutes}:{remaining_seconds:02d}"

    @staticmethod
    def calculate_performance_metrics(parse_duration: float, search_duration: float) -> Dict[str, Any]:
        """Вычисляет метрики производительности"""
        total_duration = parse_duration + search_duration

        # Определяем категорию скорости
        if total_duration <= 5:
            speed_category = "⚡ Молниеносно"
        elif total_duration <= 15:
            speed_category = "🚀 Быстро"
        elif total_duration <= 30:
            speed_category = "🐇 Нормально"
        elif total_duration <= 60:
            speed_category = "🐢 Медленно"
        else:
            speed_category = "🚧 Очень медленно"

        return {
            'total_seconds': total_duration,
            'speed_category': speed_category,
            'parse_percentage': (parse_duration / total_duration * 100) if total_duration > 0 else 0,
            'search_percentage': (search_duration / total_duration * 100) if total_duration > 0 else 0,
        }

    def extract_product_id(self, url):
        """Извлекает ID товара из URL Avito"""
        try:
            # 🔥 ПРАВИЛЬНЫЕ ПАТТЕРНЫ ДЛЯ AVITO
            patterns = [
                r'avito\.ru/.+/(\d+)$',  # /category/ID
                r'avito\.ru/.+/.+_(\d+)$',  # /category/item_NAME_ID
                r'avito\.ru/items/(\d+)$',  # /items/ID (как в твоем примере)
                r'/(\d+)(?:\?|$)',  # /ID? или /ID
                r'_(\d+)(?:\?|$)',  # _ID? или _ID
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    product_id = match.group(1)
                    if product_id and product_id.isdigit():
                        # УБРАЛ ЛОГ ОТСЮДА
                        return product_id

            # 🔥 ПРИОРИТЕТ: Используем product_id из данных товара если есть
            if hasattr(self, 'current_product_data') and self.current_product_data.get('product_id'):
                product_id = self.current_product_data['product_id']
                return str(product_id)

            fallback_id = hashlib.md5(url.encode()).hexdigest()[:12]
            return fallback_id

        except Exception as e:
            return hashlib.md5(url.encode()).hexdigest()[:12]

    def normalize_url_universal(self, url):
        """УНИВЕРСАЛЬНАЯ НОРМАЛИЗАЦИЯ URL - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # 🔥 ДЛЯ AUTO.RU - ВОЗВРАЩАЕМ ОРИГИНАЛЬНЫЙ URL БЕЗ ИЗМЕНЕНИЙ
            if 'auto.ru' in url:
                logger.debug(f"🔗 Auto.ru URL сохранен как есть: {url}")
                return url

            # 🔥 ДЛЯ AVITO - используем product_id из данных если есть
            if hasattr(self, 'current_product_data'):
                product_id = self.current_product_data.get('product_id') or self.current_product_data.get('item_id')
                if product_id:
                    normalized_url = f"https://www.avito.ru/items/{product_id}"
                    logger.debug(f"🔗 Нормализация Avito URL с product_id: {normalized_url}")
                    return normalized_url

            # 🔥 ЕСЛИ НЕТ product_id В ДАННЫХ, ИСПОЛЬЗУЕМ СТАРУЮ ЛОГИКУ
            parsed = urlparse(url)
            product_id = self.extract_product_id(url)
            domain = parsed.netloc.replace('www.', '').replace('m.', '')
            normalized_url = f"{parsed.scheme}://{domain}/items/{product_id}"

            logger.debug(f"🔗 Нормализация Avito URL из URL: {url[:80]}... -> {normalized_url}")
            return normalized_url

        except Exception as e:
            logger.error(f"❌ Ошибка нормализации URL {url}: {e}")
            return url

    async def is_duplicate_url(self, url):
        """🔥 ПРОВЕРКА ДУБЛИКАТА - БАЗА ДАННЫХ"""
        try:
            from apps.website.models import NotificationCache

            product_id = self.extract_product_id(url)
            logger.info(f"🎯 Извлечен ID из URL: {product_id} из {url[:80]}...")

            @sync_to_async
            def check_db():
                return NotificationCache.is_duplicate(product_id, url)

            return await check_db()

        except Exception as e:
            logger.error(f"❌ Ошибка проверки дубликата: {e}")
            return True

    async def get_cache_stats(self):
        """Получает статистику кэша из базы"""
        try:
            from apps.website.models import NotificationCache

            @sync_to_async
            def get_stats():
                return NotificationCache.get_cache_stats()

            return await get_stats()

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики кэша: {e}")
            return {'error': str(e)}

    async def clear_duplicate_cache(self):
        """Очищает кэш дубликатов - ИЗ БАЗЫ (АСИНХРОННАЯ ВЕРСИЯ)"""
        try:
            from apps.website.models import NotificationCache

            @sync_to_async
            def clear_database_cache():
                deleted_count = NotificationCache.objects.all().delete()[0]
                return deleted_count

            deleted_count = await clear_database_cache()
            logger.info(f"🧹 Очищен кэш уведомлений из базы: {deleted_count} записей")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша из базы: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def clear_duplicate_cache_sync(self):
        """Синхронная обертка для clear_duplicate_cache"""
        try:
            import asyncio

            # Проверяем, есть ли запущенный event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже работает, создаем новую задачу
                    # Но это синхронный метод, поэтому запускаем новый loop
                    logger.warning("⚠️ Event loop уже запущен, создаем новый для синхронного вызова")
                    return asyncio.run(self.clear_duplicate_cache())
            except RuntimeError:
                pass  # Нет текущего loop

            # Запускаем асинхронную функцию
            return asyncio.run(self.clear_duplicate_cache())

        except Exception as e:
            logger.error(f"❌ Ошибка в синхронной очистке кэша: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def _save_to_cache(self, product_id, normalized_url, product_name, time_data=None):
        """Сохранение в кэш с данными о времени"""
        try:
            from apps.website.models import NotificationCache

            @sync_to_async
            def save_to_database():
                cache_entry = NotificationCache.add_to_cache(
                    product_id=product_id,
                    normalized_url=normalized_url,
                    product_name=product_name[:255]
                )

                # Если есть данные о времени, обновляем дополнительными полями
                if time_data and cache_entry:
                    cache_entry.parse_duration = time_data.get('parse_duration_seconds', 0)
                    cache_entry.search_duration = time_data.get('search_duration_seconds', 0)
                    cache_entry.total_duration = time_data.get('total_duration_seconds', 0)
                    cache_entry.time_status = time_data.get('time_status', '')
                    cache_entry.save()

                return cache_entry

            cache_entry = await save_to_database()
            return cache_entry

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш: {e}")
            raise e

    def create_notification_keyboard(self, product_url):
        """Создает клавиатуру для уведомления"""
        try:
            url_hash = hashlib.md5(product_url.encode()).hexdigest()[:16]

            keyboard = [
                [
                    InlineKeyboardButton("🔗 Перейти к объявлению", url=product_url),
                    InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"favorite_{url_hash}")
                ]
            ]

            return InlineKeyboardMarkup(keyboard)

        except Exception as e:
            logger.error(f"❌ Ошибка создания клавиатуры: {e}")
            try:
                keyboard = [
                    [InlineKeyboardButton("🔗 Перейти к объявлению", url=product_url)]
                ]
                return InlineKeyboardMarkup(keyboard)
            except:
                return None

    async def _url_to_base64(self, image_url):
        """Конвертирует URL изображения в base64"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=15) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"
            return None
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки изображения {image_url}: {e}")
            return None

    async def _get_all_images(self, product_data, image_data=None):
        """Получает все изображения товара"""
        all_images = []

        image_urls = product_data.get('image_urls', [])
        if image_urls:
            success_count = 0
            error_count = 0

            for image_url in image_urls[:5]:
                try:
                    image_base64 = await self._url_to_base64(image_url)
                    if image_base64:
                        all_images.append(image_base64)
                        success_count += 1
                except Exception as e:
                    error_count += 1
                    if error_count == 1:
                        logger.debug(f"⚠️ Ошибка конвертации изображения: {e}")

            if error_count > 0:
                logger.warning(f"⚠️ Не удалось конвертировать {error_count} изображений")

        if not all_images and image_data:
            all_images = [image_data]

        if not all_images and product_data.get('image_data'):
            all_images = [product_data['image_data']]

        return all_images

    def _generate_hashtags(self, product_data):
        """Генерирует умные теги на основе частоты слов в названии, категории и описании"""
        try:
            from collections import Counter
            import re

            # Собираем весь текст для анализа
            all_text = ""

            # 1. Название товара (самый важный - вес x3)
            product_name = product_data.get('name', '')
            if product_name:
                all_text += f" {product_name.lower()} " * 3  # Увеличиваем вес названия

            # 2. Категория (важный - вес x2)
            category = product_data.get('avito_category') or product_data.get('category', '')
            if category:
                all_text += f" {category.lower()} " * 2

            # 3. Описание (дополнительный источник)
            description = product_data.get('description', '')
            if description and description != 'Описание отсутствует':
                all_text += f" {description.lower()}"

            if not all_text.strip():
                return "#автопоиск"

            # Извлекаем слова (только русские и английские слова от 3 символов)
            words = re.findall(r'[a-zа-яё]{3,}|[a-z]{3,}', all_text.lower())

            # Список стоп-слов для фильтрации
            stop_words = {
                # Русские стоп-слова
                'это', 'как', 'так', 'и', 'в', 'над', 'к', 'до', 'не', 'на', 'но', 'за', 'то', 'с',
                'ли', 'а', 'во', 'от', 'со', 'для', 'о', 'же', 'ну', 'вы', 'бы', 'что', 'кто', 'он',
                'она', 'из', 'или', 'мы', 'этот', 'тот', 'где', 'когда', 'да', 'нет', 'если', 'по',
                'только', 'очень', 'можно', 'при', 'есть', 'еще', 'уже', 'все', 'его', 'ее', 'их',
                'там', 'тут', 'после', 'потом', 'пока', 'тем', 'чем', 'самый', 'более', 'менее',
                'новый', 'новая', 'новое', 'оригинал', 'оригинальный', 'оригинальная', 'xl', 'xxl',
                'xxxl', 'размер', 'цвет', 'состояние', 'отличное', 'хорошее', 'купить', 'продам',
                'продажа', 'цена', 'рубль', 'руб', 'москва', 'спб', 'город', 'адрес', 'метро',
                'доставка', 'самовывоз', 'описание', 'характеристики', 'фото', 'видео', 'отзывы',
                'рейтинг', 'балл', 'продавец', 'магазин', 'частник', 'объявление', 'товар', 'вещь',
                'модель', 'бренд', 'марка', 'производитель', 'страна', 'сша', 'китай', 'европа',
                'россия', 'год', 'месяц', 'неделя', 'день', 'час', 'время', 'сегодня', 'вчера',
                'телефон', 'смартфон', 'телефоны', 'смартфоны', 'куртка', 'куртки', 'пуховик',
                'пуховики', 'одежда', 'обувь', 'аксессуары', 'электроника', 'техника'
            }

            # Фильтруем слова
            filtered_words = []
            for word in words:
                if (word not in stop_words and
                        len(word) >= 3 and
                        not word.isdigit() and
                        not any(char.isdigit() for char in word)):
                    filtered_words.append(word)

            # Считаем частоту слов
            word_freq = Counter(filtered_words)

            # Берем топ-5 самых частых слов
            top_words = [word for word, count in word_freq.most_common(7)]

            # Создаем теги (максимум 5 тегов)
            tags = []
            for word in top_words[:5]:
                # Для английских слов оставляем как есть, для русских - транслитерируем?
                tags.append(f"#{word}")

            # Если совсем нет тегов - fallback
            if not tags:
                return "#автопоиск"

            return " ".join(tags)

        except Exception as e:
            logger.error(f"❌ Ошибка генерации тегов: {e}")
            return "#автопоиск"

    def _format_message(self, product_data):
        """Форматирует сообщение для Telegram с поддержкой Auto.ru"""

        # Определяем сайт для специфичного форматирования
        site = product_data.get('site', 'avito').lower()

        if site == 'auto.ru':
            return self._format_auto_ru_message(product_data)
        else:
            return self._format_avito_message(product_data)

    def _format_auto_ru_message(self, product_data):
        """Форматирует сообщение для Auto.ru в стиле Авито"""
        economy = product_data.get('economy', 0)
        economy_percent = product_data.get('economy_percent', 0)

        if economy > 0:
            header = "💰 <b>ВЫГОДНЫЙ АВТОМОБИЛЬ!</b>"
            profit_text = f"💵 <b>Прибыль:</b> +{economy:,.0f} ₽ ({economy_percent}%)"
        else:
            header = "🚗 <b>ИНТЕРЕСНЫЙ АВТОМОБИЛЬ</b>"
            profit_text = f"⚖️ <b>Цена соответствует рынку</b>"

        hashtags = self._generate_hashtags(product_data)
        rating_text = self._format_rating(product_data)
        seller_text = self._format_seller_info(product_data)

        posted_date = product_data.get('posted_date', 'Дата не указана')
        city = product_data.get('city', 'Не указан')
        views_count = product_data.get('views_count', 0)

        # Форматируем метро и адрес как в Авито
        metro_text = self._format_metro_info(product_data)
        address_text = self._format_address_info(product_data)

        # 🔥 ДОБАВЛЯЕМ ВРЕМЯ ПАРСИНГА
        time_section = ""
        parse_time_display = product_data.get('parse_time_display')
        time_status = product_data.get('time_status')

        if parse_time_display and time_status:
            time_section = f"⏱️ <b>Время обработки:</b> {parse_time_display} ({time_status})"

        message_lines = []
        message_lines.append(header)
        message_lines.append("")

        # Основная информация
        message_lines.append(f"📦 <b>Модель:</b> {escape(product_data['name'])}")
        message_lines.append(f"📍 <b>Город:</b> {escape(city)}")

        # Год выпуска
        year = product_data.get('year', '')
        if year:
            message_lines.append(f"📅 <b>Год выпуска:</b> {escape(str(year))}")

        # Пробег
        mileage = product_data.get('mileage', '')
        if mileage:
            message_lines.append(f"🛣️ <b>Пробег:</b> {escape(mileage)}")

        # Владельцы
        owners = product_data.get('owners', '')
        if owners:
            message_lines.append(f"👥 <b>Владельцы:</b> {escape(owners)}")

        # Состояние
        condition = product_data.get('condition', '')
        if condition:
            message_lines.append(f"🔧 <b>Состояние:</b> {escape(condition)}")

        # Двигатель
        engine = product_data.get('engine', '')
        if engine:
            message_lines.append(f"⚙️ <b>Двигатель:</b> {escape(engine)}")

        # Коробка передач
        transmission = product_data.get('transmission', '')
        if transmission:
            message_lines.append(f"🔧 <b>КПП:</b> {escape(transmission)}")

        # Привод
        drive = product_data.get('drive', '')
        if drive:
            message_lines.append(f"🚗 <b>Привод:</b> {escape(drive)}")

        # Цвет
        color = product_data.get('color', '')
        if color:
            message_lines.append(f"🎨 <b>Цвет:</b> {escape(color)}")

        # Руль
        steering = product_data.get('steering', '')
        if steering:
            message_lines.append(f"🎯 <b>Руль:</b> {escape(steering)}")

        # ПТС
        pts = product_data.get('pts', '')
        if pts:
            message_lines.append(f"📄 <b>ПТС:</b> {escape(pts)}")

        # Метро и адрес
        if metro_text:
            message_lines.append(f"🚇 <b>Метро:</b> {metro_text}")

        if address_text:
            message_lines.append(f"📍 <b>Адрес:</b> {address_text}")

        # 🔥 ВРЕМЯ ОБРАБОТКИ
        if time_section:
            message_lines.append("")
            message_lines.append(time_section)

        message_lines.append("")

        # Цены
        message_lines.append(f"💎 <b>Цена продавца:</b> {product_data['price']:,.0f} ₽")

        target_price = product_data.get('target_price', product_data['price'])
        if target_price != product_data['price']:
            message_lines.append(f"🎯 <b>Рыночная цена:</b> {target_price:,.0f} ₽")

        message_lines.append(profit_text)

        # Статус цены от Auto.ru
        price_status = product_data.get('price_status', '')
        if price_status:
            message_lines.append(f"🏷️ <b>Статус:</b> {escape(price_status)}")

        message_lines.append("")

        # Информация о размещении
        message_lines.append(f"📅 <b>Размещено:</b> {escape(posted_date)}")

        if views_count:
            message_lines.append(f"👁 <b>Просмотров:</b> {views_count}")

        message_lines.append(f"👤 <b>Продавец:</b> {seller_text}")

        if rating_text:
            message_lines.append(f"⭐ <b>Рейтинг:</b> {escape(rating_text)}")

        # ID объявления
        product_id = product_data.get('product_id', '')
        if product_id:
            message_lines.append(f"🆔 <b>ID:</b> {escape(product_id)}")

        # Описание
        description = product_data.get('description', '')
        if description and description != 'Автомобиль с Auto.ru' and len(description) > 10:
            clean_description = ' '.join(description.split())

            base_lines = message_lines.copy()
            base_lines.append("")
            base_lines.append(f"#️⃣ <b>Теги:</b> {hashtags}")
            base_lines.append("")
            base_lines.append(f"🔗 <a href='{product_data['url']}'>Смотреть на Auto.ru</a>")

            base_message = "\n".join(base_lines)
            base_length = len(base_message)
            available_for_description = 1024 - base_length - 50

            if available_for_description > 100:
                if len(clean_description) > available_for_description:
                    truncated_description = clean_description[:available_for_description - 3] + "..."
                    message_lines.append("")
                    message_lines.append(f"📝 <b>Описание:</b> {escape(truncated_description)}")
                else:
                    message_lines.append("")
                    message_lines.append(f"📝 <b>Описание:</b> {escape(clean_description)}")

        message_lines.append("")
        message_lines.append(f"#️⃣ <b>Теги:</b> {hashtags}")
        message_lines.append("")
        message_lines.append(f"🔗 <a href='{product_data['url']}'>Смотреть на Auto.ru</a>")

        message = "\n".join(message_lines)

        # Проверка длины сообщения
        if len(message) > 1024:
            logger.warning("⚠️ Сообщение Auto.ru слишком длинное, обрезаем описание")

            # Сначала обрезаем описание
            for i, line in enumerate(message_lines):
                if line.startswith("📝 <b>Описание:</b>"):
                    current_desc = line.replace("📝 <b>Описание:</b> ", "")
                    if len(current_desc) > 100:
                        message_lines[i] = f"📝 <b>Описание:</b> {escape(current_desc[:97])}..."
                    break

            message = "\n".join(message_lines)

            # Если все еще длинное, убираем менее важные поля
            if len(message) > 1024:
                less_important_fields = [
                    "🏷️ <b>Статус:",
                    "🆔 <b>ID:",
                    "👁 <b>Просмотров:",
                    "⭐ <b>Рейтинг:"
                ]

                filtered_lines = []
                for line in message_lines:
                    if not any(field in line for field in less_important_fields):
                        filtered_lines.append(line)

                message = "\n".join(filtered_lines)

        return message

    def _remove_section(self, lines, section_header):
        """Удаляет секцию из сообщения"""
        try:
            result = []
            skip_section = False

            for line in lines:
                if line == section_header:
                    skip_section = True
                    continue
                elif skip_section and line and not line.startswith("   "):
                    skip_section = False

                if not skip_section:
                    result.append(line)

            return result
        except Exception as e:
            logger.error(f"❌ Ошибка удаления секции: {e}")
            return lines

    def _format_avito_message(self, product_data):
        """Форматирует сообщение для Авито (ваша существующая логика)"""
        economy = product_data.get('economy', 0)
        economy_percent = product_data.get('economy_percent', 0)

        if economy > 0:
            header = "💰 <b>ВЫГОДНАЯ СДЕЛКА!</b>"
            profit_text = f"💵 <b>Прибыль:</b> +{economy:,.0f} ₽ ({economy_percent}%)"
        else:
            header = "🔍 <b>ИНТЕРЕСНОЕ ПРЕДЛОЖЕНИЕ</b>"
            profit_text = f"⚖️ <b>Цена соответствует рынку</b>"

        hashtags = self._generate_hashtags(product_data)
        rating_text = self._format_rating(product_data)
        seller_text = self._format_seller_info(product_data)

        posted_date = product_data.get('posted_date', 'Дата не указана')
        city = product_data.get('city', 'Не указан')
        views_count = product_data.get('views_count', 0)
        color = product_data.get('color', 'Разноцветный')

        colors_text = ""
        if product_data.get('detected_colors'):
            colors_list = []
            for color_name, percentage in product_data['detected_colors'][:3]:
                colors_list.append(f"{escape(color_name)} ({percentage}%)")
            colors_text = "🎨 <b>Цвета:</b> " + ", ".join(colors_list)

        metro_text = self._format_metro_info(product_data)
        address_text = self._format_address_info(product_data)

        # 🔥 ДОБАВЛЯЕМ ВРЕМЯ ПАРСИНГА
        time_section = ""
        parse_time_display = product_data.get('parse_time_display')
        time_status = product_data.get('time_status')

        if parse_time_display and time_status:
            time_section = f"⏱️ <b>Время обработки:</b> {parse_time_display} ({time_status})"

        message_lines = []
        message_lines.append(header)
        message_lines.append("")
        message_lines.append(f"📦 <b>Товар:</b> {escape(product_data['name'])}")
        message_lines.append(f"📍 <b>Город:</b> {escape(city)}")
        message_lines.append(f"🎨 <b>Цвет:</b> {escape(color)}")

        condition = product_data.get('condition', 'Не указано')
        if condition and condition != 'Не указано':
            message_lines.append(f"📦 <b>Состояние:</b> {escape(condition)}")

        if metro_text:
            message_lines.append(f"🚇 <b>Метро:</b> {metro_text}")

        if address_text:
            message_lines.append(f"📍 <b>Адрес:</b> {address_text}")

        # 🔥 ВРЕМЯ ОБРАБОТКИ
        if time_section:
            message_lines.append("")
            message_lines.append(time_section)

        message_lines.append("")
        message_lines.append(
            f"📂 <b>Категория:</b> {escape(product_data.get('avito_category', product_data.get('category', 'Не указана')))}")
        message_lines.append("")
        message_lines.append(f"💎 <b>Цена продавца:</b> {product_data['price']:,.0f} ₽")
        message_lines.append(
            f"🎯 <b>Рыночная цена:</b> {product_data.get('target_price', product_data['price']):,.0f} ₽")
        message_lines.append(profit_text)

        if colors_text:
            message_lines.append(colors_text)

        message_lines.append("")
        message_lines.append(f"📅 <b>Размещено:</b> {escape(posted_date)}")
        message_lines.append(f"👁 <b>Просмотров:</b> {views_count}")
        message_lines.append(f"👤 <b>Продавец:</b> {seller_text}")

        if rating_text:
            message_lines.append(f"⭐ <b>Рейтинг:</b> {escape(rating_text)}")

        # Описание
        description = product_data.get('description', '')
        if description and description != 'Описание отсутствует':
            clean_description = ' '.join(description.split())
            base_lines = message_lines.copy()
            base_lines.append("")
            base_lines.append(f"#️⃣ <b>Теги:</b> {hashtags}")
            base_lines.append("")
            base_lines.append(f"🔗 <a href='{product_data['url']}'>Просмотреть объявление на Авито</a>")

            base_message = "\n".join(base_lines)
            base_length = len(base_message)
            available_for_description = 1024 - base_length - 50

            if available_for_description > 100:
                if len(clean_description) > available_for_description:
                    truncated_description = clean_description[:available_for_description - 3] + "..."
                    message_lines.append("")
                    message_lines.append(f"📝 <b>Описание:</b> {escape(truncated_description)}")
                else:
                    message_lines.append("")
                    message_lines.append(f"📝 <b>Описание:</b> {escape(clean_description)}")

        message_lines.append("")
        message_lines.append(f"#️⃣ <b>Теги:</b> {hashtags}")
        message_lines.append("")
        message_lines.append(f"🔗 <a href='{product_data['url']}'>Просмотреть объявление на Авито</a>")

        message = "\n".join(message_lines)

        if len(message) > 1024:
            logger.warning("⚠️ Сообщение Авито слишком длинное, обрезаем описание")
            for i, line in enumerate(message_lines):
                if line.startswith("📝 <b>Описание:</b>"):
                    current_desc = line.replace("📝 <b>Описание:</b> ", "")
                    if len(current_desc) > 100:
                        message_lines[i] = f"📝 <b>Описание:</b> {escape(current_desc[:97])}..."
                    break
            message = "\n".join(message_lines)

        return message

    async def send_notification(self, product_data, image_data=None):
        """ОТПРАВКА УВЕДОМЛЕНИЯ - БЕЗ ДУБЛЕЙ"""
        try:
            product_url = product_data['url']
            product_id = self.extract_product_id(product_url)
            normalized_url = self.normalize_url_universal(product_url)

            # 🔥 ПРОСТАЯ ПРОВЕРКА: ЕСТЬ В БАЗЕ - ПРОПУСТИТЬ, НЕТ - ОБРАБОТАТЬ
            if await self.is_duplicate_url(product_url):
                logger.info(f"🚫 Пропускаем дубликат: {product_data['name']} (ID: {product_id})")
                return True

            logger.info(f"📨 Отправляем уведомление: {product_data['name']} (ID: {product_id})")

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or token == 'ваш_токен_бота':
                logger.error("❌ Токен бота не установлен или установлен по умолчанию")
                return False

            if not chat_id:
                logger.error("❌ Chat ID не установлен")
                return False

            bot = Bot(token=token)
            all_images = await self._get_all_images(product_data, image_data)
            message = self._format_message(product_data)
            reply_markup = self.create_notification_keyboard(product_url)

            success = False

            # 🔥 ОДНА ПОПЫТКА ОТПРАВКИ - ЛИБО МЕДИА-ГРУППА, ЛИБО ТЕКСТ, НЕ ОБА ВАРИАНТА!
            if len(all_images) >= 1:
                logger.info(f"🖼️ Отправка медиа-группы из {len(all_images)} фото")
                success = await self._send_media_group_with_caption(
                    bot, chat_id, all_images, message, reply_markup
                )

                # 🔥 НЕ ПЫТАЕМСЯ ОТПРАВИТЬ ТЕКСТ ЕСЛИ НЕ УДАЛОСЬ ОТПРАВИТЬ ФОТО
                if not success:
                    logger.error("❌ Не удалось отправить медиа-группу")
            else:
                logger.info("📝 Отправка текста с кнопками (нет фото)")
                success = await self._send_text_with_buttons(bot, chat_id, message, reply_markup)

            # ✅ СОХРАНЯЕМ В БАЗУ ТОЛЬКО ПРИ УСПЕШНОЙ ОТПРАВКЕ
            if success:
                try:
                    # 🔥 СОБИРАЕМ ДАННЫЕ О ВРЕМЕНИ ДЛЯ СОХРАНЕНИЯ В КЭШ
                    time_data = {}
                    parse_duration = product_data.get('parse_time_seconds', 0)
                    search_duration = product_data.get('search_duration', 0)
                    total_duration = parse_duration + search_duration

                    if total_duration > 0:
                        time_data = {
                            'parse_duration_seconds': int(parse_duration),
                            'search_duration_seconds': int(search_duration),
                            'total_duration_seconds': int(total_duration),
                            'time_status': product_data.get('time_status', '')
                        }

                    await self._save_to_cache(product_id, normalized_url, product_data['name'], time_data)
                    logger.info(
                        f"✅ Уведомление отправлено и сохранено в базу: {product_data['name']} (ID: {product_id})")
                except Exception as db_error:
                    logger.error(f"❌ Ошибка сохранения в кэш базы: {db_error}")
            else:
                logger.error(f"❌ Уведомление не отправлено: {product_data['name']}")

            return success

        except Exception as e:
            logger.error(f"❌ Критическая ошибка отправки уведомления: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _send_media_group_with_caption(self, bot, chat_id, image_data_list, message, reply_markup):
        """🔥 УМНАЯ ОТПРАВКА БЕЗ ЛОЖНЫХ ОШИБОК"""
        import base64

        try:
            media_group = []

            for i, image_data in enumerate(image_data_list[:5]):
                if image_data.startswith('data:image/jpeg;base64,'):
                    image_data = image_data.replace('data:image/jpeg;base64,', '')
                elif image_data.startswith('data:image/png;base64,'):
                    image_data = image_data.replace('data:image/png;base64,', '')

                image_bytes = base64.b64decode(image_data)

                if i == 0:
                    media = InputMediaPhoto(
                        media=image_bytes,
                        caption=message,
                        parse_mode='HTML'
                    )
                else:
                    media = InputMediaPhoto(media=image_bytes)

                media_group.append(media)

            # 🔥 ДОБАВЛЯЕМ ЗАДЕРЖКУ И УВЕЛИЧЕННЫЙ ТАЙМАУТ
            logger.info(f"📸 Подготовлено {len(media_group)} изображений для отправки")
            logger.info("⏳ Добавляем задержку для стабильной отправки...")
            await asyncio.sleep(2)  # ← задержка 2 секунды перед отправкой

            # 🎯 ОТПРАВЛЯЕМ С УВЕЛИЧЕННЫМ ТАЙМАУТОМ
            await bot.send_media_group(
                chat_id=chat_id,
                media=media_group,
                read_timeout=60,  # ← увеличиваем таймаут чтения
                write_timeout=60,  # ← увеличиваем таймаут записи
                connect_timeout=60  # ← увеличиваем таймаут соединения
            )

            logger.info(f"✅ Медиа-группа из {len(media_group)} фото отправлена успешно!")
            return True

        except Exception as e:
            logger.error(f"❌ РЕАЛЬНАЯ ошибка отправки медиа-группы: {e}")
            return False

    async def _send_text_with_buttons(self, bot, chat_id, message, reply_markup):
        """Отправляет текстовое сообщение с кнопками"""
        for attempt in range(3):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

                logger.info("✅ Текст с кнопками отправлен")
                return True

            except Exception as e:
                logger.warning(f"⚠️ Попытка {attempt + 1}/3 не удалась: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
                continue

        logger.error("❌ Не удалось отправить текст с кнопками")
        return False

    def _format_metro_info(self, product):
        """Форматирует информацию о метро"""
        try:
            metro_stations = product.get('metro_stations', [])

            if metro_stations:
                metro_names = []
                for station in metro_stations[:3]:
                    station_name = station.get('name', '')
                    if station_name:
                        metro_names.append(station_name)

                if metro_names:
                    return ", ".join(metro_names)

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования метро: {e}")
            return None

    def _format_address_info(self, product):
        """Форматирует информацию об адресе"""
        try:
            address = product.get('address', '')

            if address:
                clean_address = ' '.join(address.split())
                if len(clean_address) > 50:
                    clean_address = clean_address[:47] + "..."
                return clean_address

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования адреса: {e}")
            return None

    def _format_rating(self, product):
        """Форматирует рейтинг продавца"""
        rating_text = ""
        if product.get('seller_rating') is not None:
            try:
                rating = float(product['seller_rating'])
                rating = round(rating, 1)
                full_stars = int(rating)
                half_star = 1 if rating - full_stars >= 0.5 else 0
                empty_stars = max(0, 5 - full_stars - half_star)

                stars = "★" * full_stars + "½" * half_star + "☆" * empty_stars
                rating_text = f"{stars} ({rating}/5)"

                if product.get('reviews_count'):
                    rating_text += f" ({product['reviews_count']} отзывов)"
                else:
                    rating_text += " (нет отзывов)"
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Ошибка преобразования рейтинга: {e}")
                rating_text = "Рейтинг не указан"
        return rating_text

    def _format_seller_info(self, product):
        """Форматирует информацию о продавце"""
        seller_type = " (Магазин)" if product.get('reviews_count', 0) > 150 else " (Частник)"
        return f"{product.get('seller_name', 'Не указан')}{seller_type}"

    @sync_to_async
    def save_product_to_db(self, product, economy, economy_percent, user_id):
        """СОХРАНЕНИЕ В БАЗУ ДЛЯ КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ С ВСЕМИ ПОЛЯМИ AUTO.RU И ML И ВРЕМЕНЕМ"""
        try:
            from apps.website.models import FoundItem, SearchQuery
            from django.contrib.auth.models import User
            from django.utils import timezone
            from django.db import IntegrityError
            from datetime import timedelta

            # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ 1: Получаем пользователя по переданному user_id
            try:
                user = User.objects.get(id=user_id)
                logger.info(f"👤 Сохранение товара для пользователя: {user.username} (ID: {user_id})")
            except User.DoesNotExist:
                logger.error(f"❌ Пользователь с ID {user_id} не найден")
                return False

            # 🔥 СОХРАНЯЕМ ДАННЫЕ ТОВАРА ДЛЯ ИСПОЛЬЗОВАНИЯ В extract_product_id
            self.current_product_data = product

            normalized_url = self.normalize_url_universal(product['url'])
            time_threshold = timezone.now() - timedelta(hours=24)

            # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ 2: Проверка дубликата ТОЛЬКО для этого пользователя
            existing_item = FoundItem.objects.filter(
                url=normalized_url,
                search_query__user=user,  # ← Теперь фильтруем по пользователю
                found_at__gte=time_threshold
            ).first()

            if existing_item:
                logger.info(f"🚫 Товар уже существует у пользователя {user.username} (24ч): {product['name']}")

                # 🔥 ОБНОВЛЯЕМ ML-ПОЛЯ если товар уже существует
                updated = False
                if 'ml_freshness_score' in product:
                    existing_item.ml_freshness_score = product['ml_freshness_score']
                    updated = True
                    logger.info(f"📝 Обновлен ml_freshness_score: {product['ml_freshness_score']}")

                if 'priority_score' in product:
                    existing_item.priority_score = product['priority_score']
                    updated = True
                    logger.info(f"📝 Обновлен priority_score: {product['priority_score']}")

                if 'ml_freshness_category' in product:
                    existing_item.freshness_category = product['ml_freshness_category']
                    updated = True
                    logger.info(f"📝 Обновлен freshness_category: {product['ml_freshness_category']}")

                # 🔥 ОБНОВЛЯЕМ ПОЛЯ ВРЕМЕНИ
                parse_time_display = product.get('parse_time_display')
                time_status = product.get('time_status')
                if parse_time_display and hasattr(existing_item, 'parse_time_display'):
                    existing_item.parse_time_display = parse_time_display
                    updated = True
                    logger.info(f"📝 Обновлено время парсинга: {parse_time_display}")

                if time_status and hasattr(existing_item, 'time_status'):
                    existing_item.time_status = time_status
                    updated = True
                    logger.info(f"📝 Обновлен статус времени: {time_status}")

                if updated:
                    existing_item.save()
                    logger.info(f"📝 Обновлен существующий товар с ML-полями и временем")

                return False

            # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ 3: Создаем SearchQuery ТОЛЬКО для этого пользователя
            search_query, created = SearchQuery.objects.get_or_create(
                user=user,  # ← user теперь правильный
                name=product['name'][:50],
                defaults={
                    'category': product.get('avito_category', product.get('category', 'Не указана')),
                    'target_price': product.get('target_price', product['price']),
                    'min_price': 0,
                    'max_price': 1000000,
                    'is_active': True
                }
            )

            image_urls = product.get('image_urls', [])
            if not image_urls and product.get('image_url'):
                image_urls = [product.get('image_url')]

            city = product.get('city', 'Москва')

            # 🔥 ИСПРАВЛЕНИЕ: Извлекаем ОБА значения просмотров
            views_count = product.get('views_count', 0)
            views_today_value = product.get('views_today', 0)

            # 🔥 ПРИВОДИМ К INT НА ВСЯКИЙ СЛУЧАЙ
            try:
                # Если views_count пришел как словарь (старая версия)
                if isinstance(views_count, dict):
                    logger.warning("⚠️ views_count пришел как словарь, извлекаем total_views")
                    views_count = views_count.get('total_views', 0)

                views_count = int(views_count) if views_count not in [None, ''] else 0
                views_today_value = int(views_today_value) if views_today_value not in [None, ''] else 0
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Ошибка конвертации просмотров: {e}")
                views_count = 0
                views_today_value = 0

            address = product.get('address')
            metro_stations = product.get('metro_stations', [])
            full_location = product.get('full_location')

            # 🔥 ОПРЕДЕЛЯЕМ ИСТОЧНИК (source) ПО САЙТУ
            site = product.get('site', 'avito')  # По умолчанию avito
            if site == 'auto.ru':
                source = 'auto_ru'
            else:
                source = 'avito'

            # 🔥 ИСПРАВЛЯЕМ ПЕРЕДАЧУ ЧИСЛОВЫХ ПОЛЕЙ
            year_value = product.get('year')
            if year_value and str(year_value).strip() and str(year_value).isdigit():
                year_value = int(year_value)
            else:
                year_value = None

            discount_price_value = product.get('discount_price', 0)
            if not discount_price_value or discount_price_value == '':
                discount_price_value = 0

            # 🔥 ВАЖНО: Получаем product_id из данных товара
            product_id = product.get('product_id') or product.get('item_id')
            if not product_id:
                # Если нет в данных, извлекаем из URL
                product_id = self.extract_product_id(product['url'])

            # 🔥 ВЫЧИСЛЯЕМ ВРЕМЯ И СТАТУС
            parse_duration = product.get('parse_time_seconds', 0)
            search_duration = product.get('search_duration', 0)
            total_duration = parse_duration + search_duration

            # Форматируем время
            parse_time_display = product.get('parse_time_display', self.format_duration(parse_duration))

            # Определяем статус времени
            if total_duration <= 5:
                time_status = "⚡ Молниеносно"
            elif total_duration <= 15:
                time_status = "🚀 Быстро"
            elif total_duration <= 30:
                time_status = "🐇 Нормально"
            elif total_duration <= 60:
                time_status = "🐢 Медленно"
            else:
                time_status = "🚧 Очень медленно"

            # 🔥 СОЗДАЕМ ОБЪЕКТ С ВСЕМИ НОВЫМИ ПОЛЯМИ ВКЛЮЧАЯ ML И ВРЕМЯ
            found_item_data = {
                'search_query': search_query,
                'parsed_by': user,
                'title': product['name'],
                'price': product['price'],
                'target_price': product.get('target_price', product['price']),
                'profit': economy,
                'profit_percent': economy_percent,
                'url': normalized_url,
                'image_url': product.get('image_url'),
                'image_urls': image_urls,
                'description': product.get('description', '') or '',
                'seller_name': product.get('seller_name', ''),
                'seller_rating': product.get('seller_rating'),
                'reviews_count': product.get('reviews_count', 0),
                'category': product.get('avito_category', product.get('category', 'Не указана')),
                'city': city,
                'posted_date': product.get('posted_date', ''),
                'views_count': views_count,  # ← ОБЩИЕ ПРОСМОТРЫ (число)
                'views_today': views_today_value,  # ← ПРОСМОТРЫ ЗА СЕГОДНЯ (число)
                'found_at': timezone.now(),
                'is_notified': True,
                'address': address,
                'color': product.get('color', 'Разноцветный'),
                'metro_stations': metro_stations,
                'full_location': full_location,
                'is_favorite': False,
                'condition': product.get('condition'),
                'source': source,

                # 🔥 ДОБАВЛЯЕМ ВСЕ НОВЫЕ ПОЛЯ AUTO.RU
                'steering': product.get('steering', ''),
                'transmission': product.get('transmission', ''),
                'drive': product.get('drive', ''),
                'engine': product.get('engine', ''),
                'year': year_value,
                'mileage': product.get('mileage', ''),
                'owners': product.get('owners', ''),
                'pts': product.get('pts', ''),
                'tax': product.get('tax', ''),
                'customs': product.get('customs', ''),
                'body': product.get('body', ''),
                'package': product.get('package', ''),
                'price_status': product.get('price_status', ''),
                'discount_price': discount_price_value,
                'product_id': product_id,
                'seller_avatar': product.get('seller_avatar'),
                'seller_profile_url': product.get('seller_profile_url'),

                # 🔥 ДОБАВЛЯЕМ ML-ПОЛЯ (если они есть в модели FoundItem)
                'ml_freshness_score': product.get('ml_freshness_score', 0.5),  # ← ML ОЦЕНКА СВЕЖЕСТИ
                'priority_score': product.get('priority_score', 50.0),  # ← ПРИОРИТЕТНЫЙ СКОР
                'freshness_category': product.get('ml_freshness_category', 'БЕЗ ML'),  # ← КАТЕГОРИЯ СВЕЖЕСТИ

                # 🔥 НОВЫЕ ПОЛЯ ДЛЯ ТРЕКИНГА ВРЕМЕНИ
                'parse_time_display': parse_time_display,
                'parse_time_seconds': int(parse_duration),
                'search_duration_seconds': int(search_duration),
                'total_processing_seconds': int(total_duration),
                'time_status': time_status,
            }

            # 🔥 ДОБАВЛЯЕМ seller_type ТОЛЬКО ЕСЛИ ОНО ЕСТЬ В МОДЕЛИ
            try:
                # Проверяем, существует ли поле seller_type в модели FoundItem
                if hasattr(FoundItem, 'seller_type'):
                    found_item_data['seller_type'] = product.get('seller_type', 'Не указано')
            except Exception:
                pass  # Молча игнорируем, если поле не существует

            # 🔥 УБИРАЕМ ПОЛЯ КОТОРЫХ НЕТ В МОДЕЛИ
            fields_to_check = [
                'ml_freshness_score', 'priority_score', 'freshness_category',
                'parse_time_display', 'parse_time_seconds', 'search_duration_seconds',
                'total_processing_seconds', 'time_status'
            ]
            for field_name in fields_to_check:
                if field_name in found_item_data and not hasattr(FoundItem, field_name):
                    del found_item_data[field_name]

            found_item = FoundItem(**found_item_data)

            try:
                found_item.save()

                # 🔥 ЛОГИРУЕМ ВСЕ СОХРАНЕННЫЕ ДАННЫЕ С ML И ВРЕМЕНЕМ
                logger.info(f"✅ Товар сохранен в базу для пользователя {user.username}: {product['name']}")
                logger.info(f"📦 Сохраненные данные:")
                logger.info(f"├──👤 Владелец: {user.username} (ID: {user_id})")
                logger.info(f"├──🚗 Модель: {found_item.title}")
                logger.info(f"├──💰 Цена: {found_item.price}₽")
                logger.info(f"├──🎯 Целевая цена: {found_item.target_price}₽")

                # 🔥 ЛОГИРУЕМ ML-ПОЛЯ если они сохранились
                if hasattr(found_item, 'ml_freshness_score'):
                    logger.info(f"├──🧠 ML свежесть: {found_item.ml_freshness_score}")
                else:
                    logger.info(f"├──🧠 ML свежесть: НЕ СОХРАНЕНО (нет в модели)")

                if hasattr(found_item, 'priority_score'):
                    logger.info(f"├──🏆 Приоритет: {found_item.priority_score}")
                else:
                    logger.info(f"├──🏆 Приоритет: НЕ СОХРАНЕНО (нет в модели)")

                if hasattr(found_item, 'freshness_category'):
                    logger.info(f"├──📊 Категория свежести: {found_item.freshness_category}")
                else:
                    logger.info(f"├──📊 Категория свежести: НЕ СОХРАНЕНО (нет в модели)")

                # 🔥 ЛОГИРУЕМ ВРЕМЯ ОБРАБОТКИ
                if hasattr(found_item, 'parse_time_display'):
                    logger.info(f"├──⏱️ Время парсинга: {found_item.parse_time_display}")
                else:
                    logger.info(f"├──⏱️ Время парсинга: НЕ СОХРАНЕНО (нет в модели)")

                if hasattr(found_item, 'time_status'):
                    logger.info(f"├──🏁 Статус скорости: {found_item.time_status}")
                else:
                    logger.info(f"├──🏁 Статус скорости: НЕ СОХРАНЕНО (нет в модели)")

                logger.info(f"├──🏷️ Статус цены: {getattr(found_item, 'price_status', '')}")
                logger.info(f"├──🆔 ID: {getattr(found_item, 'product_id', '')}")
                logger.info(f"├──🔗 Ссылка: {found_item.url}")
                logger.info(f"├──📅 Год: {getattr(found_item, 'year', '')}")
                logger.info(f"├──🛣️ Пробег: {getattr(found_item, 'mileage', '')}")
                logger.info(f"├──⚙️ Двигатель: {getattr(found_item, 'engine', '')}")
                logger.info(f"├──🎨 Цвет: {getattr(found_item, 'color', '')}")
                logger.info(f"├──🔧 Коробка: {getattr(found_item, 'transmission', '')}")
                logger.info(f"├──🚗 Привод: {getattr(found_item, 'drive', '')}")
                logger.info(f"├──🚙 Кузов: {getattr(found_item, 'body', '')}")
                logger.info(f"├──📦 Комплектация: {getattr(found_item, 'package', '')}")
                logger.info(f"├──🔧 Состояние: {getattr(found_item, 'condition', '')}")
                logger.info(f"├──🏠 Адрес: {getattr(found_item, 'address', '')}")
                logger.info(f"├──🏙️ Город: {getattr(found_item, 'city', '')}")
                logger.info(f"├──🚇 Метро: {len(getattr(found_item, 'metro_stations', []))} станций")
                logger.info(f"├──👤 Продавец: {getattr(found_item, 'seller_name', '')}")

                # 🔥 ЛОГИРУЕМ АВАТАРКУ ПРОДАВЦА
                if getattr(found_item, 'seller_avatar', None):
                    logger.info(f"├──🖼️ Аватар продавца: {found_item.seller_avatar}")

                # 🔥 ЛОГИРУЕМ seller_type ТОЛЬКО ЕСЛИ ОНО ЕСТЬ
                if hasattr(found_item, 'seller_type'):
                    logger.info(f"├──🏢 Тип продавца: {found_item.seller_type}")

                logger.info(f"├──⭐ Рейтинг продавца: {getattr(found_item, 'seller_rating', '')}")
                logger.info(f"├──📊 Отзывов: {getattr(found_item, 'reviews_count', 0)}")
                logger.info(f"├──👁️ Просмотры: {getattr(found_item, 'views_count', 0)}")
                logger.info(
                    f"├──👁️ Просмотров сегодня: {getattr(found_item, 'views_today', 0)}")
                logger.info(f"├──📅 Дата размещения: {getattr(found_item, 'posted_date', '')}")
                logger.info(f"├──🖼️ Фото: {len(getattr(found_item, 'image_urls', []))}")
                logger.info(f"├──💰 Цена со скидкой: {getattr(found_item, 'discount_price', 0)}₽")
                logger.info(f"├──📝 Описание: {len(getattr(found_item, 'description', ''))} симв.")
                logger.info(f"└──🔗 Источник: {found_item.source}")

                return True

            except IntegrityError as e:
                logger.warning(f"🚫 Товар уже существует у пользователя {user.username}: {product['name']}")
                return False
            except Exception as save_error:
                logger.error(f"❌ Ошибка при сохранении товара для пользователя {user.username}: {save_error}")

                # 🔥 АЛЬТЕРНАТИВНЫЙ СПОСОБ СОХРАНЕНИЯ БЕЗ ОПЦИОНАЛЬНЫХ ПОЛЕЙ
                try:
                    logger.info("🔄 Пробуем сохранить без опциональных полей...")

                    # Оставляем только основные поля
                    basic_fields = ['search_query', 'parsed_by', 'title', 'price', 'url',
                                    'description', 'found_at', 'category', 'city', 'source']

                    basic_data = {k: found_item_data[k] for k in basic_fields if k in found_item_data}

                    found_item_alt = FoundItem(**basic_data)
                    found_item_alt.save()
                    logger.info(f"✅ Товар сохранен только с основными полями для пользователя {user.username}")
                    return True
                except Exception as alt_error:
                    logger.error(f"❌ Ошибка альтернативного сохранения для пользователя {user.username}: {alt_error}")
                    return False

        except Exception as e:
            logger.error(f"❌ Критическая ошибка сохранения товара: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def process_and_notify(self, product_data, economy, economy_percent, user_id):
        """🔥 ПРОСТО СОХРАНЯЕМ И ОТПРАВЛЯЕМ - ИСПОЛЬЗУЕМ send_notification"""
        try:
            # 🔥 ПЕРЕДАЕМ user_id В СОХРАНЕНИЕ
            saved_product = await self.save_product_to_db(product_data, economy, economy_percent, user_id)
            if not saved_product:
                return False

            # 🔥 ОТПРАВЛЯЕМ В ТЕЛЕГРАМ ЧЕРЕЗ СУЩЕСТВУЮЩИЙ send_notification
            telegram_sent = await self.send_notification(product_data)
            return telegram_sent

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False

    @sync_to_async
    def add_to_favorites(self, product_url, user_id=None):
        """Добавляет товар в избранное"""
        try:
            from apps.website.models import FoundItem
            from django.contrib.auth.models import User

            logger.info(f"⭐ Добавление в избранное: {product_url} для пользователя {user_id}")

            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    logger.error(f"❌ Пользователь не найден: {user_id}")
                    return False
            else:
                user = User.objects.first()
                if not user:
                    logger.error("❌ Пользователь не найден для добавления в избранное")
                    return False

            found_item = None
            found_items = FoundItem.objects.filter(url__contains=product_url)
            for item in found_items:
                if item.search_query.user == user:
                    found_item = item
                    break

            if not found_item:
                normalized_url = self.normalize_url_universal(product_url)
                found_items = FoundItem.objects.filter(url=normalized_url)
                for item in found_items:
                    if item.search_query.user == user:
                        found_item = item
                        break

            if not found_item:
                logger.warning(f"⚠️ Товар не найден в базе для пользователя {user.username}: {product_url}")
                return False

            if found_item.is_favorite:
                logger.info(f"ℹ️ Товар уже в избранном: {found_item.title}")
                return True

            found_item.is_favorite = True
            found_item.save()

            logger.info(f"✅ Товар добавлен в избранное: {found_item.title} для пользователя {user.username}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка добавления в избранное: {e}")
            return False

    def send_favorite_to_telegram(self, product_data, user):
        """📨 Отправляет уведомление о добавлении в избранное в Telegram

        🎯 Использует существующий NotificationSender для форматирования
        ❤️ Всегда показывает "ДОБАВЛЕНО В ИЗБРАННОЕ"
        📸 Отправляет фото через медиагруппу как парсер
        🔗 Ссылка на сайт ВНУТРИ текста (как у парсера)
        """
        try:
            logger.info(f"🚀 Отправка избранного для {user.username}")

            # 1. Подготавливаем данные для notification_sender
            # Добавляем недостающие поля
            if 'economy' not in product_data:
                economy = product_data.get('target_price', 0) - product_data.get('price', 0)
                product_data['economy'] = economy
                if product_data.get('target_price', 0) > 0:
                    product_data['economy_percent'] = int((economy / product_data['target_price']) * 100)
                else:
                    product_data['economy_percent'] = 0

            # Определяем source если нет
            if 'source' not in product_data:
                url = product_data.get('url', '').lower()
                if 'auto.ru' in url:
                    product_data['source'] = 'auto_ru'
                    product_data['site'] = 'auto.ru'
                else:
                    product_data['source'] = 'avito'
                    product_data['site'] = 'avito'

            # Добавляем необходимые поля для NotificationSender
            if 'avito_category' not in product_data and 'category' in product_data:
                product_data['avito_category'] = product_data['category']

            # Проверяем наличие rating полей
            if 'seller_rating' not in product_data:
                product_data['seller_rating'] = product_data.get('seller_rating', 5.0)

            if 'reviews_count' not in product_data:
                product_data['reviews_count'] = product_data.get('reviews_count', 0)

            # Проверяем seller_type
            if 'seller_type' not in product_data:
                seller_type = product_data.get('seller_type', '')
                if seller_type in ['Магазин', 'Компания', 'reseller']:
                    product_data['seller_type'] = 'reseller'
                else:
                    product_data['seller_type'] = 'private'

            # Проверяем состояние товара
            if 'condition' not in product_data:
                product_data['condition'] = 'Не указано'

            # Проверяем цвет
            if 'color' not in product_data:
                product_data['color'] = 'Разноцветный'

            # 2. Получаем фото из разных источников
            all_images = []

            # Сначала image_urls
            image_urls = product_data.get('image_urls', [])
            if image_urls:
                logger.info(f"📸 Найдено {len(image_urls)} изображений в image_urls")
                all_images = image_urls[:10]  # Берем до 10 фото (максимум для медиагруппы)

            # Если нет image_urls, пробуем image_url
            if not all_images and product_data.get('image_url'):
                image_url = product_data['image_url']
                logger.info(f"📸 Используем основное фото: {image_url}")
                all_images = [image_url]

            # Если совсем нет фото
            if not all_images:
                logger.warning("⚠️ Нет фото для отправки")

            logger.info(f"📸 Всего фото для отправки: {len(all_images)}")

            # 3. Используем существующий NotificationSender
            notification_sender = NotificationSender()

            # Форматируем сообщение через существующий метод
            message = notification_sender._format_message(product_data)

            logger.info(f"📝 Сформировано сообщение ({len(message)} символов)")

            # 4. Меняем заголовок на "ДОБАВЛЕНО В ИЗБРАННОЕ"
            # Находим первую строку с заголовком
            lines = message.split('\n')

            if lines and 'ВЫГОДНАЯ СДЕЛКА' in lines[0]:
                # Меняем заголовок для выгодной сделки
                lines[0] = '❤️ <b>ДОБАВЛЕНО В ИЗБРАННОЕ</b>'
                # Добавляем подзаголовок о выгоде на второй строке
                lines.insert(1, '💰 <b>Выгодное предложение!</b>')
                logger.info("✅ Заголовок изменен на '❤️ ДОБАВЛЕНО В ИЗБРАННОЕ' с подзаголовком о выгоде")
            elif lines and 'ИНТЕРЕСНОЕ ПРЕДЛОЖЕНИЕ' in lines[0] or 'ИНТЕРЕСНЫЙ АВТОМОБИЛЬ' in lines[0]:
                # Меняем заголовок для обычного предложения
                lines[0] = '❤️ <b>ДОБАВЛЕНО В ИЗБРАННОЕ</b>'
                logger.info("✅ Заголовок изменен на '❤️ ДОБАВЛЕНО В ИЗБРАННОЕ'")
            elif lines and '❤️' not in lines[0]:
                # Если нет узнаваемого заголовка, добавляем наш
                lines.insert(0, '❤️ <b>ДОБАВЛЕНО В ИЗБРАННОЕ</b>')
                logger.info("✅ Добавлен заголовок '❤️ ДОБАВЛЕНО В ИЗБРАННОЕ'")

            # Для Auto.ru добавляем тег #избранное в конец тегов
            if 'auto.ru' in product_data.get('url', '').lower():
                for i, line in enumerate(lines):
                    if line.startswith("#️⃣ <b>Теги:</b>"):
                        lines[i] = line + " #избранное"
                        break

            # Для Avito добавляем тег #избранное
            elif 'avito' in product_data.get('url', '').lower():
                for i, line in enumerate(lines):
                    if line.startswith("#️⃣ <b>Теги:"):
                        lines[i] = line + " #избранное"
                        break

            message = '\n'.join(lines)

            # 5. Отправляем сообщение через существующий бот
            try:
                from shared.utils.config import get_bot_token, get_chat_id
                from telegram import Bot

                token = get_bot_token()
                chat_id = get_chat_id()

                if not token or not chat_id:
                    logger.error("❌ Токен или Chat ID не установлены")
                    return False

                # Фильтруем валидные URL фото (исключаем миниатюры и невалидные)
                valid_image_urls = []
                for url in all_images:
                    if url and isinstance(url, str) and url != '' and not url.startswith('data:'):
                        # Пропускаем миниатюры (авто.ru часто их добавляет)
                        if '128x96' not in url and '64x48' not in url and '32x24' not in url:
                            # Проверяем, что это обычная картинка, а не иконка
                            if not url.endswith('.svg') and not url.endswith('.ico'):
                                valid_image_urls.append(url)

                logger.info(f"📸 Валидных фото для отправки: {len(valid_image_urls)}")

                # Отправляем через существующий бот
                bot = Bot(token=token)

                async def send_async():
                    try:
                        # Если есть фото - отправляем с фото через медиагруппу
                        if valid_image_urls:
                            logger.info(f"📸 Отправляем медиа-группу из {len(valid_image_urls)} фото")

                            # Загружаем фото в base64 как это делает NotificationSender
                            image_data_list = []

                            for photo_url in valid_image_urls[:10]:  # максимум 10 фото для медиагруппы
                                try:
                                    image_base64 = await notification_sender._url_to_base64(photo_url)
                                    if image_base64:
                                        image_data_list.append(image_base64)
                                        logger.info(f"✅ Загружено фото: {photo_url}")
                                    else:
                                        logger.warning(f"⚠️ Не удалось загрузить фото: {photo_url}")
                                except Exception as e:
                                    logger.warning(f"⚠️ Ошибка загрузки фото {photo_url}: {e}")

                            if image_data_list:
                                # 🔥 ВАЖНО: В медиагруппе НЕ используем reply_markup (кнопки не поддерживаются)
                                # Ссылка уже есть в тексте (как у парсера)
                                success = await notification_sender._send_media_group_with_caption(
                                    bot, chat_id, image_data_list, message, reply_markup=None  # ← БЕЗ кнопок!
                                )

                                if success:
                                    logger.info(
                                        f"✅ Уведомление отправлено с {len(image_data_list)} фото: {product_data.get('name')}")
                                    return True
                                else:
                                    logger.warning("⚠️ Не удалось отправить медиа-группу, пробуем текст")
                                    # Fallback на текстовое сообщение БЕЗ кнопок
                                    await bot.send_message(
                                        chat_id=chat_id,
                                        text=message,
                                        parse_mode='HTML',
                                        disable_web_page_preview=True
                                    )
                                    logger.info(f"✅ Текстовое уведомление отправлено: {product_data.get('name')}")
                                    return True
                            else:
                                logger.warning("⚠️ Не удалось загрузить ни одного фото, отправляем текст")

                        # Если нет фото или не удалось отправить фото - отправляем текст БЕЗ кнопок
                        logger.info("📨 Отправляем текстовое сообщение БЕЗ кнопок")
                        await bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )

                        logger.info(f"✅ Уведомление отправлено: {product_data.get('name')}")
                        return True

                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки: {e}")
                        import traceback
                        traceback.print_exc()
                        return False

                # Запускаем асинхронную отправку
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(send_async())
                    return result
                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"❌ Ошибка в отправке: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в send_favorite_to_telegram: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def send_parsing_start_notification(self, query, window_index, total_queries, query_index, user_id=None):
        """Отправляет уведомление о начале парсинга запроса в Telegram"""
        try:
            from shared.utils.config import get_bot_token, get_chat_id
            from telegram import Bot

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                logger.warning("⚠️ Не удалось отправить уведомление: нет токена или chat_id")
                return False

            bot = Bot(token=token)

            # Получаем текущее время
            current_time = datetime.now().strftime("%H:%M:%S")

            # Информация о пользователе если есть
            user_info = ""
            if user_id:
                try:
                    from django.contrib.auth.models import User
                    user = await sync_to_async(User.objects.get)(id=user_id)
                    user_info = f"👤 <b>Пользователь:</b> {user.username}\n"
                except Exception:
                    user_info = f"👤 <b>Пользователь ID:</b> {user_id}\n"

            message = (
                f"🔍 <b>НАЧАЛО ПАРСИНГА</b>\n\n"
                f"{user_info}"
                f"⏰ <b>Время:</b> {current_time}\n"
                f"🖥️ <b>Окно:</b> {window_index + 1}\n"
                f"📊 <b>Запрос:</b> {query_index + 1}/{total_queries}\n"
                f"🔎 <b>Поиск:</b> <code>{escape(query)}</code>\n\n"
                f"⚡ <b>Статус:</b> Парсинг запущен..."
            )

            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info(f"✅ Уведомление о начале парсинга '{query}' отправлено в Telegram")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки уведомления о начале парсинга: {e}")
            return False

    async def send_parsing_results_notification(self, query, window_index, found_count, items_processed, user_id=None):
        """Отправляет уведомление о результатах парсинга в Telegram"""
        try:
            from shared.utils.config import get_bot_token, get_chat_id
            from telegram import Bot

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                logger.warning("⚠️ Не удалось отправить уведомление: нет токена или chat_id")
                return False

            bot = Bot(token=token)

            # Получаем текущее время
            current_time = datetime.now().strftime("%H:%M:%S")

            # Информация о пользователе если есть
            user_info = ""
            if user_id:
                try:
                    from django.contrib.auth.models import User
                    user = await sync_to_async(User.objects.get)(id=user_id)
                    user_info = f"👤 <b>Пользователь:</b> {user.username}\n"
                except Exception:
                    user_info = f"👤 <b>Пользователь ID:</b> {user_id}\n"

            filtered_count = found_count - items_processed

            message = (
                f"📊 <b>РЕЗУЛЬТАТЫ ПАРСИНГА</b>\n\n"
                f"{user_info}"
                f"⏰ <b>Время:</b> {current_time}\n"
                f"🖥️ <b>Окно:</b> {window_index + 1}\n"
                f"🔎 <b>Запрос:</b> <code>{escape(query)}</code>\n\n"
                f"📈 <b>Результаты:</b>\n"
                f"• Найдено товаров: <b>{found_count}</b>\n"
                f"• Обработано: <b>{items_processed}</b>\n"
                f"• Отфильтровано: <b>{filtered_count}</b>\n\n"
                f"✅ <b>Статус:</b> Парсинг завершен"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info(f"✅ Уведомление о результатах парсинга '{query}' отправлено в Telegram")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки уведомления о результатах: {e}")
            return False

    async def send_parser_start_notification(self, parser_data, user_id=None):
        """Отправляет уведомление о старте парсера в Telegram"""
        try:
            from shared.utils.config import get_bot_token, get_chat_id
            from telegram import Bot

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                logger.warning("⚠️ Не удалось отправить уведомление: нет токена или chat_id")
                return False

            bot = Bot(token=token)

            # Получаем текущее время
            current_time = datetime.now().strftime("%H:%M:%S")

            # Информация о пользователе если есть
            user_info = ""
            if user_id:
                try:
                    from django.contrib.auth.models import User
                    user = await sync_to_async(User.objects.get)(id=user_id)
                    user_info = f"👤 <b>Пользователь:</b> {user.username}\n"
                except Exception:
                    user_info = f"👤 <b>Пользователь ID:</b> {user_id}\n"

            message = (
                f"🚀 <b>ПАРСЕР ЗАПУЩЕН</b>\n\n"
                f"{user_info}"
                f"⏰ <b>Время старта:</b> {current_time}\n"
                f"🖥️ <b>Окон браузера:</b> {parser_data.get('browser_windows', 1)}\n"
                f"🔎 <b>Запросов:</b> {parser_data.get('queries_count', 0)}\n"
                f"🌐 <b>Сайт:</b> {parser_data.get('site', 'avito')}\n"
                f"🏙️ <b>Город:</b> {parser_data.get('city', 'Москва')}\n\n"
                f"⚡ <b>Статус:</b> Запускаем парсинг..."
            )

            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info("✅ Уведомление о старте парсера отправлено в Telegram")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки уведомления о старте: {e}")
            return False

    async def send_parser_stop_notification(self, stats, user_id=None, reason="Нормальная остановка"):
        """Отправляет уведомление об остановке парсера в Telegram"""
        try:
            from shared.utils.config import get_bot_token, get_chat_id
            from telegram import Bot

            token = get_bot_token()
            chat_id = get_chat_id()

            if not token or not chat_id:
                logger.warning("⚠️ Не удалось отправить уведомление: нет токена или chat_id")
                return False

            bot = Bot(token=token)

            # Получаем текущее время
            current_time = datetime.now().strftime("%H:%M:%S")

            # Информация о пользователе если есть
            user_info = ""
            if user_id:
                try:
                    from django.contrib.auth.models import User
                    user = await sync_to_async(User.objects.get)(id=user_id)
                    user_info = f"👤 <b>Пользователь:</b> {user.username}\n"
                except Exception:
                    user_info = f"👤 <b>Пользователь ID:</b> {user_id}\n"

            # Форматируем статистику
            stats_text = ""
            if stats:
                stats_text = (
                    f"📊 <b>Статистика работы:</b>\n"
                    f"• Обработано запросов: {stats.get('total_searches', 0)}\n"
                    f"• Найдено товаров: {stats.get('items_found', 0)}\n"
                    f"• Хороших сделок: {stats.get('good_deals_found', 0)}\n"
                    f"• Свежих сделок: {stats.get('fresh_deals_found', 0)}\n"
                    f"• Время работы: {stats.get('uptime', '0ч 0м')}\n\n"
                )

            message = (
                f"🛑 <b>ПАРСЕР ОСТАНОВЛЕН</b>\n\n"
                f"{user_info}"
                f"⏰ <b>Время остановки:</b> {current_time}\n"
                f"📝 <b>Причина:</b> {reason}\n\n"
                f"{stats_text}"
                f"✅ <b>Статус:</b> Парсер успешно остановлен"
            )

            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info("✅ Уведомление об остановке парсера отправлено в Telegram")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки уведомления об остановке: {e}")
            return False

    async def send_demo_notification(self):
        """Отправляет демо-уведомление"""
        try:
            token = get_bot_token()
            chat_id = get_chat_id()

            demo_products = [
                {
                    'name': 'iPhone 13 Pro, 128 ГБ',
                    'price': 29500,
                    'target_price': 20650,
                    'url': 'https://www.avito.ru/moskva/telefony/iphone_13_pro_128_gb_7581377646',
                    'category': 'Телефоны',
                    'seller_name': 'Пользователь',
                    'seller_rating': 4.8,
                    'reviews_count': 16,
                    'description': 'Приветствую. На продажу Apple iPhone 13 Pro 128GB Sierra Blue, без комплекта. Состояние отличное, батарея 98%. Все функции работают корректно. Только самовывоз.',
                    'avito_category': 'Телефоны',
                    'posted_date': 'сегодня в 07:45',
                    'city': 'Москва',
                    'views_count': 25,
                    'metro_stations': [
                        {'name': 'Таганская', 'color': 'rgb(145, 81, 51)'},
                        {'name': 'Марксистская', 'color': 'rgb(148, 62, 144)'}
                    ],
                    'address': 'Москва, Нижняя Радищевская ул.',
                    'economy': 8850,
                    'economy_percent': 30,
                    'parse_time_display': '2:57',
                    'time_status': '⚡ Молниеносно'
                }
            ]

            product = random.choice(demo_products)
            message = self._format_message(product)
            reply_markup = self.create_notification_keyboard(product['url'])

            bot = Bot(token=token)
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            logger.info("✅ Демо-уведомление отправлено")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка демо-отправки: {e}")
            return False

    async def send_test_notification(self, test_message="Тестовое уведомление от системы"):
        """Отправляет тестовое уведомление"""
        try:
            token = get_bot_token()
            chat_id = get_chat_id()

            message_lines = []
            message_lines.append("🧪 <b>ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>")
            message_lines.append("")
            message_lines.append(test_message)
            message_lines.append("")
            message_lines.append("⏱️ <b>Время обработки:</b> 2:57 (⚡ Молниеносно)")
            message_lines.append("✅ Система работает корректно")
            message_lines.append("🕒 Время теста")
            message_lines.append("📊 Статус: Активен")
            message_lines.append("")
            message_lines.append("#тест #система #работает #время_обработки")

            message = "\n".join(message_lines)

            keyboard = [
                [
                    InlineKeyboardButton("🌐 Перейти на сайт", url="http://127.0.0.1:8000"),
                    InlineKeyboardButton("⭐ Тест избранное", callback_data="favorite_test")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            bot = Bot(token=token)
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

            logger.info("✅ Тестовое уведомление отправлено")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка тестовой отправки: {e}")
            return False