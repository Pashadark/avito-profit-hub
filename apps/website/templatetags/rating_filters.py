from django import template

register = template.Library()


@register.filter
def rating_stars(rating):
    """
    Генерирует HTML для звезд рейтинга по формуле:
    full_stars = int(rating) - целая часть
    has_half_star = (rating - full_stars) >= 0.5 - дробная часть >= 0.5
    """
    try:
        rating = float(rating)
        full_stars = int(rating)  # Целая часть
        has_half_star = (rating - full_stars) >= 0.5  # Дробная часть >= 0.5

        stars_html = ''

        # Полные звезды
        for i in range(full_stars):
            stars_html += '<i class="ri-star-fill text-warning" style="font-size: 13px;"></i>'

        # Половинка звезды
        if has_half_star:
            stars_html += '<i class="ri-star-half-line text-warning" style="font-size: 13px;"></i>'
            # Увеличиваем счетчик полных звезд для расчета пустых
            full_stars += 1

        # Пустые звезды (оставшиеся до 5)
        empty_stars = 5 - full_stars
        for i in range(empty_stars):
            stars_html += '<i class="ri-star-line text-warning" style="font-size: 13px;"></i>'

        return stars_html

    except (ValueError, TypeError):
        # Если рейтинг не число - 5 пустых звезд
        return '<i class="ri-star-line text-warning" style="font-size: 13px;"></i>' * 5