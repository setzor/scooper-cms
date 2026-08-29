"""Settings schemas"""

from pydantic import BaseModel
from typing import Optional


class SettingBase(BaseModel):
    key: str
    value: Optional[str] = None


class Setting(SettingBase):
    pass


class SiteSettings(BaseModel):
    site_title: str
    site_description: str
    theme: str
    font_family: str
