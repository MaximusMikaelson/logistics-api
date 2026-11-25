
from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    status,
)
from psycopg import errors
from psycopg.rows import dict_row

from app.database import get_connection
from app.schemas.container import (
    Container,
    ContainerCreate,
    ContainerUpdate,
    ContainerPatch,
    ContainerListResponse,
    ContainerStatus,
    ContainerType,
)


router = APIRouter(
    prefix="/containers",
    tags=["Containers"],
)


# ============================================================
# CONSTANTS
# ============================================================

CONTAINER_COLUMNS = """
    id,
    container_number,
    container_type,
    capacity_kg,
    current_port_id,
    status
"""

ALLOWED_UPDATE_FIELDS = {
    "container_number",
    "container_type",
    "capacity_kg",
    "current_port_id",
    "status",
}


# ============================================================
# HELPERS
# ============================================================

def get_container_or_404(cur, container_id: int):
    cur.execute(
        f"""
        SELECT {CONTAINER_COLUMNS}
        FROM containers
        WHERE id = %s;
        """,
        (container_id,),
    )

    container = cur.fetchone()

    if container is None:
        raise HTTPException(
            status_code=404,
            detail="Container not found",
        )

    return container


def handle_container_integrity_error(exc):
    if isinstance(exc, errors.UniqueViolation):
        raise HTTPException(
            status_code=409,
            detail="Container number already exists",
        ) from exc

    if isinstance(exc, errors.ForeignKeyViolation):
        raise HTTPException(
            status_code=422,
            detail="Referenced port does not exist",
        ) from exc

    if isinstance(exc, errors.CheckViolation):
        raise HTTPException(
            status_code=422,
            detail="Container violates database constraints",
        ) from exc

    if isinstance(exc, errors.NotNullViolation):
        raise HTTPException(
            status_code=422,
            detail="Required container field cannot be null",
        ) from exc

    raise exc


def validate_container_transition(
    current_status: str,
    new_status: str,
):
    """
    Basic status transition validation.

    Full shipment-related rules will be implemented
    when the Shipments module is introduced.
    """
    allowed_transitions = {
        "available": {
            "available",
            "in_transit",
            "maintenance",
        },
        "in_transit": {
            "in_transit",
            "available",
        },
        "maintenance": {
            "maintenance",
            "available",
        },
    }

    if new_status not in allowed_transitions.get(
        current_status, set()
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot change container status "
                f"from {current_status} to {new_status}"
            ),
        )


# ============================================================
# GET /containers/
# Search, filtering, pagination
# ============================================================

@router.get(
    "/",
    response_model=ContainerListResponse,
)
def get_containers(
    search: Annotated[
        str | None,
        Query(max_length=50),
    ] = None,
    container_type: ContainerType | None = None,
    container_status: Annotated[
        ContainerStatus | None,
        Query(alias="status"),
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
        conditions.append(
            "container_number ILIKE %s"
        )
        params.append(f"%{search}%")

    if container_type is not None:
        conditions.append(
            "container_type = %s"
        )
        params.append(container_type)

    if container_status is not None:
        conditions.append(
            "status = %s"
        )
        params.append(container_status)

    if current_port_id is not None:
        conditions.append(
            "current_port_id = %s"
        )
        params.append(current_port_id)

    if min_capacity is not None:
        conditions.append(
            "capacity_kg >= %s"
        )
        params.append(min_capacity)

    if max_capacity is not None:
        conditions.append(
            "capacity_kg <= %s"
        )
        params.append(max_capacity)

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
                FROM containers
                {where_clause};
                """,
                params,
            )

            total = cur.fetchone()["total"]

            cur.execute(
                f"""
                SELECT {CONTAINER_COLUMNS}
                FROM containers
                {where_clause}
                ORDER BY id
                LIMIT %s OFFSET %s;
                """,
                (*params, limit, offset),
            )

            containers = cur.fetchall()

    return {
        "containers": containers,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# GET /containers/{container_id}
# ============================================================

@router.get(
    "/{container_id}",
    response_model=Container,
)
def get_container(container_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            container = get_container_or_404(
                cur, container_id
            )

    return container


# ============================================================
# POST /containers/
# ============================================================

@router.post(
    "/",
    response_model=Container,
    status_code=status.HTTP_201_CREATED,
)
def create_container(container: ContainerCreate):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    INSERT INTO containers (
                        container_number,
                        container_type,
                        capacity_kg,
                        current_port_id,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING {CONTAINER_COLUMNS};
                    """,
                    (
                        container.container_number,
                        container.container_type,
                        container.capacity_kg,
                        container.current_port_id,
                        container.status,
                    ),
                )

                created = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.ForeignKeyViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_container_integrity_error(exc)

    return created


# ============================================================
# PUT /containers/{container_id}
# Full update
# ============================================================

@router.put(
    "/{container_id}",
    response_model=Container,
)
def update_container(
    container_id: int,
    container: ContainerUpdate,
):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:

                # Lock the row for this transaction.
                cur.execute(
                    """
                    SELECT status
                    FROM containers
                    WHERE id = %s
                    FOR UPDATE;
                    """,
                    (container_id,),
                )

                existing = cur.fetchone()

                if existing is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Container not found",
                    )

                validate_container_transition(
                    existing["status"],
                    container.status,
                )

                cur.execute(
                    f"""
                    UPDATE containers
                    SET
                        container_number = %s,
                        container_type = %s,
                        capacity_kg = %s,
                        current_port_id = %s,
                        status = %s
                    WHERE id = %s
                    RETURNING {CONTAINER_COLUMNS};
                    """,
                    (
                        container.container_number,
                        container.container_type,
                        container.capacity_kg,
                        container.current_port_id,
                        container.status,
                        container_id,
                    ),
                )

                updated = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.ForeignKeyViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_container_integrity_error(exc)

    return updated


# ============================================================
# PATCH /containers/{container_id}
# Partial update
# ============================================================

@router.patch(
    "/{container_id}",
    response_model=Container,
)
def patch_container(
    container_id: int,
    container: ContainerPatch,
):
    updates = container.model_dump(
        exclude_unset=True
    )

    if not updates:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                return get_container_or_404(
                    cur, container_id
                )

    if not updates.keys() <= ALLOWED_UPDATE_FIELDS:
        raise HTTPException(
            status_code=422,
            detail="Invalid update fields",
        )

    required_fields = {
        "container_number",
        "container_type",
        "capacity_kg",
        "status",
    }

    for field in required_fields:
        if (
            field in updates
            and updates[field] is None
        ):
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    set_clause = ", ".join(
        f"{field} = %s"
        for field in updates
    )

    params = [
        *updates.values(),
        container_id,
    ]

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:

                cur.execute(
                    """
                    SELECT status
                    FROM containers
                    WHERE id = %s
                    FOR UPDATE;
                    """,
                    (container_id,),
                )

                existing = cur.fetchone()

                if existing is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Container not found",
                    )

                if "status" in updates:
                    validate_container_transition(
                        existing["status"],
                        updates["status"],
                    )

                cur.execute(
                    f"""
                    UPDATE containers
                    SET {set_clause}
                    WHERE id = %s
                    RETURNING {CONTAINER_COLUMNS};
                    """,
                    params,
                )

                updated = cur.fetchone()

    except (
        errors.UniqueViolation,
        errors.ForeignKeyViolation,
        errors.CheckViolation,
        errors.NotNullViolation,
    ) as exc:
        handle_container_integrity_error(exc)

    return updated


# ============================================================
# DELETE /containers/{container_id}
# ============================================================

@router.delete(
    "/{container_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_container(container_id: int):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:

                cur.execute(
                    """
                    SELECT status
                    FROM containers
                    WHERE id = %s
                    FOR UPDATE;
                    """,
                    (container_id,),
                )

                existing = cur.fetchone()

                if existing is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Container not found",
                    )

                if existing["status"] == "in_transit":
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Cannot delete a container "
                            "while it is in transit"
                        ),
                    )

                cur.execute(
                    """
                    DELETE FROM containers
                    WHERE id = %s
                    RETURNING id;
                    """,
                    (container_id,),
                )

    except errors.ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Container is referenced "
                "by other records"
            ),
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
