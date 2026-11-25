from fastapi import APIRouter, HTTPException
from app.schemas.port import Port, PortCreate, PortUpdate
from app.database import get_connection

router = APIRouter(
    prefix="/ports",
    tags=["Ports"],
)

@router.get("/")
def get_ports():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, country FROM ports ORDER BY id"
            )
            rows = cur.fetchall()

    return {
        "ports": [
            {"id": row[0], "name": row[1], "country": row[2]}
            for row in rows
        ]
    }

@router.get("/{port_id}", response_model=Port)
def get_port(port_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, country FROM ports WHERE id = %s",
                (port_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Port not found",
        )

    return {
        "id": row[0],
        "name": row[1],
        "country": row[2],
    }

@router.post("/", response_model=Port, status_code=201)
def create_port(port: PortCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ports (name, country)
                VALUES (%s, %s)
                RETURNING id, name, country
                """,
                (port.name, port.country),
            )
            row = cur.fetchone()

    return {
        "id": row[0],
        "name": row[1],
        "country": row[2],
    }

@router.put("/{port_id}", response_model=Port)
def update_port(port_id: int, port: PortUpdate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ports
                SET name = %s, country = %s
                WHERE id = %s
                RETURNING id, name, country
                """,
                (port.name, port.country, port_id),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Port not found",
        )

    return {
        "id": row[0],
        "name": row[1],
        "country": row[2],
    }

@router.delete("/{port_id}", status_code=204)
def delete_port(port_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ports WHERE id = %s RETURNING id",
                (port_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Port not found",
        )