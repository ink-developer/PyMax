from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Auth(SQLModel, table=True):
    token: str | None = None
    device_id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
