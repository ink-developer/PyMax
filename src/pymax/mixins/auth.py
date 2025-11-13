import asyncio
import re
import sys
from typing import Any

from pymax.exceptions import Error
from pymax.interfaces import ClientProtocol
from pymax.mixins.utils import MixinsUtils
from pymax.payloads import RegisterPayload, RequestCodePayload, SendCodePayload
from pymax.static.constant import PHONE_REGEX
from pymax.static.enum import AuthType, Opcode


class AuthMixin(ClientProtocol):
    def _check_phone(self) -> bool:
        return bool(re.match(PHONE_REGEX, self.phone))

    async def _request_code(
        self, phone: str, language: str = "ru"
    ) -> dict[str, int | str]:
        try:
            self.logger.info("Requesting auth code")

            payload = RequestCodePayload(
                phone=phone, type=AuthType.START_AUTH, language=language
            ).model_dump(by_alias=True)

            data = await self._send_and_wait(
                opcode=Opcode.AUTH_REQUEST, payload=payload
            )
            if data.get("payload", {}).get("error"):
                MixinsUtils.handle_error(data)

            self.logger.debug(
                "Code request response opcode=%s seq=%s",
                data.get("opcode"),
                data.get("seq"),
            )
            payload_data = data.get("payload")
            if isinstance(payload_data, dict):
                return payload_data
            else:
                self.logger.error("Invalid payload data received")
                raise ValueError("Invalid payload data received")
        except Exception:
            self.logger.error("Request code failed", exc_info=True)
            raise RuntimeError("Request code failed")

    async def _send_code(self, code: str, token: str) -> dict[str, Any]:
        try:
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
        except Exception:
            self.logger.error("Send code failed", exc_info=True)
            raise RuntimeError("Send code failed")

    async def _login(self) -> None:
        self.logger.info("Starting login flow")

        request_code_payload = await self._request_code(self.phone)
        temp_token = request_code_payload.get("token")
        if not temp_token or not isinstance(temp_token, str):
            self.logger.critical("Failed to request code: token missing")
            raise ValueError("Failed to request code")

        print("Введите код: ", end="", flush=True)
        code = await asyncio.to_thread(lambda: sys.stdin.readline().strip())
        if len(code) != 6 or not code.isdigit():
            self.logger.error("Invalid code format entered")
            raise ValueError("Invalid code format")

        login_resp = await self._send_code(code, temp_token)
        token: str | None = (
            login_resp.get("tokenAttrs", {}).get("LOGIN", {}).get("token")
        )
        if not token:
            self.logger.critical("Failed to login, token not received")
            raise ValueError("Failed to login, token not received")

        self._token = token
        self._database.update_auth_token(self._device_id, self._token)
        self.logger.info("Login successful, token saved to database")

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

            data = await self._send_and_wait(
                opcode=Opcode.AUTH_CONFIRM, payload=payload
            )
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

        request_code_payload = await self._request_code(self.phone)
        temp_token = request_code_payload.get("token")

        if not temp_token or not isinstance(temp_token, str):
            self.logger.critical("Failed to request code: token missing")
            raise ValueError("Failed to request code")

        print("Введите код: ", end="", flush=True)
        code = await asyncio.to_thread(lambda: sys.stdin.readline().strip())
        if len(code) != 6 or not code.isdigit():
            self.logger.error("Invalid code format entered")
            raise ValueError("Invalid code format")

        registration_response = await self._send_code(code, temp_token)
        token: str | None = (
            registration_response.get("tokenAttrs", {}).get("REGISTER", {}).get("token")
        )
        if not token:
            self.logger.critical("Failed to register, token not received")
            raise ValueError("Failed to register, token not received")

        data = await self._submit_reg_info(first_name, last_name, token)
        self._token = data.get("token")
        if not self._token:
            self.logger.critical("Failed to register, token not received")
            raise ValueError("Failed to register, token not received")

        self._database.update_auth_token(self._device_id, self._token)
        self.logger.info("Registration successful, token saved to database")
