from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CargoCategory = Literal[
    "general",
    "perishable",
    "hazardous",
    "oversized",
    "fragile",
]

CustomerId = Annotated[int, Field(gt=0)]
CargoName = Annotated[str, Field(min_length=2, max_length=150)]
Description = Annotated[str, Field(max_length=5000)]

WeightKg = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
]

VolumeM3 = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=3),
]


class CargoBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    customer_id: CustomerId
    name: CargoName
    description: Description | None = None
    weight_kg: WeightKg
    volume_m3: VolumeM3
    category: CargoCategory


class CargoCreate(CargoBase):
    pass


class CargoUpdate(CargoBase):
    pass


class CargoPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    customer_id: CustomerId | None = None
    name: CargoName | None = None
    description: Description | None = None
    weight_kg: WeightKg | None = None
    volume_m3: VolumeM3 | None = None
    category: CargoCategory | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        required_fields = {
            "customer_id",
            "name",
            "weight_kg",
            "volume_m3",
            "category",
        }

        for field in required_fields & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class Cargo(CargoBase):
    id: Annotated[int, Field(gt=0)]
    created_at: datetime


class CargoListResponse(BaseModel):
    cargo: list[Cargo]
    total: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=100)]
    offset: Annotated[int, Field(ge=0)]