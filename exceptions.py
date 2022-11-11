class StatusCodeError(Exception):
    """Исключение статус ответа не равен 200."""

    pass


class HomeworkStatusError(KeyError):
    """Исключение неизвестный статус домашней работы."""

    pass


class HomeworkKeyError(Exception):
    """Исключение при отсутствии ключа homework."""

    pass
