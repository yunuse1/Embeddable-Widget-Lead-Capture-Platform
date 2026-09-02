from fastapi import FastAPI

from app.routers import auth, public, widgets


app = FastAPI(
    title="Embeddable Widget & Lead Capture Platform",
    version="0.3.0",
)


app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(public.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
