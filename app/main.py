from fastapi import FastAPI
from app.routers.ports import router as ports_router
from app.routers import ships
from app.routers import containers
from app.routers import customers

app = FastAPI(
    title="Logistics API",
    version="1.0.0",
    description="REST API for an international maritime logistics company",
)

app.include_router(ports_router)
app.include_router(ships.router)
app.include_router(containers.router)
app.include_router(customers.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}