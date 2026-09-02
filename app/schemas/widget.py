from datetime import datetime

from pydantic import BaseModel, Field


class WidgetCreate(BaseModel):
    widget_type: str = Field(default="contact", min_length=2, max_length=30)
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    button_text: str = Field(default="Submit", min_length=1, max_length=50)
    fields: list[dict] = Field(default_factory=list)
    display_options: dict = Field(default_factory=dict)


class WidgetUpdate(BaseModel):
    widget_type: str | None = Field(default=None, min_length=2, max_length=30)
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    button_text: str | None = Field(default=None, min_length=1, max_length=50)
    fields: list[dict] | None = None
    display_options: dict | None = None
    is_active: bool | None = None


class WidgetResponse(BaseModel):
    id: int
    public_id: str
    widget_type: str
    title: str
    description: str | None
    button_text: str
    fields: list[dict]
    display_options: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
