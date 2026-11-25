from pydantic import BaseModel, Field, field_validator


class Port(BaseModel):
    id: int
    name: str
    country: str

class PortCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=2, max_length=100)

    @field_validator("name", "country", mode="before")
    @classmethod
    def clean_name(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value


class PortUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=2, max_length=100)

    @field_validator("name", "country", mode="before")
    @classmethod
    def clean_name(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value
