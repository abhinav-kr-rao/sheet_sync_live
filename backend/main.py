from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for Frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "sheets_db"),
}


def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


@app.get("/")
def read_root():
    return {"message": "Google Sheets Sync API is running!"}


@app.get("/data")
def get_sheet_data():
    """
    Fetches all data from the 'sheet_data' table.
    Returns a list of dictionaries (rows).
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)  # Return rows as dicts

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
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
