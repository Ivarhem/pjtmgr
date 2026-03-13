from pydantic import BaseModel


class SettingsRead(BaseModel):
    org_name: str | None = None


class SettingsUpdate(BaseModel):
    org_name: str | None = None
