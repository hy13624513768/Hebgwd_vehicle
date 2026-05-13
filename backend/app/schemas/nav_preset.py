from pydantic import BaseModel, Field


class NavPresetMarker(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    lng: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    locked: bool = True


class NavPresetListOut(BaseModel):
    markers: list[NavPresetMarker]


class NavPresetReplaceIn(BaseModel):
    markers: list[NavPresetMarker] = Field(min_length=1)
