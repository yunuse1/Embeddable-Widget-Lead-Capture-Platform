from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, public, submissions, widgets


app = FastAPI(
    title="Embeddable Widget & Lead Capture Platform",
    version="0.4.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(public.router)
app.include_router(submissions.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
