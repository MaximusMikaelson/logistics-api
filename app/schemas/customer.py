
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


CompanyName = Annotated[
    str, Field(min_length=2, max_length=150)
]

Country = Annotated[
    str, Field(min_length=2, max_length=100)
]

ContactName = Annotated[
    str, Field(min_length=2, max_length=100)
]

Email = Annotated[
    str,
    Field(
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]

Phone = Annotated[
    str,
    Field(
        min_length=5,
        max_length=30,
        pattern=r"^\+?[0-9 ()-]+$",
    ),
]


# ============================================================
# BASE SCHEMA
# ============================================================

class CustomerBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    company_name: CompanyName
    country: Country
    contact_name: ContactName | None = None
    email: Email
    phone: Phone | None = None
    is_active: bool = True


# ============================================================
# CREATE
# ============================================================

class CustomerCreate(CustomerBase):
    pass


# ============================================================
# FULL UPDATE
# ============================================================

class CustomerUpdate(CustomerBase):
    pass


# ============================================================
# PARTIAL UPDATE
# ============================================================

class CustomerPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    company_name: CompanyName | None = None
    country: Country | None = None
    contact_name: ContactName | None = None
    email: Email | None = None
    phone: Phone | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        required_fields = {
            "company_name",
            "country",
            "email",
            "is_active",
        }

        for field in required_fields:
            if (
                field in self.model_fields_set
                and getattr(self, field) is None
            ):
                raise ValueError(
                    f"{field} cannot be null"
                )

        return self


# ============================================================
# RESPONSE
# ============================================================

class Customer(CustomerBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int = Field(gt=0)
    created_at: datetime


# ============================================================
# LIST RESPONSE
# ============================================================

class CustomerListResponse(BaseModel):
    customers: list[Customer]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
