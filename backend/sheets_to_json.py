import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import os
import sys
import time
import threading
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
# The ID of your Google Sheet (from the URL) - now managed by SheetSyncManager

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "sheets_db"),
}


class SheetSyncManager:
    def __init__(self):
        self.sheet_id = os.getenv("SPREADSHEET_ID")
        self.running = False
        self.thread = None
        self.creds = None
        self.drive_service = None
        self.gspread_client = None
        self.last_modified_time = None

    def _setup_services(self):
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"❌ Credentials file '{CREDENTIALS_FILE}' not found.")
            return False

        try:
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(
                CREDENTIALS_FILE, scope
            )
            self.gspread_client = gspread.authorize(self.creds)
            self.drive_service = build("drive", "v3", credentials=self.creds)
            return True
        except Exception as e:
            print(f"❌ Error setting up Google Services: {e}")
            return False

    def create_db_if_not_exists(self):
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

    def get_db_connection(self):
        """Establishes a connection to the MySQL database."""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                return conn
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None

    def sync_data_to_db(self, header, rows):
        """
        Syncs the data to MySQL.
        Strategy: Drop table -> Create Table (dynamic schema) -> Insert All.
        This ensures exact mirror of the sheet.
        """
        conn = self.get_db_connection()
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
                if conn.is_connected():
                    cursor.close()
                    conn.close()
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

    def _sync_loop(self):
        print(f"Starting sync loop for Sheet ID: {self.sheet_id}")

        if not self._setup_services():
            self.running = False  # Stop if services can't be set up
            return

        self.create_db_if_not_exists()
        self.last_hash = None  # Reset state

        while self.running:
            try:
                # 1. Fetch Data Directly (No Drive API Metadata check)
                # This ensures real-time updates as Drive API modifiedTime has propagation delay
                try:
                    sheet = self.gspread_client.open_by_key(self.sheet_id).sheet1
                    raw_data = sheet.get_all_values()

                    # print("Raw data fetched:", raw_data)

                    if not raw_data:
                        current_hash = "EMPTY"
                        header, rows = [], []
                    else:
                        current_hash = str(raw_data)  # Simple string hash
                        header = raw_data[0]
                        rows = raw_data[1:]

                    # Check for changes (content based or manual trigger forced reset)
                    # self.last_modified_time is repurposed as a "Force Sync" flag from webhook
                    if (
                        self.last_modified_time is None
                        or current_hash != self.last_hash
                    ):
                        print("Change detected! Syncing...")
                        self.sync_data_to_db(header, rows)
                        self.last_hash = current_hash
                        self.last_modified_time = "SYNCED"  # Set to something not None
                    else:
                        # print("   No changes.") # Reduce spam
                        pass

                except gspread.exceptions.SpreadsheetNotFound:
                    print(
                        f"Sheet with ID '{self.sheet_id}' not found. Check ID and permissions."
                    )
                    time.sleep(5)
                except Exception as e:
                    print(f"Error fetching sheet data: {e}")

            except Exception as e:
                print(f"Loop Error: {e}")

            time.sleep(2)  # Poll every 2 seconds

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()
        print("SheetSyncManager started.")

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)  # Wait for the thread to finish
            self.thread = None
        print("SheetSyncManager stopped.")

    def set_sheet_id(self, new_id):
        if new_id == self.sheet_id:
            return
        print(f"Switching to new Sheet ID: {new_id}")
        self.stop()
        self.sheet_id = new_id
        self.last_modified_time = None  # Reset to force fetch on new sheet
        self.start()


# Global Instance
sync_manager = SheetSyncManager()

if __name__ == "__main__":
    # For standalone testing
    if not os.getenv("SPREADSHEET_ID"):
        print("Please set the SPREADSHEET_ID environment variable in your .env file.")
        sys.exit(1)
    else:
        sync_manager.start()
        try:
            while True:
                time.sleep(1)  # Keep main thread alive
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt detected.")
            sync_manager.stop()
            sys.exit(0)
        except Exception as e:
            print(f"Fatal error in main thread: {e}")
            sync_manager.stop()
            sys.exit(1)
