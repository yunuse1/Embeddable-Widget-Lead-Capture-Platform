from fastapi import FastAPI


app = FastAPI(
    title="Embeddable Widget & Lead Capture Platform",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }