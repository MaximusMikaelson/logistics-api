
from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app


client = TestClient(app)


# ==========================================
# HEALTH CHECK
# ==========================================

def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ==========================================
# GET PORTS
# ==========================================

def test_get_ports():
    response = client.get("/ports/")

    assert response.status_code == 200
    assert "ports" in response.json()
    assert isinstance(response.json()["ports"], list)


def test_get_port_by_id(test_port):
    response = client.get(f"/ports/{test_port}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_port
    assert data["name"] == "Port of Rotterdam"
    assert data["country"] == "Netherlands"


def test_get_nonexistent_port():
    response = client.get("/ports/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Port not found"
    }


# ==========================================
# POST PORTS
# ==========================================

def test_create_port():
    response = client.post(
        "/ports/",
        json={
            "name": "Port of Barcelona",
            "country": "Spain",
        },
    )

    data = response.json()

    try:
        assert response.status_code == 201
        assert isinstance(data["id"], int)
        assert data["name"] == "Port of Barcelona"
        assert data["country"] == "Spain"

    finally:
        if "id" in data:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM ports WHERE id = %s",
                        (data["id"],),
                    )


def test_create_port_with_empty_name():
    response = client.post(
        "/ports/",
        json={
            "name": "",
            "country": "Germany",
        },
    )

    assert response.status_code == 422


def test_create_port_without_country():
    response = client.post(
        "/ports/",
        json={
            "name": "Port of Barcelona",
        },
    )

    assert response.status_code == 422


def test_create_port_with_spaces_only():
    response = client.post(
        "/ports/",
        json={
            "name": "     ",
            "country": "Germany",
        },
    )

    assert response.status_code == 422


def test_create_port_trims_spaces():
    response = client.post(
        "/ports/",
        json={
            "name": "  Port of Oslo  ",
            "country": "  Norway  ",
        },
    )

    assert response.status_code == 201

    data = response.json()

    try:
        assert data["name"] == "Port of Oslo"
        assert data["country"] == "Norway"

    finally:
        if "id" in data:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM ports WHERE id = %s",
                        (data["id"],),
                    )


def test_create_port_with_long_name():
    response = client.post(
        "/ports/",
        json={
            "name": "A" * 101,
            "country": "Germany",
        },
    )

    assert response.status_code == 422


def test_create_port_with_short_country():
    response = client.post(
        "/ports/",
        json={
            "name": "Port of Helsinki",
            "country": "F",
        },
    )

    assert response.status_code == 422


def test_create_port_with_long_country():
    response = client.post(
        "/ports/",
        json={
            "name": "Port of Helsinki",
            "country": "A" * 101,
        },
    )

    assert response.status_code == 422


def test_create_port_with_numeric_name():
    response = client.post(
        "/ports/",
        json={
            "name": 123,
            "country": "Germany",
        },
    )

    assert response.status_code == 422


def test_create_port_with_list_country():
    response = client.post(
        "/ports/",
        json={
            "name": "Port of Oslo",
            "country": ["Norway", "Sweden"],
        },
    )

    assert response.status_code == 422


def test_create_port_with_null_name():
    response = client.post(
        "/ports/",
        json={
            "name": None,
            "country": "Germany",
        },
    )

    assert response.status_code == 422


# ==========================================
# PUT PORTS
# ==========================================

def test_update_port(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "Port of Rotterdam Updated",
            "country": "Netherlands",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_port
    assert data["name"] == "Port of Rotterdam Updated"
    assert data["country"] == "Netherlands"


def test_update_nonexistent_port():
    response = client.put(
        "/ports/999999",
        json={
            "name": "Unknown Port",
            "country": "Germany",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Port not found"
    }


def test_update_port_with_empty_name(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "",
            "country": "Netherlands",
        },
    )

    assert response.status_code == 422


def test_update_port_without_country(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "Port of Rotterdam Updated",
        },
    )

    assert response.status_code == 422


def test_update_port_with_long_name(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "A" * 101,
            "country": "Netherlands",
        },
    )

    assert response.status_code == 422


# ==========================================
# DELETE PORTS
# ==========================================

def test_delete_port(test_port):
    response = client.delete(f"/ports/{test_port}")

    assert response.status_code == 204

    check_response = client.get(f"/ports/{test_port}")

    assert check_response.status_code == 404


def test_delete_nonexistent_port():
    response = client.delete("/ports/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Port not found"
    }


# ==========================================
# ADDITIONAL PORT VALIDATION TESTS
# ==========================================

def test_update_port_trims_spaces(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "  Port of Hamburg  ",
            "country": "  Germany  ",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Port of Hamburg"
    assert data["country"] == "Germany"


def test_update_port_with_spaces_only(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "     ",
            "country": "Germany",
        },
    )

    assert response.status_code == 422


def test_update_port_with_short_country(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": "Port of Hamburg",
            "country": "G",
        },
    )

    assert response.status_code == 422


def test_update_port_with_null_name(test_port):
    response = client.put(
        f"/ports/{test_port}",
        json={
            "name": None,
            "country": "Germany",
        },
    )

    assert response.status_code == 422
