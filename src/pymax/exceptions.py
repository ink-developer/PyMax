class InvalidPhoneError(Exception):
    """
    Исключение, вызываемое при неверном формате номера телефона.

    Args:
        phone (str): Некорректный номер телефона.
    """

    def __init__(self, phone: str) -> None:
        super().__init__(f"Invalid phone number format: {phone}")


class WebSocketNotConnectedError(Exception):
    """
    Исключение, вызываемое при попытке обращения к WebSocket,
    если соединение не установлено.
    """

    def __init__(self) -> None:
        super().__init__("WebSocket is not connected")


class SocketNotConnectedError(Exception):
    """
    Исключение, вызываемое при попытке обращения к сокету,
    если соединение не установлено.
    """

    def __init__(self) -> None:
        super().__init__("Socket is not connected")


class SocketSendError(Exception):
    """
    Исключение, вызываемое при ошибке отправки данных через сокет.
    """

    def __init__(self) -> None:
        super().__init__("Send and wait failed (socket)")


class ResponseError(Exception):
    """
    Исключение, вызываемое при ошибке в ответе от сервера.
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"Response error: {message}")


class ResponseStructureError(Exception):
    """
    Исключение, вызываемое при неверной структуре ответа от сервера.
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"Response structure error: {message}")


class Error(Exception):
    """
    Базовое исключение для ошибок PyMax.
    """

    def __init__(
        self,
        error: str,
        message: str,
        title: str,
        localized_message: str | None = None,
    ) -> None:
        self.error = error
        self.message = message
        self.title = title
        self.localized_message = localized_message

        parts = []
        if localized_message:
            parts.append(localized_message)
        if message:
            parts.append(message)
        if title:
            parts.append(f"({title})")
        parts.append(f"[{error}]")

        super().__init__("PyMax Error: " + " ".join(parts))


class RateLimitError(Error):
    """
    Исключение, вызываемое при превышении лимита запросов.
    """

    def __init__(
        self, error: str, message: str, title: str, localized_message: str | None = None
    ) -> None:
        super().__init__(error, message, title, localized_message)


class LoginError(Error):
    """
    Исключение, вызываемое при ошибке авторизации.
    """

    def __init__(
        self, error: str, message: str, title: str, localized_message: str | None = None
    ) -> None:
        super().__init__(error, message, title, localized_message)
