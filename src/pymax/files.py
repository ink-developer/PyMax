import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from aiofiles import open as aio_open
from aiohttp import ClientSession
from typing_extensions import override


class BaseFile(ABC):
    def __init__(self, url: str | None = None, path: str | None = None) -> None:
        self.url = url
        self.path = path

        if self.url is None and self.path is None:
            raise ValueError("Either url or path must be provided.")

        if self.url and self.path:
            raise ValueError("Only one of url or path must be provided.")

    @abstractmethod
    async def read(self) -> bytes:
        if self.url:
            async with (
                ClientSession() as session,
                session.get(self.url) as response,
            ):
                response.raise_for_status()
                return await response.read()
        elif self.path:
            async with aio_open(self.path, "rb") as f:
                return await f.read()
        else:
            raise ValueError("Either url or path must be provided.")


class Photo(BaseFile):
    ALLOWED_EXTENSIONS: ClassVar[set[str]] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
    }  # FIXME: костыль ✅

    def __init__(self, url: str | None = None, path: str | None = None) -> None:
        if path:
            self.file_name = Path(path).name
        elif url:
            self.file_name = Path(url).name

        super().__init__(url, path)

    def validate_photo(self) -> tuple[str, str] | None:
        if self.path:
            extension = Path(self.path).suffix.lower()
            if extension not in self.ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Invalid photo extension: {extension}. Allowed: {self.ALLOWED_EXTENSIONS}"
                )

            return (extension[1:], ("image/" + extension[1:]).lower())
        elif self.url:
            extension = Path(self.url).suffix.lower()
            if extension not in self.ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Invalid photo extension in URL: {extension}. Allowed: {self.ALLOWED_EXTENSIONS}"
                )

            mime_type = mimetypes.guess_type(self.url)[0]

            if not mime_type or not mime_type.startswith("image/"):
                raise ValueError(f"URL does not appear to be an image: {self.url}")

            return (extension[1:], mime_type)
        return None

    @override
    async def read(self) -> bytes:
        return await super().read()


class Video(BaseFile):
    def __init__(self, url: str | None = None, path: str | None = None) -> None:
        self.file_name: str = ""
        if path:
            self.file_name = Path(path).name
        elif url:
            self.file_name = Path(url).name

        if not self.file_name:
            raise ValueError("Either url or path must be provided.")
        super().__init__(url, path)

    @override
    async def read(self) -> bytes:
        return await super().read()


class File(BaseFile):
    def __init__(self, url: str | None = None, path: str | None = None) -> None:
        self.file_name: str = ""
        if path:
            self.file_name = Path(path).name
        elif url:
            self.file_name = Path(url).name

        if not self.file_name:
            raise ValueError("Either url or path must be provided.")

        super().__init__(url, path)

    @override
    async def read(self) -> bytes:
        return await super().read()
