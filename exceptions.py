class TakeAPIError(Exception):
    """Исключение для проверки запроса к API."""

    pass


class TrueAPIError(Exception):
    """Исключение проверки ответа API на корректность."""

    pass
