
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from psycopg import errors, sql
from psycopg.rows import dict_row

from app.database import get_connection
from app.schemas.cargo import (
    Cargo,
    CargoCategory,
    CargoCreate,
    CargoListResponse,
    CargoPatch,
    CargoUpdate,
)


router = APIRouter(
    prefix="/cargo",
    tags=["Cargo"],
)

CargoId = Annotated[int, Path(gt=0)]

CARGO_COLUMNS = """
    id,
    customer_id,
    name,
    description,
    weight_kg,
    volume_m3,
    category,
    created_at
"""

ALLOWED_UPDATE_FIELDS = {
    "customer_id",
    "name",
    "description",
    "weight_kg",
    "volume_m3",
    "category",
}


def validate_customer(cursor, customer_id: int):
    cursor.execute(
        """
        SELECT id, is_active
        FROM customers
        WHERE id = %s
        FOR SHARE
        """,
        (customer_id,),
    )

    customer = cursor.fetchone()

    if customer is None:
        raise HTTPException(
            status_code=422,
            detail="Customer does not exist",
        )

    if not customer["is_active"]:
        raise HTTPException(
            status_code=409,
            detail="Customer is inactive",
        )


def get_cargo_or_404(cursor, cargo_id: int, lock=False):
    query = f"""
        SELECT {CARGO_COLUMNS}
        FROM cargo
        WHERE id = %s
    """

    if lock:
        query += " FOR UPDATE"

    cursor.execute(query, (cargo_id,))
    cargo = cursor.fetchone()

    if cargo is None:
        raise HTTPException(
            status_code=404,
            detail="Cargo not found",
        )

    return cargo


@router.get("/", response_model=CargoListResponse)
def get_cargo_list(
    search: Annotated[str | None, Query(max_length=150)] = None,
    customer_id: Annotated[int | None, Query(gt=0)] = None,
    category: CargoCategory | None = None,
    min_weight: Annotated[Decimal | None, Query(gt=0)] = None,
    max_weight: Annotated[Decimal | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if (
        min_weight is not None
        and max_weight is not None
        and min_weight > max_weight
    ):
        raise HTTPException(
            status_code=422,
            detail="min_weight cannot exceed max_weight",
        )

    conditions = []
    params = []

    if search:
        conditions.append(
            "(name ILIKE %s OR description ILIKE %s)"
        )
        pattern = f"%{search}%"
        params.extend([pattern, pattern])

    if customer_id is not None:
        conditions.append("customer_id = %s")
        params.append(customer_id)

    if category is not None:
        conditions.append("category = %s")
        params.append(category)

    if min_weight is not None:
        conditions.append("weight_kg >= %s")
        params.append(min_weight)

    if max_weight is not None:
        conditions.append("weight_kg <= %s")
        params.append(max_weight)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM cargo
                {where_clause}
                """,
                params,
            )

            total = cursor.fetchone()["total"]

            cursor.execute(
                f"""
                SELECT {CARGO_COLUMNS}
                FROM cargo
                {where_clause}
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )

            cargo = cursor.fetchall()

    return {
        "cargo": cargo,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{cargo_id}", response_model=Cargo)
def get_cargo(cargo_id: CargoId):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            return get_cargo_or_404(cursor, cargo_id)


@router.post("/", response_model=Cargo, status_code=201)
def create_cargo(cargo: CargoCreate):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                validate_customer(cursor, cargo.customer_id)

                cursor.execute(
                    f"""
                    INSERT INTO cargo (
                        customer_id,
                        name,
                        description,
                        weight_kg,
                        volume_m3,
                        category
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING {CARGO_COLUMNS}
                    """,
                    (
                        cargo.customer_id,
                        cargo.name,
                        cargo.description,
                        cargo.weight_kg,
                        cargo.volume_m3,
                        cargo.category,
                    ),
                )

                return cursor.fetchone()

    except errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=422,
            detail="Invalid customer ID",
        )

    except (
        errors.CheckViolation,
        errors.NotNullViolation,
        errors.NumericValueOutOfRange,
    ):
        raise HTTPException(
            status_code=422,
            detail="Invalid cargo data",
        )


@router.put("/{cargo_id}", response_model=Cargo)
def update_cargo(cargo_id: CargoId, cargo: CargoUpdate):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                get_cargo_or_404(cursor, cargo_id, lock=True)
                validate_customer(cursor, cargo.customer_id)

                cursor.execute(
                    f"""
                    UPDATE cargo
                    SET
                        customer_id = %s,
                        name = %s,
                        description = %s,
                        weight_kg = %s,
                        volume_m3 = %s,
                        category = %s
                    WHERE id = %s
                    RETURNING {CARGO_COLUMNS}
                    """,
                    (
                        cargo.customer_id,
                        cargo.name,
                        cargo.description,
                        cargo.weight_kg,
                        cargo.volume_m3,
                        cargo.category,
                        cargo_id,
                    ),
                )

                return cursor.fetchone()

    except errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=422,
            detail="Invalid customer ID",
        )

    except (
        errors.CheckViolation,
        errors.NotNullViolation,
        errors.NumericValueOutOfRange,
    ):
        raise HTTPException(
            status_code=422,
            detail="Invalid cargo data",
        )


@router.patch("/{cargo_id}", response_model=Cargo)
def patch_cargo(cargo_id: CargoId, cargo: CargoPatch):
    updates = cargo.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=422,
            detail="No fields provided for update",
        )

    if not set(updates).issubset(ALLOWED_UPDATE_FIELDS):
        raise HTTPException(
            status_code=422,
            detail="Invalid update fields",
        )

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                current = get_cargo_or_404(
                    cursor,
                    cargo_id,
                    lock=True,
                )

                customer_id = updates.get(
                    "customer_id",
                    current["customer_id"],
                )

                validate_customer(cursor, customer_id)

                assignments = sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(
                        sql.Identifier(field)
                    )
                    for field in updates
                )

                query = sql.SQL(
                    """
                    UPDATE cargo
                    SET {}
                    WHERE id = %s
                    RETURNING {}
                    """
                ).format(
                    assignments,
                    sql.SQL(CARGO_COLUMNS),
                )

                cursor.execute(
                    query,
                    [*updates.values(), cargo_id],
                )

                return cursor.fetchone()

    except errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=422,
            detail="Invalid customer ID",
        )

    except (
        errors.CheckViolation,
        errors.NotNullViolation,
        errors.NumericValueOutOfRange,
    ):
        raise HTTPException(
            status_code=422,
            detail="Invalid cargo data",
        )


@router.delete("/{cargo_id}", status_code=204)
def delete_cargo(cargo_id: CargoId):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                get_cargo_or_404(cursor, cargo_id, lock=True)

                cursor.execute(
                    "DELETE FROM cargo WHERE id = %s",
                    (cargo_id,),
                )

    except errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=409,
            detail="Cargo is referenced by other records",
        )
