# Nombres de TypeProduct.name considerados alimentación para cronogramas (sin mayúsculas).
FEED_SCHEDULE_PRODUCT_TYPE_NAMES = ("alimento", "feed", "food", "alimentacion", "alimentación")

# Jornada laboral en campo para distribuir raciones (primera a la hora de inicio, las
# siguientes cada `gap_between_times_per_day` minutos; la última no debe pasar del fin).
FEEDING_WORKDAY_START_HOUR = 6
FEEDING_WORKDAY_END_HOUR = 18


def feeding_work_window_minutes() -> int:
    return (FEEDING_WORKDAY_END_HOUR - FEEDING_WORKDAY_START_HOUR) * 60
