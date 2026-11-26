import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env.test", override=True)

if os.getenv("DB_NAME") != "logistics_test_db":
    raise RuntimeError("Tests must use logistics_test_db")

import pytest

from app.database import get_connection


@pytest.fixture
def test_port():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ports (name, country)
                VALUES (%s, %s)
                RETURNING id
                """,
                ("Port of Rotterdam", "Netherlands"),
            )
            port_id = cur.fetchone()[0]

    yield port_id

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ports WHERE id = %s",
                (port_id,),
            )