import hmac
import logging
import os
import re

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import db

API_KEY = os.environ["API_KEY"]

app = FastAPI()

app.mount("/static", StaticFiles(directory="/app/static"), name="static")

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def inject_api_key() -> None:
    index_path = "/app/static/index.html"
    with open(index_path, "r") as f:
        content = f.read()
    content = content.replace("REPLACE_ME", API_KEY)
    with open(index_path, "w") as f:
        f.write(content)
    logger.info("Static UI ready")


@app.get("/")
def serve_ui():
    return FileResponse("/app/static/index.html")

CUSTOMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,20}$")


def verify_api_key(x_api_key: str = Header(None)) -> None:
    if x_api_key is None or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    logger.error("Unhandled exception: %s", type(exc).__name__, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/customer/{customer_id}", dependencies=[Depends(verify_api_key)])
def get_customer(customer_id: str):
    if not CUSTOMER_ID_PATTERN.match(customer_id):
        raise HTTPException(status_code=400, detail="Invalid customer_id format")

    conn = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT customer_id, risk_tier, risk_factors FROM customers WHERE customer_id = %s",
            (customer_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {
            "customer_id": row[0],
            "risk_tier": row[1],
            "risk_factors": row[2],
        }
    except HTTPException:
        raise
    except Exception:
        logger.error("Database query failed")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn is not None:
            conn.close()
