from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from auth.router import router as auth_router
from auth.passkeys import router as passkey_router
from patients.router import router as patients_router
from patients.ficha import router as ficha_router
from patients.notes import router as notes_router
from appointments.router import router as appointments_router
from finance.router import router as finance_router
from specialties.router import router as specialties_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Conflur API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(passkey_router)
app.include_router(patients_router)
app.include_router(ficha_router)
app.include_router(notes_router)
app.include_router(appointments_router)
app.include_router(finance_router)
app.include_router(specialties_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
