import random
import logging

# ✅ Создаем логгер для этого модуля
logger = logging.getLogger('parser.user_agents')

# 🔥 ОБНОВЛЕННЫЙ СПИСОК USER AGENTS (ТОЛЬКО DESKTOP)
USER_AGENTS = [
    # Chrome - Desktop (обновленные версии)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

    # Firefox - Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux i686; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",

    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",

    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",

    # 🔥 RARE BROWSERS (для большего разнообразия)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5.3206.53",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5.3206.53",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/23.11.0.2403 Yowser/2.5 Safari/537.36",

    # 🔥 LINUX VARIANTS
    "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; OpenBSD amd64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

    # 🔥 ДОПОЛНИТЕЛЬНЫЕ DESKTOP USER AGENTS
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def get_browser_emoji(browser):
    """Возвращает эмодзи для браузера"""
    emoji_map = {
        'Chrome': '🌐',
        'Firefox': '🦊',
        'Safari': '🍎',
        'Edge': '🔵',
        'Opera': '🎭',
        'Vivaldi': '🎵',
        'Yandex': '🔶',
        'Other': '💻'
    }
    return emoji_map.get(browser, '💻')


def get_device_emoji(device):
    """Возвращает эмодзи для устройства"""
    emoji_map = {
        'Desktop': '🖥️',
        'Mobile': '📱',
        'Tablet': '📱'
    }
    return emoji_map.get(device, '💻')


def get_os_emoji(os):
    """Возвращает эмодзи для операционной системы"""
    emoji_map = {
        'Windows': '🪟',
        'Mac OS': '🍎',
        'Linux': '🐧',
        'Android': '🤖',
        'iOS': '📱',
        'Unknown': '💻'
    }
    return emoji_map.get(os, '💻')


def get_random_user_agent():
    """Возвращает случайный User-Agent из списка"""
    user_agent = random.choice(USER_AGENTS)
    parsed_info = parse_user_agent(user_agent)

    browser_emoji = get_browser_emoji(parsed_info['browser'])
    device_emoji = get_device_emoji(parsed_info['device'])
    os_emoji = get_os_emoji(parsed_info['os'])

    logger.debug(
        f"🎲 Случайный User-Agent: {browser_emoji} {parsed_info['browser']} на {device_emoji} {parsed_info['device']} ({os_emoji} {parsed_info['os']})")
    return user_agent


def get_weighted_user_agent():
    """
    Возвращает User-Agent с весами (чаще популярные браузеры)
    Chrome - 50%, Firefox - 20%, Safari - 10%, Others - 20%
    """
    try:
        # 🔥 ТОЧНОЕ КОЛИЧЕСТВО ВЕСОВ: 22 для 22 User-Agent
        weights = [
            # Chrome - Desktop (9)
            5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0,
            # Firefox - Desktop (4)
            2.0, 2.0, 2.0, 2.0,
            # Safari (1)
            1.0,
            # Edge (2)
            2.0, 2.0,
            # Opera (2)
            1.0, 1.0,
            # Rare Browsers (3)
            1.0, 1.0, 1.0,
            # Linux Variants (3)
            1.0, 1.0, 1.0
        ]

        # 🔥 ПРОВЕРКА И АВТОИСПРАВЛЕНИЕ
        if len(weights) != len(USER_AGENTS):
            logger.warning(
                f"⚠️ Количество весов ({len(weights)}) не совпадает с User-Agent ({len(USER_AGENTS)}). Автоисправление...")
            # Автоматически корректируем количество весов
            if len(weights) < len(USER_AGENTS):
                # Добавляем недостающие веса
                weights.extend([1.0] * (len(USER_AGENTS) - len(weights)))
            else:
                # Убираем лишние веса
                weights = weights[:len(USER_AGENTS)]

        # Нормализуем веса
        total = sum(weights)
        normalized_weights = [w / total for w in weights]

        user_agent = random.choices(USER_AGENTS, weights=normalized_weights)[0]
        parsed_info = parse_user_agent(user_agent)

        browser_emoji = get_browser_emoji(parsed_info['browser'])
        device_emoji = get_device_emoji(parsed_info['device'])

        logger.debug(
            f"⚖️  User-Agent с весами: {browser_emoji} {parsed_info['browser']} на {device_emoji} {parsed_info['device']}")
        return user_agent

    except Exception as e:
        logger.error(f"❌ Ошибка в get_weighted_user_agent: {e}")
        # Фолбэк на случайный выбор
        return get_random_user_agent()


def parse_user_agent(user_agent_string):
    """
    Парсит User-Agent и возвращает информацию о браузере и устройстве
    """
    ua = user_agent_string.lower()

    # Определяем браузер
    if 'chrome' in ua and 'edge' not in ua and 'opr' not in ua and 'vivaldi' not in ua:
        browser = 'Chrome'
    elif 'firefox' in ua:
        browser = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        browser = 'Safari'
    elif 'edge' in ua:
        browser = 'Edge'
    elif 'opr' in ua:
        browser = 'Opera'
    elif 'vivaldi' in ua:
        browser = 'Vivaldi'
    elif 'yabrowser' in ua:
        browser = 'Yandex'
    else:
        browser = 'Other'

    # Определяем устройство (ТОЛЬКО DESKTOP)
    device = 'Desktop'

    # Определяем ОС
    if 'windows' in ua:
        os = 'Windows'
    elif 'mac' in ua:
        os = 'Mac OS'
    elif 'linux' in ua:
        os = 'Linux'
    elif 'android' in ua:
        os = 'Android'
    elif 'ios' in ua or 'iphone' in ua or 'ipad' in ua:
        os = 'iOS'
    else:
        os = 'Unknown'

    return {
        'browser': browser,
        'device': device,
        'os': os,
        'is_mobile': False,  # Всегда False для desktop-only
        'is_desktop': True,  # Всегда True для desktop-only
        'original': user_agent_string
    }


def get_user_agent_stats():
    """Статистика по доступным User-Agents"""
    stats = {}
    for ua in USER_AGENTS:
        parsed = parse_user_agent(ua)
        browser = parsed['browser']
        device = parsed['device']

        if browser not in stats:
            stats[browser] = {}
        if device not in stats[browser]:
            stats[browser][device] = 0
        stats[browser][device] += 1

    return stats


def debug_user_agents_count():
    """Автоматическая проверка количества User-Agent и весов"""
    actual_count = len(USER_AGENTS)
    logger.info(f"🔍 ОТЛАДКА: Всего User-Agent: {actual_count}")

    # Статистика по типам
    stats = {}
    for i, ua in enumerate(USER_AGENTS):
        parsed = parse_user_agent(ua)
        browser = parsed['browser']
        device = parsed['device']
        key = f"{browser} {device}"

        if key not in stats:
            stats[key] = 0
        stats[key] += 1

        browser_emoji = get_browser_emoji(browser)
        device_emoji = get_device_emoji(device)
        os_emoji = get_os_emoji(parsed['os'])

        logger.debug(
            f"   {i + 1:2d}. {browser_emoji} {browser:8} {device_emoji} {device:8} - {os_emoji} {parsed['os']}")

    logger.info("📊 СТАТИСТИКА User-Agent:")
    for browser_device, count in stats.items():
        logger.info(f"   {browser_device}: {count}")

    return actual_count


# 🔥 ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПАРСЕРА

def rotate_user_agent_smartly(last_used=None):
    """
    Умная ротация User-Agent:
    - Меняет браузеры
    - Избегает повторений
    """
    if not last_used:
        user_agent = get_weighted_user_agent()
        parsed_info = parse_user_agent(user_agent)

        browser_emoji = get_browser_emoji(parsed_info['browser'])
        device_emoji = get_device_emoji(parsed_info['device'])

        logger.info(
            f"🔄 Первый User-Agent: {browser_emoji} {parsed_info['browser']} на {device_emoji} {parsed_info['device']}")
        return user_agent

    # Парсим последний использованный UA
    last_parsed = parse_user_agent(last_used)
    last_browser_emoji = get_browser_emoji(last_parsed['browser'])
    last_device_emoji = get_device_emoji(last_parsed['device'])

    # Пробуем найти UA с другим браузером
    for ua in USER_AGENTS:
        parsed = parse_user_agent(ua)
        if parsed['browser'] != last_parsed['browser']:
            new_browser_emoji = get_browser_emoji(parsed['browser'])
            new_device_emoji = get_device_emoji(parsed['device'])

            logger.info(
                f"🔄 Смена User-Agent: {last_browser_emoji}{last_parsed['browser']}→{new_browser_emoji}{parsed['browser']} на {last_device_emoji}{last_parsed['device']}→{new_device_emoji}{parsed['device']}")
            return ua

    # Если не нашли, возвращаем случайный
    user_agent = get_random_user_agent()
    parsed_info = parse_user_agent(user_agent)

    browser_emoji = get_browser_emoji(parsed_info['browser'])
    device_emoji = get_device_emoji(parsed_info['device'])

    logger.info(
        f"🔄 Случайная смена User-Agent: {browser_emoji} {parsed_info['browser']} на {device_emoji} {parsed_info['device']}")
    return user_agent


def apply_user_agent_to_driver(driver, window_id=None):
    """
    Применяет случайный User-Agent к драйверу Selenium
    """
    try:
        user_agent = get_weighted_user_agent()
        parsed_info = parse_user_agent(user_agent)

        # Применяем User-Agent через CDP
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            'userAgent': user_agent
        })

        browser_emoji = get_browser_emoji(parsed_info['browser'])
        device_emoji = get_device_emoji(parsed_info['device'])
        os_emoji = get_os_emoji(parsed_info['os'])

        if window_id is not None:
            logger.info(
                f"🖥️ Окно {window_id} | User-Agent: {browser_emoji} {parsed_info['browser']} на {device_emoji} {parsed_info['device']} ({os_emoji} {parsed_info['os']})")
        else:
            logger.info(
                f"🌐 User-Agent установлен: {browser_emoji} {parsed_info['browser']} на {device_emoji} {parsed_info['device']}")

        return user_agent

    except Exception as e:
        logger.error(f"❌ Ошибка установки User-Agent: {e}")
        return None


# 🔥 Функция для использования в парсере
def get_smart_user_agent_for_parser(window_id, last_user_agent=None):
    """
    Умный выбор User-Agent для парсера с детальным логированием
    """
    user_agent = rotate_user_agent_smartly(last_user_agent)
    parsed_info = parse_user_agent(user_agent)

    browser_emoji = get_browser_emoji(parsed_info['browser'])
    device_emoji = get_device_emoji(parsed_info['device'])
    os_emoji = get_os_emoji(parsed_info['os'])

    logger.info(
        f"🖥️ Окно {window_id} | 🔄 User-Agent: {browser_emoji} {parsed_info['browser']} {device_emoji} {parsed_info['device']} ({os_emoji} {parsed_info['os']})")

    return user_agent


# Пример использования (для тестирования)
if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%H:%M:%S'
    )

    logger.info("📊 User Agents Statistics:")
    stats = get_user_agent_stats()
    for browser, devices in stats.items():
        browser_emoji = get_browser_emoji(browser)
        logger.info(f"  {browser_emoji} {browser}: {devices}")

    logger.info(f"🎯 Всего User Agents: {len(USER_AGENTS)}")
    logger.info(f"📱 Мобильные устройства: {sum(1 for ua in USER_AGENTS if parse_user_agent(ua)['is_mobile'])}")
    logger.info(f"💻 Десктопные устройства: {sum(1 for ua in USER_AGENTS if parse_user_agent(ua)['is_desktop'])}")

    # Отладочная информация
    debug_user_agents_count()

    # Тестируем ротацию
    logger.info("\n🔄 Тест ротации User-Agents:")
    last_ua = None
    for i in range(5):
        last_ua = get_smart_user_agent_for_parser(f"test_{i}", last_ua)