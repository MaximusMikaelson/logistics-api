from pydantic import BaseModel, Field


class ShipCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    imo_number: str = Field(pattern=r"^\d{7}$")
    capacity_teu: int = Field(gt=0)
    current_port_id: int | None = None

class Ship(BaseModel):
    id: int
    name: str
    imo_number: str
    capacity_teu: int
    current_port_id: int | None

class ShipUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    imo_number: str = Field(pattern=r"^\d{7}$")
    capacity_teu: int = Field(gt=0)
    current_port_id: int | None = None