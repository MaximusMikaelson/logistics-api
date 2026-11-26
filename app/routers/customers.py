
from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from psycopg import errors
from psycopg.rows import dict_row

from app.database import get_connection
from app.schemas.customer import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
    CustomerPatch,
    CustomerListResponse,
)


router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


# ============================================================
# CONSTANTS
# ============================================================

CUSTOMER_COLUMNS = """
    id,
    company_name,
    country,
    contact_name,
    email,
    phone,
    is_active,
    created_at
"""

ALLOWED_UPDATE_FIELDS = {
    "company_name",
    "country",
    "contact_name",
    "email",
    "phone",
    "is_active",
}

CustomerId = Annotated[int, Path(gt=0)]


# ============================================================
# HELPERS
# ============================================================

def get_customer_or_404(cur, customer_id: int):
    cur.execute(
        f"""
        SELECT {CUSTOMER_COLUMNS}
        FROM customers
        WHERE id = %s;
        """,
        (customer_id,),
    )

    customer = cur.fetchone()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


def handle_customer_integrity_error(exc):
    if isinstance(exc, errors.UniqueViolation):
        raise HTTPException(
            status_code=409,
            detail="Customer email already exists",
        ) from exc

    if isinstance(
        exc,
        (errors.CheckViolation, errors.NotNullViolation),
    ):
        raise HTTPException(
            status_code=422,
            detail="Customer violates database constraints",
        ) from exc

    raise exc


# ============================================================
# GET /customers/
# ============================================================

@router.get(
    "/",
    response_model=CustomerListResponse,
)
def get_customers(
    search: Annotated[
        str | None,
        Query(max_length=150),
    ] = None,
    country: Annotated[
        str | None,
        Query(max_length=100),
    ] = None,
    is_active: bool | None = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
):
    conditions = []
    params = []

    if search:
        conditions.append(
            """
            (
                company_name ILIKE %s
                OR contact_name ILIKE %s
                OR email ILIKE %s
            )
            """
        )

        pattern = f"%{search}%"

        params.extend(
            [pattern, pattern, pattern]
        )

    if country is not None:
        conditions.append("country ILIKE %s")
        params.append(country)

    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(is_active)

    where_clause = ""

    if conditions:
        where_clause = (
            "WHERE " + " AND ".join(conditions)
        )

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM customers
                {where_clause};
                """,
                params,
            )

            total = cur.fetchone()["total"]

            cur.execute(
                f"""
                SELECT {CUSTOMER_COLUMNS}
                FROM customers
                {where_clause}
                ORDER BY id
                LIMIT %s OFFSET %s;
                """,
                (*params, limit, offset),
            )

            customers = cur.fetchall()

    return {
        "customers": customers,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# GET /customers/{customer_id}
# ============================================================

@router.get(
    "/{customer_id}",
    response_model=Customer,
)
def get_customer(customer_id: CustomerId):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return get_customer_or_404(
                cur, customer_id
            )


# ============================================================
# POST /customers/
# ============================================================

@router.post(
    "/",
    response_model=Customer,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(customer: CustomerCreate):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    INSERT INTO customers (
                        company_name,
                        country,
                        contact_name,
                        email,
                        phone,
                        is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING {CUSTOMER_COLUMNS};
                    """,
                    (
                        customer.company_name,
                        customer.country,
                        customer.contact_name,
                        customer.email,
                        customer.phone,
                        customer.is_active,
                    ),
                )

                created = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_customer_integrity_error(exc)

    return created


# ============================================================
# PUT /customers/{customer_id}
# ============================================================

@router.put(
    "/{customer_id}",
    response_model=Customer,
)
def update_customer(
    customer_id: CustomerId,
    customer: CustomerUpdate,
):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    UPDATE customers
                    SET
                        company_name = %s,
                        country = %s,
                        contact_name = %s,
                        email = %s,
                        phone = %s,
                        is_active = %s
                    WHERE id = %s
                    RETURNING {CUSTOMER_COLUMNS};
                    """,
                    (
                        customer.company_name,
                        customer.country,
                        customer.contact_name,
                        customer.email,
                        customer.phone,
                        customer.is_active,
                        customer_id,
                    ),
                )

                updated = cur.fetchone()

                if updated is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Customer not found",
                    )

    except (
        errors.UniqueViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_customer_integrity_error(exc)

    return updated


# ============================================================
# PATCH /customers/{customer_id}
# ============================================================

@router.patch(
    "/{customer_id}",
    response_model=Customer,
)
def patch_customer(
    customer_id: CustomerId,
    customer: CustomerPatch,
):
    updates = customer.model_dump(
        exclude_unset=True
    )

    if not updates:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                return get_customer_or_404(
                    cur, customer_id
                )

    if not updates.keys() <= ALLOWED_UPDATE_FIELDS:
        raise HTTPException(
            status_code=422,
            detail="Invalid update fields",
        )

    set_clause = ", ".join(
        f"{field} = %s"
        for field in updates
    )

    params = [
        *updates.values(),
        customer_id,
    ]

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    UPDATE customers
                    SET {set_clause}
                    WHERE id = %s
                    RETURNING {CUSTOMER_COLUMNS};
                    """,
                    params,
                )

                updated = cur.fetchone()

                if updated is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Customer not found",
                    )

    except (
        errors.UniqueViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_customer_integrity_error(exc)

    return updated


# ============================================================
# DELETE /customers/{customer_id}
# ============================================================

@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer(customer_id: CustomerId):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    DELETE FROM customers
                    WHERE id = %s
                    RETURNING id;
                    """,
                    (customer_id,),
                )

                deleted = cur.fetchone()

                if deleted is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Customer not found",
                    )

    except errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer is referenced "
                "by other records"
            ),
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
