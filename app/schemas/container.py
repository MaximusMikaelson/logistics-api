
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# TYPES
# ============================================================

ContainerType = Literal[
    "20GP",
    "40GP",
    "40HC",
    "20RF",
    "40RF",
]

ContainerStatus = Literal[
    "available",
    "in_transit",
    "maintenance",
]


# ============================================================
# ISO 6346 VALIDATION
# ============================================================

LETTER_VALUES = {
    "A": 10, "B": 12, "C": 13, "D": 14,
    "E": 15, "F": 16, "G": 17, "H": 18,
    "I": 19, "J": 20, "K": 21, "L": 23,
    "M": 24, "N": 25, "O": 26, "P": 27,
    "Q": 28, "R": 29, "S": 30, "T": 31,
    "U": 32, "V": 34, "W": 35, "X": 36,
    "Y": 37, "Z": 38,
}


def calculate_iso6346_check_digit(number: str) -> int:
    """
    Calculate ISO 6346 check digit.

    Expects the first 10 characters:
    4 letters + 6 digits.
    """
    if len(number) != 10:
        raise ValueError(
            "Container number prefix must contain 10 characters"
        )

    total = 0

    for position, char in enumerate(number):
        if char.isdigit():
            value = int(char)
        else:
            value = LETTER_VALUES.get(char)

            if value is None:
                raise ValueError(
                    f"Invalid character: {char}"
                )

        total += value * (2 ** position)

    remainder = total % 11

    return 0 if remainder == 10 else remainder


def validate_iso6346_number(number: str) -> str:
    """
    Validate container number according to ISO 6346.
    """
    if len(number) != 11:
        raise ValueError(
            "Container number must contain exactly 11 characters"
        )

    if not (
        number[:4].isalpha()
        and number[:4].isascii()
        and number[:4].isupper()
        and number[4:].isascii()
        and number[4:].isdigit()
    ):
        raise ValueError(
            "Container number must contain 4 uppercase letters "
            "followed by 7 digits"
        )

    if number[3] not in {"U", "J", "Z"}:
        raise ValueError(
            "Fourth character must be U, J or Z"
        )

    expected_digit = calculate_iso6346_check_digit(
        number[:10]
    )

    actual_digit = int(number[10])

    if actual_digit != expected_digit:
        raise ValueError(
            f"Invalid ISO 6346 check digit: "
            f"expected {expected_digit}, "
            f"got {actual_digit}"
        )

    return number


# ============================================================
# FIELD TYPES
# ============================================================

ContainerNumber = Annotated[
    str,
    Field(
        min_length=11,
        max_length=11,
        pattern=r"^[A-Z]{3}[UJZ][0-9]{7}$",
        description="ISO 6346 container number",
        examples=["MSCU1234566"],
    ),
]

CapacityKg = Annotated[
    int,
    Field(
        gt=0,
        le=100000,
        description="Container payload capacity in kilograms",
    ),
]

PortId = Annotated[
    int,
    Field(gt=0),
]


# ============================================================
# BASE SCHEMA
# ============================================================

class ContainerBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    container_number: ContainerNumber
    container_type: ContainerType
    capacity_kg: CapacityKg
    current_port_id: PortId | None = None
    status: ContainerStatus = "available"

    @field_validator("container_number")
    @classmethod
    def validate_container_number(cls, value: str) -> str:
        return validate_iso6346_number(value)


# ============================================================
# CREATE
# ============================================================

class ContainerCreate(ContainerBase):
    """
    Request schema for creating a container.
    """
    pass


# ============================================================
# FULL UPDATE (PUT)
# ============================================================

class ContainerUpdate(ContainerBase):
    """
    Request schema for replacing container data.
    """
    pass


# ============================================================
# PARTIAL UPDATE (PATCH)
# ============================================================

class ContainerPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    container_number: ContainerNumber | None = None
    container_type: ContainerType | None = None
    capacity_kg: CapacityKg | None = None
    current_port_id: PortId | None = None
    status: ContainerStatus | None = None

    @field_validator("container_number")
    @classmethod
    def validate_container_number(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return validate_iso6346_number(value)

    @model_validator(mode="after")
    def validate_patch(self):
        """
        Reject explicit null for required database columns.
        """
        required_fields = {
            "container_number",
            "container_type",
            "capacity_kg",
            "status",
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

class Container(ContainerBase):
    """
    Response schema representing a stored container.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: int = Field(gt=0)


# ============================================================
# LIST RESPONSE
# ============================================================

class ContainerListResponse(BaseModel):
    containers: list[Container]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
