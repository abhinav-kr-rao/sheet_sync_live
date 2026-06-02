import os
from multiprocessing import pool

import mysql.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import Error, pooling
from pydantic import BaseModel

# Import the sync manager
from sheets_to_json import sync_manager

load_dotenv()

app = FastAPI()

# Enable CORS
origins = ["http://localhost:3000", "https://sheet-sync-live.vercel.app/"]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Start/Stop Sync on App Lifecycle
@app.on_event("startup")
def startup_event():
    # Only start if ID is present, otherwise wait for /settings
    if sync_manager.sheet_id:
        sync_manager.start()


@app.on_event("shutdown")
def shutdown_event():
    sync_manager.stop()


# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "sheets_db"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "ssl_disabled": False,
}

# implementing connection pooling
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="sheets_pool", pool_size=5, pool_reset_session=True, **DB_CONFIG
    )
    print("Database connection pool successfully created")
except Error as e:
    print("Failed to created db pool")
    db_pool = None


def get_db_connection():
    """Establishes a connection to the MySQL database."""
    # try:
    #     conn = mysql.connector.connect(**DB_CONFIG)
    #     if conn.is_connected():
    #         return conn
    # except Error as e:
    #     print(f"Error connecting to MySQL: {e}")
    #     return None
    if not db_pool:
        return None
    try:
        return db_pool.get_connection()
    except Error as e:
        print(f"Error getting connection from pool : {e}")
        return None


class SheetSettings(BaseModel):
    sheet_id: str


@app.get("/")
def read_root():
    return {
        "message": "Google Sheets Sync API is running!",
        "current_sheet_id": sync_manager.sheet_id,
        "status": "Running" if sync_manager.running else "Stopped",
    }


@app.post("/settings")
async def update_settings(settings: SheetSettings):
    """Updates the Sheet ID and restarts sync."""
    if not settings.sheet_id:
        raise HTTPException(status_code=400, detail="Sheet ID cannot be empty")

    sync_manager.set_sheet_id(settings.sheet_id)
    return {"message": "Sheet ID updated", "new_id": settings.sheet_id}


@app.get("/settings")
def get_settings():
    return {"sheet_id": sync_manager.sheet_id}


@app.post("/webhook")
async def webhook_trigger():
    """
    Manual trigger to force a check immediately.
    Can be called by Google Apps Script or manually.
    """
    # Force check by resetting last modified time
    sync_manager.last_modified_time = None
    return {"message": "Sync triggered manually"}


@app.get("/data")
def get_sheet_data():
    conn = get_db_connection()
    if not conn:
        # Instead of a 500 error, return a safe empty state with a warning
        return {"data": [], "warning": "Database temporarily unreachable"}

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES LIKE 'sheet_data'")
        if not cursor.fetchone():
            return {"data": []}

        cursor.execute("SELECT * FROM sheet_data")
        return {"data": cursor.fetchall()}
    except Error as e:
        print(f"Database error during fetch: {e}")
        return {"data": [], "warning": "Failed to read database"}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()  # This actually just returns it to the pool!
    # def get_sheet_data():
    """
    Fetches all data from the 'sheet_data' table.
    Returns a list of dictionaries (rows).
    """
    conn = get_db_connection()
    # print("conn /is ", conn)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)  # Return rows as dicts
        print("Curosr is ", cursor)
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'sheet_data'")
        result = cursor.fetchone()
        if not result:
            return {"message": "No data synced yet.", "data": []}

        cursor.execute("SELECT * FROM sheet_data")
        rows = cursor.fetchall()

        return {"data": rows}

    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
