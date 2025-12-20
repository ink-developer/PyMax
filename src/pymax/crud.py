from typing import cast
from uuid import UUID

from sqlalchemy.engine.base import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from .models import Auth
from .static.enum import DeviceType


class Database:
    def __init__(self, workdir: str) -> None:
        self.workdir = workdir
        self.engine = self.get_engine(workdir)
        self.create_all()
        self._ensure_single_auth()

    def create_all(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def get_engine(self, workdir: str) -> Engine:
        return create_engine(f"sqlite:///{workdir}/session.db")

    def get_session(self) -> Session:
        return Session(bind=self.engine)

    def get_auth_token(self) -> str | None:
        with self.get_session() as session:
            token = cast(str | None, session.exec(select(Auth.token)).first())
            return token

    def get_device_id(self) -> UUID:
        with self.get_session() as session:
            device_id = session.exec(select(Auth.device_id)).first()

            if device_id is None:
                auth = Auth()
                session.add(auth)
                session.commit()
                session.refresh(auth)
                return auth.device_id
            return device_id

    def insert_auth(self, auth: Auth) -> Auth:
        with self.get_session() as session:
            session.add(auth)
            session.commit()
            session.refresh(auth)
            return auth

    def update_auth_token(self, device_id: UUID, token: str) -> None:
        with self.get_session() as session:
            auth = session.exec(select(Auth).where(Auth.device_id == device_id)).first()
            if auth:
                auth.token = token
                session.add(auth)
                session.commit()
                session.refresh(auth)
                return

            existing = session.exec(select(Auth)).first()
            if existing:
                existing.device_id = device_id
                existing.token = token
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return

            new_auth = Auth(device_id=device_id, token=token)
            session.add(new_auth)
            session.commit()
            session.refresh(new_auth)

    def update(self, auth: Auth) -> Auth:
        with self.get_session() as session:
            session.add(auth)
            session.commit()
            session.refresh(auth)
            return auth

    def _ensure_single_auth(self) -> None:
        with self.get_session() as session:
            rows = session.exec(select(Auth)).all()
            if not rows:
                auth = Auth(device_type=DeviceType.WEB.value)
                session.add(auth)
                session.commit()
                session.refresh(auth)
                return

            if len(rows) > 1:
                _ = rows[0]
                for extra in rows[1:]:
                    session.delete(extra)
                session.commit()
