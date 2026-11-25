
from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import BaseModel, Field
from psycopg import errors
from psycopg.rows import dict_row

from app.database import get_connection
from app.schemas.ship import Ship, ShipCreate, ShipUpdate


router = APIRouter(
    prefix="/ships",
    tags=["Ships"],
)


# ============================================================
# SCHEMAS
# ============================================================

class ShipPatch(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    imo_number: str | None = Field(
        default=None,
        pattern=r"^\d{7}$",
    )
    capacity_teu: int | None = Field(
        default=None,
        gt=0,
    )
    current_port_id: int | None = None


class ShipListResponse(BaseModel):
    ships: list[Ship]
    total: int
    limit: int
    offset: int


# ============================================================
# HELPERS
# ============================================================

SHIP_COLUMNS = """
    id,
    name,
    imo_number,
    capacity_teu,
    current_port_id
"""


def handle_ship_integrity_error(exc: Exception):
    if isinstance(exc, errors.UniqueViolation):
        raise HTTPException(
            status_code=409,
            detail="Ship with this IMO number already exists",
        ) from exc

    if isinstance(exc, errors.ForeignKeyViolation):
        raise HTTPException(
            status_code=422,
            detail="Current port does not exist",
        ) from exc

    if isinstance(exc, errors.CheckViolation):
        raise HTTPException(
            status_code=422,
            detail="Invalid ship data",
        ) from exc

    if isinstance(exc, errors.NotNullViolation):
        raise HTTPException(
            status_code=422,
            detail="Required ship field cannot be null",
        ) from exc

    raise exc


def get_ship_or_404(cur, ship_id: int):
    cur.execute(
        f"""
        SELECT {SHIP_COLUMNS}
        FROM ships
        WHERE id = %s;
        """,
        (ship_id,),
    )

    ship = cur.fetchone()

    if ship is None:
        raise HTTPException(
            status_code=404,
            detail="Ship not found",
        )

    return ship


# ============================================================
# GET /ships/
# Search, filtering, sorting, pagination
# ============================================================

@router.get(
    "/",
    response_model=ShipListResponse,
)
def get_ships(
    search: Annotated[
        str | None,
        Query(max_length=100),
    ] = None,
    current_port_id: Annotated[
        int | None,
        Query(gt=0),
    ] = None,
    min_capacity: Annotated[
        int | None,
        Query(ge=0),
    ] = None,
    max_capacity: Annotated[
        int | None,
        Query(ge=0),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
):
    if (
        min_capacity is not None
        and max_capacity is not None
        and min_capacity > max_capacity
    ):
        raise HTTPException(
            status_code=422,
            detail="min_capacity cannot exceed max_capacity",
        )

    conditions = []
    params = []

    if search:
        conditions.append("name ILIKE %s")
        params.append(f"%{search}%")

    if current_port_id is not None:
        conditions.append("current_port_id = %s")
        params.append(current_port_id)

    if min_capacity is not None:
        conditions.append("capacity_teu >= %s")
        params.append(min_capacity)

    if max_capacity is not None:
        conditions.append("capacity_teu <= %s")
        params.append(max_capacity)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:

            cur.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM ships
                {where_clause};
                """,
                params,
            )

            total = cur.fetchone()["total"]

            cur.execute(
                f"""
                SELECT {SHIP_COLUMNS}
                FROM ships
                {where_clause}
                ORDER BY id
                LIMIT %s
                OFFSET %s;
                """,
                (*params, limit, offset),
            )

            ships = cur.fetchall()

    return {
        "ships": ships,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# GET /ships/{ship_id}
# ============================================================

@router.get(
    "/{ship_id}",
    response_model=Ship,
)
def get_ship(ship_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            ship = get_ship_or_404(cur, ship_id)

    return ship


# ============================================================
# POST /ships/
# ============================================================

@router.post(
    "/",
    response_model=Ship,
    status_code=status.HTTP_201_CREATED,
)
def create_ship(ship: ShipCreate):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    INSERT INTO ships (
                        name,
                        imo_number,
                        capacity_teu,
                        current_port_id
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING {SHIP_COLUMNS};
                    """,
                    (
                        ship.name,
                        ship.imo_number,
                        ship.capacity_teu,
                        ship.current_port_id,
                    ),
                )

                created_ship = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.ForeignKeyViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_ship_integrity_error(exc)

    return created_ship


# ============================================================
# PUT /ships/{ship_id}
# Full update
# ============================================================

@router.put(
    "/{ship_id}",
    response_model=Ship,
)
def update_ship(
    ship_id: int,
    ship: ShipUpdate,
):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    UPDATE ships
                    SET
                        name = %s,
                        imo_number = %s,
                        capacity_teu = %s,
                        current_port_id = %s
                    WHERE id = %s
                    RETURNING {SHIP_COLUMNS};
                    """,
                    (
                        ship.name,
                        ship.imo_number,
                        ship.capacity_teu,
                        ship.current_port_id,
                        ship_id,
                    ),
                )

                updated_ship = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.ForeignKeyViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_ship_integrity_error(exc)

    if updated_ship is None:
        raise HTTPException(
            status_code=404,
            detail="Ship not found",
        )

    return updated_ship


# ============================================================
# PATCH /ships/{ship_id}
# Partial update
# ============================================================

@router.patch(
    "/{ship_id}",
    response_model=Ship,
)
def patch_ship(
    ship_id: int,
    ship: ShipPatch,
):
    updates = ship.model_dump(exclude_unset=True)

    # Required database columns cannot be NULL.
    for field in (
        "name",
        "imo_number",
        "capacity_teu",
    ):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:

                if not updates:
                    return get_ship_or_404(cur, ship_id)

                # Column names come only from the fixed schema.
                allowed_fields = {
                    "name",
                    "imo_number",
                    "capacity_teu",
                    "current_port_id",
                }

                if not updates.keys() <= allowed_fields:
                    raise HTTPException(
                        status_code=422,
                        detail="Invalid update fields",
                    )

                set_clause = ", ".join(
                    f"{field} = %s"
                    for field in updates
                )

                params = list(updates.values())
                params.append(ship_id)

                cur.execute(
                    f"""
                    UPDATE ships
                    SET {set_clause}
                    WHERE id = %s
                    RETURNING {SHIP_COLUMNS};
                    """,
                    params,
                )

                updated_ship = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.ForeignKeyViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_ship_integrity_error(exc)

    if updated_ship is None:
        raise HTTPException(
            status_code=404,
            detail="Ship not found",
        )

    return updated_ship


# ============================================================
# DELETE /ships/{ship_id}
# ============================================================

@router.delete(
    "/{ship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ship(ship_id: int):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM ships
                    WHERE id = %s
                    RETURNING id;
                    """,
                    (ship_id,),
                )

                deleted_ship = cur.fetchone()

    except errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=409,
            detail="Ship is referenced by other records",
        ) from exc

    if deleted_ship is None:
        raise HTTPException(
            status_code=404,
            detail="Ship not found",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
