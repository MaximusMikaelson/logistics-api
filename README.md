
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
- Git

## Features

- RESTful CRUD operations
- Request and response validation
- Search and filtering
- Limit-offset pagination
- Parameterized SQL queries
- Database transactions
- Row-level locking
- Container status transition validation
- Customer activation and deactivation
- HTTP error handling
- Interactive Swagger documentation

## Modules

- [x] Ports
- [x] Ships
- [x] Containers
- [x] Customers
- [ ] Cargo
- [ ] Voyages
- [ ] Shipments
- [ ] Tracking Events

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
│   │   └── customers.py
│   └── schemas/
│       ├── port.py
│       ├── ship.py
│       ├── container.py
│       └── customer.py
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

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

The PostgreSQL database, tables and permissions must
be configured before using the API.

Automated database initialization is planned.

## Running the Application

```bash
uvicorn app.main:app --reload
```

## API Documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Testing

Configure a separate test database before running tests.

```bash
pytest -v
```

## Roadmap

- Cargo management
- Voyage management
- Shipment management
- Container tracking
- Database migrations
- Service and repository layers
- Authentication and authorization
- Docker deployment
- Extended automated testing
- CI/CD pipeline

## Project Status

Active development.

This project demonstrates practical backend engineering
through the development of a maritime logistics system.
