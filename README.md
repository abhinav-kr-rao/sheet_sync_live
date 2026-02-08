# Google Sheets to MySQL Sync App

This application syncs data from a Google Sheet to a MySQL database in near real-time and displays it on a Next.js frontend.

## Prerequisites

*   **Python 3.10+** (with `uv` installed, or use `pip`)
*   **Node.js 18+**
*   **MySQL Server** running locally or in the cloud.
*   **Google Cloud Service Account** with headers/keys.

## Setup

### 1. Google Cloud Credentials
1.  Place your `credentials.json` (Service Account Key) inside the `backend/` folder.
2.  Share your Google Sheet with the `client_email` found in `credentials.json`.

### 2. Backend Setup
Navigate to the `backend` folder:
```bash
cd backend
```

Create a `.env` file (copy from `.env.example` or create new) with your config:
```ini
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=sheets_db
SPREADSHEET_ID=your_google_sheet_id
```

Install dependencies:
```bash
# using uv (recommended)
uv sync

# OR using pip
pip install -r requirements.txt
```

### 3. Frontend Setup
Navigate to the `frontend` folder:
```bash
cd frontend
npm install
```

## Running the Application

You need to run **3 separate terminals**:

### Terminal 1: Sync Script
This script fetches data from Google Sheets and syncs it to MySQL every 2 seconds.
```bash
cd backend
uv run sheets_to_json.py
```

### Terminal 2: Backend API
This serves the data from MySQL to the Frontend.
```bash
cd backend
uv run fastapi dev main.py
```

### Terminal 3: Frontend
This runs the Next.js UI.
```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.
