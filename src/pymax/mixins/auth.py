import asyncio
import datetime
import re
import sys
from typing import Any

import qrcode

from pymax.exceptions import Error
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import RegisterPayload, RequestCodePayload, SendCodePayload
from pymax.static.constant import PHONE_REGEX
from pymax.static.enum import AuthType, DeviceType, Opcode


class AuthMixin(ClientProtocol):
    def _check_phone(self) -> bool:
        return bool(re.match(PHONE_REGEX, self.phone))

    async def request_code(self, phone: str, language: str = "ru") -> str:
        """
        Запрашивает код аутентификации для указанного номера телефона и возвращает временный токен.

        Метод отправляет запрос на получение кода верификации на переданный номер телефона.
        Используется в процессе аутентификации или регистрации.

        :param phone: Номер телефона в международном формате.
        :type phone: str
        :param language: Язык для сообщения с кодом. По умолчанию "ru".
        :type language: str
        :return: Временный токен для дальнейшей аутентификации.
        :rtype: str
        :raises ValueError: Если полученные данные имеют неверный формат.
        :raises Error: Если сервер вернул ошибку.

        .. note::
            Используется только в пользовательском flow аутентификации.
        """
        self.logger.info("Requesting auth code")

        payload = RequestCodePayload(
            phone=phone, type=AuthType.START_AUTH, language=language
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.AUTH_REQUEST, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        self.logger.debug(
            "Code request response opcode=%s seq=%s",
            data.get("opcode"),
            data.get("seq"),
        )
        payload_data = data.get("payload")
        if isinstance(payload_data, dict):
            return payload_data["token"]
        else:
            self.logger.error("Invalid payload data received")
            raise ValueError("Invalid payload data received")

    async def resend_code(self, phone: str, language: str = "ru") -> str:
        """
        Повторно запрашивает код аутентификации для указанного номера телефона и возвращает временный токен.

        :param phone: Номер телефона в международном формате.
        :type phone: str
        :param language: Язык для сообщения с кодом. По умолчанию "ru".
        :type language: str
        :return: Временный токен для дальнейшей аутентификации.
        :rtype: str
        :raises ValueError: Если полученные данные имеют неверный формат.
        :raises Error: Если сервер вернул ошибку.
        """
        self.logger.info("Resending auth code")

        payload = RequestCodePayload(
            phone=phone, type=AuthType.RESEND, language=language
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.AUTH_REQUEST, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        self.logger.debug(
            "Code resend response opcode=%s seq=%s",
            data.get("opcode"),
            data.get("seq"),
        )
        payload_data = data.get("payload")
        if isinstance(payload_data, dict):
            return payload_data["token"]
        else:
            self.logger.error("Invalid payload data received")
            raise ValueError("Invalid payload data received")

    async def _send_code(self, code: str, token: str) -> dict[str, Any]:
        """
        Отправляет код верификации на сервер для подтверждения.

        :param code: Код верификации (6 цифр).
        :type code: str
        :param token: Временный токен, полученный из request_code.
        :type token: str
        :return: Словарь с данными ответа сервера, содержащий токены аутентификации.
        :rtype: dict[str, Any]
        :raises Error: Если сервер вернул ошибку.
        """
        self.logger.info("Sending verification code")

        payload = SendCodePayload(
            token=token,
            verify_code=code,
            auth_token_type=AuthType.CHECK_CODE,
        ).model_dump(by_alias=True)

        data = await self._send_and_wait(opcode=Opcode.AUTH, payload=payload)

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        self.logger.debug(
            "Send code response opcode=%s seq=%s",
            data.get("opcode"),
            data.get("seq"),
        )
        payload_data = data.get("payload")
        if isinstance(payload_data, dict):
            return payload_data
        else:
            self.logger.error("Invalid payload data received")
            raise ValueError("Invalid payload data received")

    def _print_qr(self, qr_link: str) -> None:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(qr_link)
        qr.make(fit=True)

        qr.print_ascii()

    async def _request_qr_login(self) -> dict[str, Any]:
        self.logger.info("Requesting QR login data")

        data = await self._send_and_wait(opcode=Opcode.GET_QR, payload={})

        if data.get("payload", {}).get("error"):
            MixinsUtils.handle_error(data)

        self.logger.debug(
            "QR login data response opcode=%s seq=%s",
            data.get("opcode"),
            data.get("seq"),
        )
        payload_data = data.get("payload")
        if isinstance(payload_data, dict):
            return payload_data
        else:
            self.logger.error("Invalid payload data received")
            raise ValueError("Invalid payload data received")

    def _validate_version(self, version: str, min_version: str) -> bool:
        def version_tuple(v: str) -> tuple[int, ...]:
            return tuple(map(int, (v.split("."))))

        return version_tuple(version) >= version_tuple(min_version)

    async def _login(self) -> None:
        self.logger.info("Starting login flow")

        if self.user_agent.device_type == DeviceType.WEB.value and self._ws:
            if not self._validate_version(self.user_agent.app_version, "25.12.13"):
                self.logger.error("Your app version is too old")
                raise ValueError("Your app version is too old")

            login_resp = await self._login_by_qr()
        else:
            temp_token = await self.request_code(self.phone)
            if not temp_token or not isinstance(temp_token, str):
                self.logger.critical("Failed to request code: token missing")
                raise ValueError("Failed to request code")

            print("Введите код: ", end="", flush=True)
            code = await asyncio.to_thread(lambda: sys.stdin.readline().strip())
            if len(code) != 6 or not code.isdigit():
                self.logger.error("Invalid code format entered")
                raise ValueError("Invalid code format")

            login_resp = await self._send_code(code, temp_token)

        token = login_resp.get("tokenAttrs", {}).get("LOGIN", {}).get("token", "")

        if not token:
            self.logger.critical("Failed to login, token not received")
            raise ValueError("Failed to login, token not received")

        self._token = token
        self._database.update_auth_token((self._device_id), self._token)
        self.logger.info("Login successful, token saved to database")

    async def _poll_qr_login(self, track_id: str, poll_interval: int) -> bool:
        self.logger.info("Polling for QR login confirmation")

        while True:
            data = await self._send_and_wait(
                opcode=Opcode.GET_QR_STATUS,
                payload={"trackId": track_id},
            )

            payload = data.get("payload", {})

            if payload.get("error"):
                MixinsUtils.handle_error(data)
            status = payload.get("status")

            if not status:
                self.logger.warning("No status in QR login response")
                continue

            if status.get("loginAvailable"):
                self.logger.info("QR login confirmed")
                return True
            else:
                exp_at = status.get("expiresAt")
                if (
                    exp_at
                    and isinstance(exp_at, (int, float))
                    and exp_at < datetime.datetime.now().timestamp() * 1000
                ):
                    self.logger.warning("QR code expired")
                    return False

            await asyncio.sleep(poll_interval / 1000)

    async def _get_qr_login_data(self, track_id: str) -> dict[str, Any]:
        self.logger.info("Getting QR login data")

        data = await self._send_and_wait(
            opcode=Opcode.LOGIN_BY_QR,
            payload={"trackId": track_id},
        )

        self.logger.debug(
            "QR login data response opcode=%s seq=%s",
            data.get("opcode"),
            data.get("seq"),
        )
        payload_data = data.get("payload")
        if isinstance(payload_data, dict):
            return payload_data
        else:
            self.logger.error("Invalid payload data received")
            raise ValueError("Invalid payload data received")

    async def _login_by_qr(self) -> dict[str, Any]:
        data = await self._request_qr_login()

        poll_interval = data.get("pollingInterval")
        link = data.get("qrLink")
        track_id = data.get("trackId")
        expires_at = data.get("expiresAt")

        if not poll_interval or not link or not track_id or not expires_at:
            self.logger.critical("Invalid QR login data received")
            raise ValueError("Invalid QR login data received")

        self.logger.info("Starting QR login flow")
        self._print_qr(link)

        poll_qr_task = asyncio.create_task(self._poll_qr_login(track_id, poll_interval))

        while True:
            now_ms = datetime.datetime.now().timestamp() * 1000

            done, pending = await asyncio.wait(
                [poll_qr_task],
                timeout=1,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if now_ms >= expires_at:
                poll_qr_task.cancel()
                self.logger.error("QR code expired before confirmation")
                raise RuntimeError("QR code expired before confirmation")

            if poll_qr_task in done:
                exc = poll_qr_task.exception()
                if exc is not None:
                    raise exc
                elif poll_qr_task.result():
                    self.logger.info("QR login successful")

                    data = await self._get_qr_login_data(track_id)
                    return data

                else:
                    self.logger.error("QR login failed or expired")
                    raise RuntimeError("QR login failed or expired")

    async def _submit_reg_info(
        self, first_name: str, last_name: str | None, token: str
    ) -> dict[str, Any]:
        try:
            self.logger.info("Submitting registration info")

            payload = RegisterPayload(
                first_name=first_name,
                last_name=last_name,
                token=token,
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(opcode=Opcode.AUTH_CONFIRM, payload=payload)
            if data.get("payload", {}).get("error"):
                MixinsUtils.handle_error(data)

            self.logger.debug(
                "Registration info response opcode=%s seq=%s",
                data.get("opcode"),
                data.get("seq"),
            )
            payload_data = data.get("payload")
            if isinstance(payload_data, dict):
                return payload_data
            raise ValueError("Invalid payload data received")
        except Exception:
            self.logger.error("Submit registration info failed", exc_info=True)
            raise RuntimeError("Submit registration info failed")

    async def _register(self, first_name: str, last_name: str | None = None) -> None:
        self.logger.info("Starting registration flow")

        request_code_payload = await self.request_code(self.phone)
        temp_token = request_code_payload

        if not temp_token or not isinstance(temp_token, str):
            self.logger.critical("Failed to request code: token missing")
            raise ValueError("Failed to request code")

        print("Введите код: ", end="", flush=True)
        code = await asyncio.to_thread(lambda: sys.stdin.readline().strip())
        if len(code) != 6 or not code.isdigit():
            self.logger.error("Invalid code format entered")
            raise ValueError("Invalid code format")

        registration_response = await self._send_code(code, temp_token)
        token = registration_response.get("tokenAttrs", {}).get("REGISTER", {}).get("token", "")
        if not token:
            self.logger.critical("Failed to register, token not received")
            raise ValueError("Failed to register, token not received")

        data = await self._submit_reg_info(first_name, last_name, token)
        self._token = data.get("token")
        if not self._token:
            self.logger.critical("Failed to register, token not received")
            raise ValueError("Failed to register, token not received")

        self.logger.info("Registration successful")
        self.logger.info("Token: %s", self._token)
        self.logger.warning(
            "IMPORTANT: Use this token ONLY with device_type='DESKTOP' and the special init user agent"
        )
        self.logger.warning("This token MUST NOT be used in web clients")
