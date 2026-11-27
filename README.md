
# Logistics API

A REST API for international maritime logistics management,
built with Python, FastAPI and PostgreSQL.

## Tech Stack

- Python 3.14
- FastAPI
- PostgreSQL
- Psycopg 3
- Pydantic v2
- Pytest
- Uvicorn
- Linux (Ubuntu)
- Git & GitHub

## Features

- RESTful CRUD operations
- Request and response validation
- Partial updates with PATCH
- Search and filtering
- Limit-offset pagination
- Parameterized SQL queries
- Database transactions
- Row-level locking
- Foreign key constraints
- ISO 6346 container number validation
- Container status transition validation
- Customer activation and deactivation
- Cargo weight and volume management
- Precise decimal arithmetic
- Cross-module business logic validation
- HTTP error handling
- Environment-based configuration
- Interactive Swagger documentation

## Modules

- [x] Ports
- [x] Ships
- [x] Containers
- [x] Customers
- [x] Cargo
- [ ] Voyages
- [ ] Shipments
- [ ] Tracking Events

## Business Rules

- Container numbers must comply with ISO 6346 validation.
- Container status transitions must follow predefined rules.
- Containers in transit cannot be deleted.
- Cargo must belong to an existing customer.
- Cargo cannot be registered for inactive customers.
- Cargo weight and volume must be positive.
- Existing cargo records are preserved when a customer is deactivated.

## Project Structure

```text
logistics-api/
├── app/
│   ├── database.py
│   ├── main.py
│   ├── routers/
│   │   ├── ports.py
│   │   ├── ships.py
│   │   ├── containers.py
│   │   ├── customers.py
│   │   └── cargo.py
│   └── schemas/
│       ├── port.py
│       ├── ship.py
│       ├── container.py
│       ├── customer.py
│       └── cargo.py
├── tests/
│   ├── conftest.py
│   └── test_ports.py
├── test_db.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/MaximusMikaelson/logistics-api.git
cd logistics-api
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
cp .env.example .env
```

Set your PostgreSQL connection settings in `.env`.

## Database Configuration

The application uses PostgreSQL as its relational database.

Required environment variables:

| Variable | Description |
|----------|-------------|
| DB_HOST | Database host |
| DB_PORT | Database port |
| DB_NAME | Database name |
| DB_USER | Database user |
| DB_PASSWORD | Database password |

The PostgreSQL database, tables and permissions must
be configured manually before using the API.

Automated database initialization and migrations are planned.

Never commit real credentials or the `.env` file.

## Running the Application

```bash
uvicorn app.main:app --reload
```

For development environments that require access
from outside the Linux instance, such as WSL:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## API Resources

| Resource | Endpoint | Description |
|----------|----------|-------------|
| Health | /health | Application health check |
| Ports | /ports/ | Maritime port management |
| Ships | /ships/ | Vessel management |
| Containers | /containers/ | Shipping container management |
| Customers | /customers/ | Customer management |
| Cargo | /cargo/ | Cargo registration and management |

## Cargo Categories

- General
- Perishable
- Hazardous
- Oversized
- Fragile

## Testing

The project uses Pytest for automated testing.

Configure a separate test database before running tests.

```bash
pytest -v
```

Automated test coverage is currently focused on the Ports module.

Additional modules are being verified through manual API
testing using Swagger UI.

Extended automated test coverage is planned.

## Roadmap

- Voyage management
- Shipment management
- Container tracking
- Database initialization scripts
- Database migrations
- Database indexing and query optimization
- Service and repository layers
- Connection pooling
- Authentication and authorization
- Structured application logging
- Docker deployment
- Extended automated testing
- CI/CD pipeline

## Project Status

Active development.

Five of eight planned core modules have been implemented.

This project demonstrates practical backend engineering
through the development of a maritime logistics system,
with an emphasis on relational databases, REST API design,
data integrity and business logic.

## Author

[MaximusMikaelson](https://github.com/MaximusMikaelson)
