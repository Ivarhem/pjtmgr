from pydantic import BaseModel


class TermConfigRead(BaseModel):
    term_key: str
    category: str
    standard_label_en: str
    standard_label_ko: str
    definition: str | None = None
    default_ui_label: str
    custom_ui_label: str | None = None
    ui_label: str
    is_customized: bool
    is_active: bool
    sort_order: int


class TermConfigCreate(BaseModel):
    term_key: str
    category: str
    standard_label_en: str
    standard_label_ko: str
    definition: str | None = None
    default_ui_label: str
    custom_ui_label: str | None = None
    sort_order: int = 0


class TermConfigUpdate(BaseModel):
    category: str | None = None
    standard_label_en: str | None = None
    standard_label_ko: str | None = None
    definition: str | None = None
    default_ui_label: str | None = None
    custom_ui_label: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
