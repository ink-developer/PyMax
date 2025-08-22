from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Auth(SQLModel, table=True):
    token: str | None = None
    device_id: UUID = Field(default_factory=uuid4, primary_key=True)
