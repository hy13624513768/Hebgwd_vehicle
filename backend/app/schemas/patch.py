"""PATCH 中省略与清空是不同操作，只有明确列出的字段允许 null。"""

from typing import ClassVar
from pydantic import BaseModel, ConfigDict, model_validator


class PatchModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nullable_fields: ClassVar[set[str]] = set()

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, values):
        if isinstance(values, dict):
            invalid = [key for key, value in values.items()
                       if key in cls.model_fields and value is None and key not in cls.nullable_fields]
            if invalid:
                raise ValueError("以下字段不能清空：" + ", ".join(invalid))
        return values
