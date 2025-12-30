import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, NoReturn

import requests

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

    @staticmethod
    def _fetch_and_extract(url: str, session: requests.Session) -> str | None:
        try:
            js_code = session.get(url, timeout=10).text
        except requests.RequestException:
            return None
        return MixinsUtils._extract_version(js_code)

    @staticmethod
    def _extract_version(js_code: str) -> str | None:
        ws_anchor = "wss://ws-api.oneme.ru/websocket"
        pos = js_code.find(ws_anchor)
        if pos == -1:
            return None

        snippet = js_code[pos : pos + 2000]

        match = re.search(r'[:=]\s*"(\d{1,2}\.\d{1,2}\.\d{1,2})"', snippet)
        if match:
            version = match.group(1)
            return version

        return None

    @staticmethod
    def get_current_web_version() -> str | None:
        try:
            html = requests.get("https://web.max.ru/", timeout=10).text
        except requests.RequestException:
            return None

        main_chunk_import = html.split("import(")[2].split(")")[0].strip("\"'")
        main_chunk_url = f"https://web.max.ru{main_chunk_import}"
        try:
            main_chunk_code = requests.get(main_chunk_url, timeout=10).text
        except requests.exceptions.RequestException as e:
            return None

        arr = main_chunk_code.split("\n")[0].split("[")[1].split("]")[0].split(",")
        urls = []
        for i in arr:
            if "/chunks/" in i:
                url = "https://web.max.ru/_app/immutable" + i[3 : len(i) - 1]
                urls.append(url)

        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0"
        if urls:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [
                    pool.submit(MixinsUtils._fetch_and_extract, url, session) for url in urls
                ]
                for f in as_completed(futures):
                    ver = f.result()
                    if ver:
                        return ver
        return None
