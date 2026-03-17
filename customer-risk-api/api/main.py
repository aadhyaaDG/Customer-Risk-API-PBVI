import logging
import re

from fastapi import FastAPI, HTTPException

import db

app = FastAPI()

logger = logging.getLogger(__name__)

CUSTOMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,20}$")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/customer/{customer_id}")
def get_customer(customer_id: str):
    if not CUSTOMER_ID_PATTERN.match(customer_id):
        raise HTTPException(status_code=422, detail="Invalid customer_id format")

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
