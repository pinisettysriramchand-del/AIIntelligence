"""Application entry point."""

from stratiq.interface.app_factory import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("stratiq.main:app", host="0.0.0.0", port=8000, reload=True)
