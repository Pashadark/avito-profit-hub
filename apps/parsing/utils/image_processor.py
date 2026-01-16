# utils/image_processor.py
import requests
import base64
import re
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger('parser.image_processor')


class ImageProcessor:
    """Универсальный обработчик изображений для Avito и Auto.ru с УЛУЧШЕННЫМ качеством"""

    def __init__(self, driver):
        self.driver = driver

    def get_images(self, site='avito'):
        """Универсальный метод получения изображений для разных сайтов"""
        if site == 'auto.ru':
            return self.get_auto_ru_images_improved()
        else:
            return self.get_avito_images()

    def get_auto_ru_images_improved(self):
        """🔥 ПЕРЕПИСАННЫЙ метод получения фото Auto.ru в МАКСИМАЛЬНОМ КАЧЕСТВЕ"""
        try:
            logger.info("🎯 АВТОМАТИЧЕСКИЙ поиск фото Auto.ru в МАКСИМАЛЬНОМ качестве...")

            # 🔥 ПРИОРИТЕТ 1: Получаем ОРИГИНАЛЬНЫЕ фото через клик по галерее
            original_images = self._get_auto_ru_original_images()
            if original_images and len(original_images) > 1:
                logger.info(f"✅ Найдено {len(original_images)} ОРИГИНАЛЬНЫХ фото через галерею")
                return original_images

            # 🔥 ПРИОРИТЕТ 2: Прямая навигация по миниатюрам
            if not original_images or len(original_images) <= 1:
                direct_images = self._get_auto_ru_images_direct_navigation()
                if direct_images:
                    logger.info(f"✅ Найдено {len(direct_images)} фото через прямую навигацию")
                    return direct_images

            # 🔥 ПРИОРИТЕТ 3: Ищем в JavaScript данных
            js_images = self._get_auto_ru_images_from_js_enhanced()
            if js_images:
                logger.info(f"✅ Найдено {len(js_images)} фото через JS")
                return js_images

            # 🔥 ПРИОРИТЕТ 4: Прямой поиск в HTML
            html_images = self._get_auto_ru_images_from_html_enhanced()
            logger.info(f"✅ Найдено {len(html_images)} фото через HTML")
            return html_images

        except Exception as e:
            logger.error(f"❌ Критическая ошибка поиска фото Auto.ru: {e}")
            return []

    def _get_auto_ru_original_images(self):
        """🔥 Получает ОРИГИНАЛЬНЫЕ фото через галерею"""
        try:
            logger.info("🖼️ Получение ОРИГИНАЛЬНЫХ фото через галерею...")

            # Открываем галерею
            if not self._open_auto_ru_gallery_enhanced():
                logger.warning("❌ Не удалось открыть галерею")
                return []

            # Собираем ОРИГИНАЛЬНЫЕ фото
            original_images = self._collect_original_gallery_images()

            # Закрываем галерею
            self._close_auto_ru_gallery()

            return original_images

        except Exception as e:
            logger.error(f"❌ Ошибка получения оригинальных фото: {e}")
            try:
                self._close_auto_ru_gallery()
            except:
                pass
            return []

    def _open_auto_ru_gallery_enhanced(self):
        """🔥 УЛУЧШЕННОЕ открытие галереи Auto.ru"""
        try:
            gallery_triggers = [
                '.ImageGalleryDesktop__image',
                '.ImageGalleryDesktop__thumb:first-child',
                '.Brazzers__image:first-child',
                '.ImageGallery__image:first-child',
                'img[data-zone-name="gallery-image"]:first-child',
                '.Gallery__image:first-child'
            ]

            for trigger in gallery_triggers:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, trigger))
                    )
                    self.driver.execute_script("arguments[0].click();", element)
                    logger.info(f"✅ Галерея открыта через: {trigger}")
                    time.sleep(3)  # Ждем полной загрузки галереи
                    return True
                except Exception as e:
                    logger.debug(f"❌ Не удалось открыть через {trigger}: {e}")
                    continue

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка открытия галереи: {e}")
            return False

    def _collect_original_gallery_images(self):
        """🔥 Собирает ОРИГИНАЛЬНЫЕ фото из открытой галереи с улучшенной навигацией"""
        try:
            original_urls = set()
            max_photos = 30

            # 🔥 НАХОДИМ ЭЛЕМЕНТ ТЕКУЩЕГО ИЗОБРАЖЕНИЯ В ПОПАПЕ ГАЛЕРЕИ
            current_image_selectors = [
                '.ImageGalleryFullscreenVertical__image img',
                '.ImageGalleryPopup__image img',
                '.GalleryPopup__image img',
                '.swiper-slide-active img',
                '.ImageGalleryFullscreen__image img',
                'img[class*="FullscreenVertical__image"]'
            ]

            current_image_element = None
            for selector in current_image_selectors:
                try:
                    current_image_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Найден элемент изображения в галерее: {selector}")
                    break
                except:
                    continue

            if not current_image_element:
                logger.error("❌ Не найден элемент изображения в открытой галерее")
                return []

            # 🔥 ПОЛУЧАЕМ ПЕРВОЕ ФОТО В МАКСИМАЛЬНОМ КАЧЕСТВЕ
            first_image = self._get_original_image_url(current_image_element)
            if first_image:
                original_urls.add(first_image)
                logger.info(f"✅ Первое ОРИГИНАЛЬНОЕ фото: {first_image[:100]}...")

            # 🔥 НАХОДИМ КНОПКУ "ВПЕРЕД" С ПОВТОРНЫМИ ПОПЫТКАМИ
            next_button = None
            for attempt in range(3):
                next_button = self._find_gallery_next_button_enhanced()
                if next_button:
                    break
                logger.info(f"🔄 Попытка {attempt + 1} найти кнопку...")
                time.sleep(1)

            if not next_button:
                logger.warning("❌ Не найдена кнопка переключения, возвращаем только первое фото")
                return list(original_urls)

            # 🔥 ПЕРЕБИРАЕМ ВСЕ ФОТО В ГАЛЕРЕЕ С УЛУЧШЕННОЙ ОБРАБОТКОЙ
            previous_url = first_image

            for i in range(max_photos - 1):
                try:
                    logger.info(f"🔄 Переключаем на фото {i + 2}...")

                    # 🔥 ПРОБУЕМ РАЗНЫЕ СПОСОБЫ КЛИКА
                    click_success = False

                    # Способ 1: Обычный клик через JavaScript
                    try:
                        self.driver.execute_script("arguments[0].click();", next_button)
                        click_success = True
                        logger.info("✅ Клик через JavaScript выполнен")
                    except Exception as e:
                        logger.warning(f"❌ Ошибка JavaScript клика: {e}")

                    # Способ 2: ActionChains клик
                    if not click_success:
                        try:
                            ActionChains(self.driver).move_to_element(next_button).click().perform()
                            click_success = True
                            logger.info("✅ Клик через ActionChains выполнен")
                        except Exception as e:
                            logger.warning(f"❌ Ошибка ActionChains клика: {e}")

                    if not click_success:
                        logger.error("❌ Не удалось кликнуть по кнопке")
                        break

                    # 🔥 ЖДЕМ ЗАГРУЗКИ НОВОГО ФОТО
                    time.sleep(2)

                    # 🔥 ПРОВЕРЯЕМ, ИЗМЕНИЛОСЬ ЛИ ИЗОБРАЖЕНИЕ
                    new_image = self._get_original_image_url(current_image_element)

                    if not new_image:
                        logger.warning("❌ Не удалось получить новое изображение")
                        break

                    if new_image == previous_url:
                        logger.warning("⚠️ Изображение не изменилось после клика")
                        # Пробуем еще раз с большей задержкой
                        time.sleep(3)
                        new_image = self._get_original_image_url(current_image_element)

                        if new_image == previous_url:
                            logger.info("⚠️ Достигнут конец галереи")
                            break

                    if new_image and new_image not in original_urls:
                        original_urls.add(new_image)
                        logger.info(f"✅ ОРИГИНАЛЬНОЕ фото {len(original_urls)}: {new_image[:100]}...")
                        previous_url = new_image
                    else:
                        logger.info("⚠️ Дубликат фото или конец галереи")
                        break

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка на шаге {i + 1}: {e}")
                    # Пробуем продолжить со следующей фотографией
                    continue

            logger.info(f"🎯 Всего собрано ОРИГИНАЛЬНЫХ фото: {len(original_urls)}")
            return list(original_urls)

        except Exception as e:
            logger.error(f"❌ Ошибка сбора оригинальных фото: {e}")
            return []

    def _get_auto_ru_images_direct_navigation(self):
        """🔥 ПРЯМАЯ навигация по галерее без попапа"""
        try:
            logger.info("🔍 Прямая навигация по галерее Auto.ru...")
            original_urls = set()

            # 🔥 ИЩЕМ ВСЕ МИНИАТЮРЫ ГАЛЕРЕИ И КЛИКАЕМ ПО НИМ ПООЧЕРЕДНО
            thumbnail_selectors = [
                '.ImageGalleryDesktop__thumb',
                '.ImageGallery__thumb',
                '[data-zone-name="gallery-image"]',
                '.Gallery__thumb img'
            ]

            thumbnails = []
            for selector in thumbnail_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        thumbnails = elements
                        logger.info(f"✅ Найдено миниатюр: {len(thumbnails)}")
                        break
                except:
                    continue

            if not thumbnails:
                logger.warning("❌ Миниатюры галереи не найдены")
                return []

            # 🔥 ОГРАНИЧИВАЕМ КОЛИЧЕСТВО ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
            thumbnails = thumbnails[:15]

            for i, thumb in enumerate(thumbnails):
                try:
                    # 🔥 КЛИКАЕМ ПО МИНИАТЮРЕ
                    self.driver.execute_script("arguments[0].click();", thumb)
                    time.sleep(2)  # Ждем загрузки большого изображения

                    # 🔥 ИЩЕМ БОЛЬШОЕ ИЗОБРАЖЕНИЕ
                    large_image_selectors = [
                        '.ImageGalleryDesktop__image img',
                        '.ImageGallery__image img',
                        '[class*="gallery"] img[src*="avatars.mds.yandex.net"]'
                    ]

                    large_image_url = None
                    for selector in large_image_selectors:
                        try:
                            large_img = self.driver.find_element(By.CSS_SELECTOR, selector)
                            url = large_img.get_attribute('src')
                            if url and 'avatars.mds.yandex.net' in url:
                                original_url = self._convert_to_original_quality(url)
                                if original_url and original_url not in original_urls:
                                    large_image_url = original_url
                                    break
                        except:
                            continue

                    if large_image_url:
                        original_urls.add(large_image_url)
                        logger.info(f"✅ Фото {i + 1}: {large_image_url[:100]}...")
                    else:
                        logger.warning(f"⚠️ Не удалось получить фото {i + 1}")

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки миниатюры {i + 1}: {e}")
                    continue

            logger.info(f"🎯 Прямой метод собрал фото: {len(original_urls)}")
            return list(original_urls)

        except Exception as e:
            logger.error(f"❌ Ошибка прямой навигации: {e}")
            return []

    def _get_original_image_url(self, image_element):
        """🔥 Получает ОРИГИНАЛЬНЫЙ URL фото СРАЗУ в максимальном качестве"""
        try:
            # 🔥 ПРОВЕРЯЕМ ВСЕ ВОЗМОЖНЫЕ АТРИБУТЫ
            attributes = ['src', 'data-src', 'data-url', 'data-original', 'data-srcset']

            for attr in attributes:
                try:
                    url = image_element.get_attribute(attr)
                    if url and 'avatars.mds.yandex.net' in url:
                        # 🔥 ОБРАБАТЫВАЕМ SRCSET
                        if attr == 'data-srcset' and ',' in url:
                            # Берем самый большой вариант из srcset
                            variants = [v.strip() for v in url.split(',')]
                            best_variant = variants[0]  # Первый обычно самый большой
                            url = best_variant.split(' ')[0].strip()

                        # 🔥 ПРЕОБРАЗУЕМ В ОРИГИНАЛ СРАЗУ
                        original_url = self._convert_to_original_quality(url)
                        if original_url:
                            return original_url
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"⚠️ Ошибка получения оригинального URL: {e}")
            return None

    def _convert_to_original_quality(self, url):
        """🔥 ПРЕОБРАЗУЕТ ЛЮБОЙ URL В ОРИГИНАЛЬНОЕ КАЧЕСТВО"""
        try:
            if not url or 'avatars.mds.yandex.net' not in url:
                return url

            # 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Получаем ОРИГИНАЛЫ, а не просто большие размеры

            # Паттерн для URL Auto.ru: /get-autoru-vos/ID/HASH/size
            pattern = r'(https://avatars\.mds\.yandex\.net/get-autoru-[^/]+/[^/]+/[^/]+)/[^/?]+'
            match = re.search(pattern, url)

            if match:
                # 🔥 ВОЗВРАЩАЕМ ОРИГИНАЛЬНЫЙ URL БЕЗ РАЗМЕРОВ
                base_url = match.group(1)
                original_url = f"{base_url}/orig"
                logger.info(f"🎯 Преобразовано в ОРИГИНАЛ: {original_url[:100]}...")
                return original_url

            # 🔥 ДЛЯ СТАРЫХ ФОРМАТОВ URL
            if '/get-autoru-' in url:
                # Убираем ВСЕ параметры размера и добавляем /orig
                original_url = re.sub(r'/\d+x\d+[a-z]*', '/orig', url)
                original_url = original_url.split('?')[0]  # Убираем параметры

                # Если не добавился /orig, добавляем вручную
                if '/orig' not in original_url:
                    if original_url.endswith('/'):
                        original_url += 'orig'
                    else:
                        original_url += '/orig'

                logger.info(f"🎯 Преобразовано в ОРИГИНАЛ (старый формат): {original_url[:100]}...")
                return original_url

            return url

        except Exception as e:
            logger.warning(f"⚠️ Ошибка преобразования в оригинал: {e}")
            return url

    def _find_gallery_next_button_enhanced(self):
        """🔥 УЛУЧШЕННЫЙ поиск кнопки 'вперед' с правильными селекторами"""
        try:
            next_selectors = [
                '.ImageGalleryFullscreenVertical__nav_right',
                '.ImageGalleryFullscreenVertical__nav.ImageGalleryFullscreenVertical__nav_right',
                '.ImageGalleryPopup__nav_right',
                '.GalleryPopup__next',
                '[data-ga-name="next"]',
                '.swiper-button-next',
                '[class*="nav_right"]',
                'button[aria-label*="следующ"]',
                'button[aria-label*="next"]',
                # 🔥 ДОБАВЛЯЕМ СЕЛЕКТОРЫ ДЛЯ SVG КНОПОК
                'div[class*="nav_right"]',
                '.ImageGalleryFullscreenVertical__nav:last-child',
                '[class*="FullscreenVertical"] [class*="nav_right"]'
            ]

            for selector in next_selectors:
                try:
                    element = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Найдена кнопка переключения: {selector}")
                    return element
                except Exception as e:
                    logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            # 🔥 ЕСЛИ НЕ НАШЛИ КНОПКУ, ПРОБУЕМ НАЙТИ ЧЕРЕЗ XPath
            try:
                xpath_selectors = [
                    "//div[contains(@class, 'nav_right')]",
                    "//button[contains(@class, 'nav_right')]",
                    "//div[contains(@class, 'ImageGalleryFullscreenVertical__nav_right')]",
                    "//*[contains(@class, 'nav_right') and not(contains(@class, 'nav_left'))]"
                ]

                for xpath in xpath_selectors:
                    try:
                        element = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        logger.info(f"✅ Найдена кнопка через XPath: {xpath}")
                        return element
                    except:
                        continue
            except Exception as e:
                logger.debug(f"❌ XPath поиск не сработал: {e}")

            logger.warning("❌ Не найдена кнопка переключения фото")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка поиска кнопки: {e}")
            return None

    def _close_auto_ru_gallery(self):
        """Закрывает галерею Auto.ru"""
        try:
            close_selectors = [
                '.ImageGalleryFullscreenVertical__close',
                '.ImageGalleryPopup__close',
                '.Popup__close',
                '[data-ga-name="close"]',
                '.GalleryPopup__close'
            ]

            for selector in close_selectors:
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].click();", close_btn)
                    time.sleep(1)
                    return True
                except:
                    continue

            # Пробуем ESC
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                return True
            except:
                pass

            return False

        except Exception as e:
            logger.debug(f"⚠️ Ошибка закрытия галереи: {e}")
            return False

    def _get_auto_ru_images_from_js_enhanced(self):
        """🔥 УЛУЧШЕННЫЙ поиск фото в JavaScript данных"""
        try:
            logger.info("🔍 Улучшенный поиск фото в JS данных...")

            # Ищем во всех script элементах
            scripts = self.driver.find_elements(By.TAG_NAME, 'script')

            for script in scripts:
                try:
                    script_type = script.get_attribute('type') or ''
                    script_content = script.get_attribute('innerHTML') or script.text

                    if not script_content:
                        continue

                    # 🔥 ИЩЕМ ОРИГИНАЛЬНЫЕ URL В РАЗЛИЧНЫХ ФОРМАТАХ JSON
                    original_urls = self._extract_original_urls_from_text(script_content)
                    if original_urls:
                        logger.info(f"✅ Найдено {len(original_urls)} фото в JS")
                        return original_urls[:20]

                except Exception as e:
                    continue

            return []

        except Exception as e:
            logger.error(f"❌ Ошибка поиска в JS: {e}")
            return []

    def _extract_original_urls_from_text(self, text):
        """🔥 Извлекает ОРИГИНАЛЬНЫЕ URL из текста"""
        try:
            original_urls = set()

            # 🔥 РАЗЛИЧНЫЕ ПАТТЕРНЫ ДЛЯ ПОИСКА ОРИГИНАЛОВ
            patterns = [
                # Паттерн для оригинальных URL
                r'https://[^"]*avatars\.mds\.yandex\.net[^"]*/orig[^"]*',
                # Паттерн для URL с большими размерами
                r'https://[^"]*avatars\.mds\.yandex\.net[^"]*/1200x900[^"]*',
                r'https://[^"]*avatars\.mds\.yandex\.net[^"]*/1024x768[^"]*',
                # Паттерн для base URL которые можно преобразовать в оригиналы
                r'https://[^"]*avatars\.mds\.yandex\.net/get-autoru-[^/]+/[^/]+/[^/"/?]+'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text)
                for url in matches:
                    # 🔥 ПРЕОБРАЗУЕМ В ОРИГИНАЛ
                    original_url = self._convert_to_original_quality(url)
                    if original_url and original_url not in original_urls:
                        original_urls.add(original_url)
                        logger.info(f"🖼️ Найдено оригинальное фото: {original_url[:100]}...")

            return list(original_urls)

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения URL из текста: {e}")
            return []

    def _get_auto_ru_images_from_html_enhanced(self):
        """🔥 УЛУЧШЕННЫЙ поиск фото в HTML"""
        try:
            logger.info("🔍 Улучшенный поиск фото в HTML...")
            original_urls = set()

            # 🔥 ИЩЕМ ВСЕ ИЗОБРАЖЕНИЯ НА СТРАНИЦЕ
            all_images = self.driver.find_elements(By.TAG_NAME, 'img')

            for img in all_images:
                try:
                    # 🔥 ПРОВЕРЯЕМ РАЗМЕРЫ - исключаем мелкие иконки
                    try:
                        size = img.size
                        if size['width'] < 200 or size['height'] < 150:
                            continue
                    except:
                        pass

                    # 🔥 ПРОВЕРЯЕМ ВИДИМОСТЬ
                    if not img.is_displayed():
                        continue

                    # 🔥 ПОЛУЧАЕМ URL И ПРЕОБРАЗУЕМ В ОРИГИНАЛ
                    for attr in ['src', 'data-src', 'data-url']:
                        url = img.get_attribute(attr)
                        if url and 'avatars.mds.yandex.net' in url:
                            original_url = self._convert_to_original_quality(url)
                            if original_url and original_url not in original_urls:
                                original_urls.add(original_url)
                                logger.info(f"✅ HTML фото: {original_url[:100]}...")
                                break

                except Exception as e:
                    continue

            return list(original_urls)[:15]

        except Exception as e:
            logger.error(f"❌ Ошибка поиска в HTML: {e}")
            return []

    def get_avito_images(self):
        """🔥 УЛУЧШЕННЫЙ метод получения БОЛЬШИХ фото Avito через галерею"""
        try:
            logger.info("🎯 Автоматический поиск БОЛЬШИХ фото Avito...")

            # 🔥 ПРИОРИТЕТ 1: Открываем галерею и берем полноразмерные фото
            gallery_images = self._get_avito_gallery_images_enhanced()
            if gallery_images and len(gallery_images) > 1:
                logger.info(f"✅ Найдено {len(gallery_images)} БОЛЬШИХ фото через галерею")
                return gallery_images

            # 🔥 ПРИОРИТЕТ 2: Ищем большие фото прямо на странице
            main_images = self._get_avito_main_page_images()
            if main_images:
                logger.info(f"✅ Найдено {len(main_images)} фото со страницы")
                return main_images

            # 🔥 ПРИОРИТЕТ 3: Старый метод как fallback
            old_images = self.get_avito_images_fallback()
            if old_images:
                logger.info(f"✅ Найдено {len(old_images)} фото старым методом")
                return old_images

            logger.warning("❌ Фото не найдены")
            return []

        except Exception as e:
            logger.error(f"❌ Критическая ошибка поиска фото Avito: {e}")
            return self.get_avito_images_fallback()

    def _get_avito_gallery_images_enhanced(self):
        """🔥 Получает БОЛЬШИЕ фото через открытие галереи Avito"""
        try:
            logger.info("🖼️ Получение БОЛЬШИХ фото через галерею Avito...")

            # Открываем галерею
            if not self._open_avito_gallery():
                logger.warning("❌ Не удалось открыть галерею Avito")
                return []

            # Собираем БОЛЬШИЕ фото
            large_images = self._collect_large_gallery_images()

            # Закрываем галерею
            self._close_avito_gallery()

            return large_images

        except Exception as e:
            logger.error(f"❌ Ошибка получения больших фото: {e}")
            try:
                self._close_avito_gallery()
            except:
                pass
            return []

    def _open_avito_gallery(self):
        """🔥 Открывает галерею Avito кликом по фото"""
        try:
            logger.info("🔍 Попытка открытия галереи Avito...")

            gallery_triggers = [
                'img.desktop-1ky5g7j',  # ⬅️ ТВОЙ СЕЛЕКТОР!
                '[data-marker="image-frame/image-wrapper"]',
                '.image-frame-preview',
                '[data-marker*="image"] img',
                '.styles_imageWrapper__NoH_Y',
                'img[data-marker*="image"]',
                '.photo-slider-view__image',
                '[data-marker="image-preview/image"]',
                '.image-frame-picture'
            ]

            for trigger in gallery_triggers:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, trigger))
                    )
                    self.driver.execute_script("arguments[0].click();", element)
                    logger.info(f"✅ Галерея Avito открыта через: {trigger}")
                    time.sleep(3)  # Увеличиваем время для загрузки галереи
                    return True
                except Exception as e:
                    logger.debug(f"❌ Не удалось открыть через {trigger}: {e}")
                    continue

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка открытия галереи Avito: {e}")
            return False

    def _collect_large_gallery_images(self):
        """🔥 Собирает БОЛЬШИЕ фото из открытой галереи Avito"""
        try:
            large_urls = set()
            max_photos = 20

            # 🔥 ЖДЕМ ПОЛНОЙ ЗАГРУЗКИ ГАЛЕРЕИ
            time.sleep(4)

            # 🔥 ПРАВИЛЬНЫЕ СЕЛЕКТОРЫ ДЛЯ ГАЛЕРЕИ
            current_image_selectors = [
                '[data-marker="extended-gallery/frame-img"]',  # ⬅️ ТВОЙ СЕЛЕКТОР!
                '.styles__extended-gallery-img___XzRjNG',  # ⬅️ ТВОЙ СЕЛЕКТОР!
                '[data-marker="extended-gallery-frame/image"]',
                '.image-frame-preview-img',
                '.styles_previewImage__XzRjNG',
                '.gallery-img-preview',
                'img[class*="previewImage"]',
                '.photo-slider-view__image img'
            ]

            current_image_element = None
            for selector in current_image_selectors:
                try:
                    current_image_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Найден элемент изображения в галерее Avito: {selector}")

                    # Проверяем что изображение загружено
                    src = current_image_element.get_attribute('src')
                    if src and 'avito.st' in src:
                        logger.info(f"✅ Изображение загружено: {src[:100]}...")
                        break
                    else:
                        logger.warning("⚠️ Изображение найдено, но src невалидный")
                        current_image_element = None

                except Exception as e:
                    logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            if not current_image_element:
                logger.error("❌ Не найден элемент изображения в открытой галерее Avito")
                return []

            # 🔥 ПОЛУЧАЕМ ПЕРВОЕ ФОТО В БОЛЬШОМ КАЧЕСТВЕ
            first_image = self._get_large_avito_image_url(current_image_element)
            if first_image:
                large_urls.add(first_image)
                logger.info(f"✅ Первое БОЛЬШОЕ фото Avito: {first_image[:100]}...")
            else:
                logger.warning("❌ Не удалось получить URL первого изображения")
                return []

            # 🔥 НАХОДИМ КНОПКУ "ВПЕРЕД" ДЛЯ AVITO
            next_button = self._find_avito_gallery_next_button()
            if not next_button:
                logger.warning("❌ Не найдена кнопка переключения, возвращаем только первое фото")
                return list(large_urls)

            # 🔥 ПЕРЕБИРАЕМ ВСЕ ФОТО В ГАЛЕРЕЕ AVITO
            previous_url = first_image

            for i in range(max_photos - 1):
                try:
                    logger.info(f"🔄 Переключаем на фото Avito {i + 2}...")

                    # Кликаем по кнопке "вперед"
                    self.driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)  # Ждем загрузки нового фото

                    # Получаем новое фото
                    new_image = self._get_large_avito_image_url(current_image_element)

                    if not new_image:
                        logger.warning("❌ Не удалось получить новое изображение")
                        break

                    if new_image == previous_url:
                        logger.warning("⚠️ Изображение не изменилось после клика")
                        # Пробуем еще раз с большей задержкой
                        time.sleep(3)
                        new_image = self._get_large_avito_image_url(current_image_element)

                        if new_image == previous_url:
                            logger.info("⚠️ Достигнут конец галереи Avito")
                            break

                    if new_image and new_image not in large_urls:
                        large_urls.add(new_image)
                        logger.info(f"✅ БОЛЬШОЕ фото Avito {len(large_urls)}: {new_image[:100]}...")
                        previous_url = new_image
                    else:
                        logger.info("⚠️ Дубликат фото или конец галереи Avito")
                        break

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка на шаге {i + 1}: {e}")
                    continue

            logger.info(f"🎯 Всего собрано БОЛЬШИХ фото Avito: {len(large_urls)}")
            return list(large_urls)

        except Exception as e:
            logger.error(f"❌ Ошибка сбора больших фото Avito: {e}")
            return []

    def _get_large_avito_image_url(self, image_element):
        """🔥 Получает URL БОЛЬШОГО фото Avito из галереи"""
        try:
            # 🔥 ПРОВЕРЯЕМ ВСЕ ВОЗМОЖНЫЕ АТРИБУТЫ
            attributes = ['src', 'data-src', 'data-url', 'data-original', 'data-srcset']

            for attr in attributes:
                try:
                    url = image_element.get_attribute(attr)
                    if url and 'avito.st' in url:
                        logger.info(f"🔍 Найден URL в атрибуте {attr}: {url[:100]}...")

                        # 🔥 ПРЕОБРАЗУЕМ В БОЛЬШОЙ РАЗМЕР СРАЗУ
                        large_url = self._convert_to_large_avito_url(url)
                        if large_url:
                            logger.info(f"✅ Преобразовано в большой размер: {large_url[:100]}...")
                            return large_url
                except:
                    continue

            # 🔥 ЕСЛИ НЕ НАШЛИ В АТРИБУТАХ, ПРОБУЕМ ВЗЯТЬ ПРЯМО SRC
            try:
                url = image_element.get_attribute('src')
                if url and 'avito.st' in url:
                    large_url = self._convert_to_large_avito_url(url)
                    if large_url:
                        return large_url
            except:
                pass

            logger.warning("❌ Не удалось получить URL изображения")
            return None

        except Exception as e:
            logger.debug(f"⚠️ Ошибка получения URL большого фото Avito: {e}")
            return None

    def _convert_to_large_avito_url(self, url):
        """🔥 ПРЕОБРАЗУЕТ ЛЮБОЙ URL Avito В БОЛЬШОЙ РАЗМЕР"""
        try:
            if not url or 'avito.st' not in url:
                return url

            # 🔥 ЗАМЕНЯЕМ РАЗМЕРЫ НА БОЛЬШИЕ
            size_replacements = [
                ('64x48', '1280x960'),
                ('128x96', '1280x960'),
                ('256x192', '1280x960'),
                ('300x300', '1280x960'),
                ('200x200', '1280x960'),
                ('400x300', '1280x960'),
                ('640x480', '1280x960')
            ]

            large_url = url
            for small_size, large_size in size_replacements:
                if small_size in large_url:
                    large_url = large_url.replace(small_size, large_size)
                    break

            # 🔥 УДАЛЯЕМ ПАРАМЕТРЫ СЖАТИЯ И ДОБАВЛЯЕМ КАЧЕСТВО
            large_url = re.sub(r'__[^_]+__', '', large_url)

            # Добавляем параметр качества если его нет
            if '?' in large_url:
                if 'quality=' not in large_url:
                    large_url += '&quality=100'
            else:
                large_url += '?quality=100'

            logger.info(f"🎯 Преобразовано в БОЛЬШОЙ размер: {large_url[:100]}...")
            return large_url

        except Exception as e:
            logger.warning(f"⚠️ Ошибка преобразования в большой размер: {e}")
            return url

    def _find_avito_gallery_next_button(self):
        """🔥 Поиск кнопки 'вперед' в галерее Avito"""
        try:
            next_selectors = [
                '[data-marker="extended-gallery-frame/control-right"]',  # ⬅️ ТВОЙ СЕЛЕКТОР!
                '.styles__control-button_right___XzRjNG',  # ⬅️ ТВОЙ СЕЛЕКТОР!
                '[data-marker="extended-gallery/control-right"]',
                '.image-frame-forward',
                '.photo-slider-track-button-next',
                '[class*="control-right"]',
                '.swiper-button-next',
                'button[aria-label*="следующ"]',
                'button[aria-label*="next"]'
            ]

            for selector in next_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Найдена кнопка переключения Avito: {selector}")
                    return element
                except Exception as e:
                    logger.debug(f"❌ Селектор '{selector}' не сработал: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка поиска кнопки Avito: {e}")
            return None

    def _close_avito_gallery(self):
        """Закрывает галерею Avito"""
        try:
            close_selectors = [
                '[data-marker="extended-gallery-frame/control-close"]',
                '.styles__control-close___XzRjNG',
                '.image-frame-close',
                '.photo-slider-close',
                '[class*="close"]',
                'button[aria-label*="закрыть"]'
            ]

            for selector in close_selectors:
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].click();", close_btn)
                    time.sleep(1)
                    logger.info("✅ Галерея Avito закрыта")
                    return True
                except:
                    continue

            # Пробуем ESC
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                logger.info("✅ Галерея Avito закрыта по ESC")
                return True
            except:
                pass

            return False

        except Exception as e:
            logger.debug(f"⚠️ Ошибка закрытия галереи Avito: {e}")
            return False

    def _get_avito_main_page_images(self):
        """🔥 Ищет большие фото прямо на странице Avito"""
        try:
            logger.info("🔍 Поиск больших фото на основной странице Avito...")
            large_urls = set()

            # 🔥 СЕЛЕКТОРЫ ДЛЯ БОЛЬШИХ ФОТО НА ОСНОВНОЙ СТРАНИЦЕ
            main_page_selectors = [
                '[data-marker="image-frame/image-wrapper"] img',
                '.image-frame-picture img',
                '.photo-slider-view__image img',
                '[data-marker="image-preview/image"]',
                'img[src*="avito.st"][src*="1280x960"]',
                'img[src*="avito.st"][src*="1024x768"]'
            ]

            for selector in main_page_selectors:
                try:
                    images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in images:
                        src = img.get_attribute('src')
                        if src and self._is_large_avito_image(src):
                            large_url = self._convert_to_large_avito_url(src)
                            if large_url and large_url not in large_urls:
                                large_urls.add(large_url)
                                logger.info(f"✅ Большое фото со страницы: {large_url[:100]}...")

                    if large_urls:
                        break

                except Exception as e:
                    continue

            return list(large_urls)

        except Exception as e:
            logger.debug(f"❌ Ошибка поиска фото на странице Avito: {e}")
            return []

    def _is_large_avito_image(self, url):
        """Проверяет, является ли фото Avito большим"""
        if not url:
            return False

        # 🔥 ПРИЗНАКИ БОЛЬШИХ ФОТО AVITO
        large_indicators = [
            '1280x960', '1024x768', '800x600', 'orig_', 'large'
        ]

        # 🔥 ПРИЗНАКИ МАЛЕНЬКИХ ФОТО
        small_indicators = [
            '64x48', '128x96', '256x192', '300x300', '200x200'
        ]

        # Если есть признаки больших фото - ок
        if any(indicator in url for indicator in large_indicators):
            return True

        # Если нет признаков маленьких фото - считаем большим
        if not any(indicator in url for indicator in small_indicators):
            return True

        return False

    def get_avito_images_fallback(self):
        """Резервный метод получения изображений Avito"""
        try:
            logger.info("🔍 Используем резервный метод поиска изображений Avito...")
            images = []

            all_imgs = self.driver.find_elements(By.TAG_NAME, 'img')

            for img in all_imgs:
                try:
                    src = img.get_attribute('src')
                    if not src or 'avito.st' not in src:
                        continue

                    if self._is_avito_thumbnail(img, src) or self._is_avito_advertisement_image(img, src):
                        continue

                    quality_url = self._extract_avito_high_quality_url(src)
                    if quality_url and quality_url not in images:
                        images.append(quality_url)

                except:
                    continue

            images = images[:10]
            logger.info(f"✅ Резервным методом найдено {len(images)} изображений Avito")
            return images

        except Exception as e:
            logger.error(f"❌ Ошибка резервного метода Avito: {e}")
            return []

    def _is_avito_thumbnail(self, img_element, src):
        """Проверяет, является ли изображение Avito миниатюрой"""
        try:
            size = img_element.size
            if size['width'] < 150 or size['height'] < 150:
                return True

            thumbnail_indicators = ['_64x48', '_75x55', '_128x96', '_300x300', 'small', 'thumbnail', 'preview']
            if any(marker in src for marker in thumbnail_indicators):
                return True

            class_name = img_element.get_attribute('class') or ''
            thumbnail_classes = ['thumb', 'thumbnail', 'preview', 'mini', 'small']
            if any(thumb_class in class_name.lower() for thumb_class in thumbnail_classes):
                return True

            return False

        except:
            return False

    def _is_avito_advertisement_image(self, img_element, src):
        """Проверяет, является ли изображение Avito рекламой"""
        try:
            parent = img_element.find_element(By.XPATH, './..')
            parent_class = parent.get_attribute('class') or ''

            ad_indicators = ['ads', 'ad', 'banner', 'promo', 'recommendation', 'similar']
            if any(indicator in parent_class.lower() for indicator in ad_indicators):
                return True

            alt_text = img_element.get_attribute('alt') or ''
            if any(ad_word in alt_text.lower() for ad_word in ['реклама', 'баннер', 'ads', 'ad']):
                return True

            if any(ad_marker in src.lower() for ad_marker in ['/ads/', '/banners/', 'tracking', 'pixel']):
                return True

            return False

        except:
            return False

    def _get_current_avito_main_image_url(self, main_image_element):
        """Получает URL текущего основного изображения Avito"""
        try:
            attributes = ['src', 'data-src', 'data-url', 'data-original']

            for attr in attributes:
                url = main_image_element.get_attribute(attr)
                if url and 'avito.st' in url:
                    high_quality_url = self._extract_avito_high_quality_url(url)
                    return high_quality_url

            url = main_image_element.get_attribute('src')
            if url and 'avito.st' in url:
                return self._extract_avito_high_quality_url(url)

        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения URL изображения Avito: {e}")

        return None

    def _extract_avito_high_quality_url(self, src):
        """Извлекает URL изображения Avito в максимальном качестве"""
        if not src:
            return None

        if 'avito.st' in src:
            high_quality_url = re.sub(r'_\d+x\d+', '_1280x960', src)
            high_quality_url = re.sub(r'[?&](size|width|height|quality)=\w+', '', high_quality_url)

            if '?' in high_quality_url:
                high_quality_url += '&quality=100'
            else:
                high_quality_url += '?quality=100'

            return high_quality_url

        return src

    def download_image_to_base64(self, image_url, site='avito'):
        """🔥 УЛУЧШЕННОЕ скачивание изображений для Telegram"""
        try:
            session = requests.Session()

            # 🔥 УЛУЧШЕННЫЕ ЗАГОЛОВКИ ДЛЯ ЛУЧШЕГО КАЧЕСТВА
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Referer': 'https://auto.ru/' if site == 'auto.ru' else 'https://www.avito.ru/',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            }

            session.headers.update(headers)

            # 🔥 УВЕЛИЧИВАЕМ ТАЙМАУТ ДЛЯ БОЛЬШИХ ИЗОБРАЖЕНИЙ
            response = session.get(image_url, timeout=45, stream=True)
            response.raise_for_status()

            # 🔥 ПРОВЕРЯЕМ РАЗМЕР ИЗОБРАЖЕНИЯ
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) < 5000:  # Слишком маленькое изображение
                logger.warning(f"⚠️ Изображение слишком маленькое: {content_length} байт")
                # Можно попробовать альтернативный URL или пропустить

            image_base64 = base64.b64encode(response.content).decode('utf-8')

            # 🔥 ОПРЕДЕЛЯЕМ ТИП ИЗОБРАЖЕНИЯ
            content_type = response.headers.get('content-type', '').lower()

            if 'webp' in content_type or image_url.endswith('.webp'):
                mime_type = 'image/webp'
            elif 'jpeg' in content_type or 'jpg' in content_type or image_url.endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif 'png' in content_type or image_url.endswith('.png'):
                mime_type = 'image/png'
            else:
                mime_type = 'image/jpeg'  # fallback

            logger.info(f"✅ Изображение скачано: {len(image_base64)} байт, тип: {mime_type}")
            return f"data:{mime_type};base64,{image_base64}"

        except Exception as e:
            logger.error(f"❌ Ошибка скачивания изображения {image_url}: {e}")
            return None

    def get_image_count(self, site='avito'):
        """Возвращает количество найденных изображений"""
        try:
            images = self.get_images(site)
            return len(images)
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета изображений: {e}")
            return 0

    def validate_image_url(self, image_url, site='avito'):
        """Проверяет валидность URL изображения"""
        try:
            if not image_url:
                return False

            if site == 'auto.ru':
                return 'avatars.mds.yandex.net' in image_url
            else:
                return 'avito.st' in image_url

        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки URL изображения: {e}")
            return False