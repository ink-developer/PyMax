from typing import Any, NoReturn

from pymax.exceptions import Error, RateLimitError


class MixinsUtils:
    @staticmethod
    def handle_error(data: dict[str, Any]) -> NoReturn:
        error = data.get("payload", {}).get("error")
        localized_message = data.get("payload", {}).get("localizedMessage")
        title = data.get("payload", {}).get("title")
        message = data.get("payload", {}).get("message")

        if error == "too.many.requests":  # TODO: вынести в статик
            raise RateLimitError(
                error=error,
                message=message,
                title=title,
                localized_message=localized_message,
            )

        raise Error(
            error=error,
            message=message,
            title=title,
            localized_message=localized_message,
        )
