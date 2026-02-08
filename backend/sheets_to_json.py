import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys
import time
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the scope
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Path to the credentials file
CREDENTIALS_FILE = "credentials.json"
# The ID of your Google Sheet (from the URL)
SHEET_ID = os.getenv("SPREADSHEET_ID")

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "sheets_db"),
}


def create_db_if_not_exists():
    """Creates the database if it doesn't exist."""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
        )
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            print(f"Database '{DB_CONFIG['database']}' checked/created.")
            cursor.close()
            conn.close()
    except Error as e:
        print(f"Error creating database: {e}")


def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def sync_data_to_db(header, rows):
    """
    Syncs the data to MySQL.
    Strategy: Drop table -> Create Table (dynamic schema) -> Insert All.
    This ensures exact mirror of the sheet.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        table_name = "sheet_data"

        # 1. Drop existing table to handle schema changes or deleted rows
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # 2. Create Table based on headers
        # Sanitize column names to be valid MySQL identifiers
        safe_headers = [
            f"`{h.replace(' ', '_').replace('-', '_')}`" if h else f"`col_{i}`"
            for i, h in enumerate(header)
        ]

        # If header is empty, generate generic columns
        if not safe_headers and rows:
            safe_headers = [f"`col_{i}`" for i in range(len(rows[0]))]

        if not safe_headers:
            print("No headers or data found. Skipping DB sync.")
            return

        cols_def = ", ".join([f"{col} TEXT" for col in safe_headers])
        create_query = f"CREATE TABLE {table_name} ({cols_def});"
        cursor.execute(create_query)

        # 3. Insert Data
        if rows:
            # Prepare INSERT statement
            placeholders = ", ".join(["%s"] * len(safe_headers))
            cols_str = ", ".join(safe_headers)
            insert_query = (
                f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
            )

            # Pad rows if they are shorter than header (Google Sheets behavior)
            # or truncate if longer
            normalized_rows = []
            for row in rows:
                # Resize row to match header length
                if len(row) < len(safe_headers):
                    row += [""] * (len(safe_headers) - len(row))
                elif len(row) > len(safe_headers):
                    row = row[: len(safe_headers)]
                normalized_rows.append(row)

            cursor.executemany(insert_query, normalized_rows)
            conn.commit()
            print(f"   ✅ Synced {len(rows)} rows to MySQL table '{table_name}'.")

    except Error as e:
        print(f"MySQL Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def fetch_sheet_data():
    """
    Fetches data from Google Sheet and syncs to MySQL.
    """
    print("Starting Google Sheets -> MySQL sync loop...")

    # Ensure DB exists first
    create_db_if_not_exists()

    try:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(f"Credentials file '{CREDENTIALS_FILE}' not found.")

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE, scope
        )

        last_hash = None

        while True:
            try:
                client = gspread.authorize(creds)
                print(f"Checking sheet '{SHEET_ID}'...")

                try:
                    sheet = client.open_by_key(SHEET_ID).sheet1
                except gspread.exceptions.SpreadsheetNotFound:
                    print("❌ Sheet not found. Check ID and permissions.")
                    time.sleep(10)
                    continue

                raw_data = sheet.get_all_values()

                if not raw_data:
                    print("Sheet is empty.")
                else:
                    # Separate header and data
                    header = raw_data[0]
                    rows = raw_data[1:]

                    # Simple change detection using string representation of data
                    # (For a real production app, use a proper checksum)
                    current_hash = str(raw_data)

                    if current_hash != last_hash:
                        print("🔔 Changes detected in Sheet!")
                        sync_data_to_db(header, rows)
                        last_hash = current_hash
                    else:
                        print("   No changes.")

            except Exception as e:
                print(f"⚠️ Loop Error: {e}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
    except Exception as e:
        print(f"Fatal Error: {e}")


if __name__ == "__main__":
    fetch_sheet_data()
