# Google Sheets to MySQL Sync App

This application syncs data from a Google Sheet to a MySQL database in near real-time and displays it on a Next.js frontend.

## Prerequisites

*   **Python 3.10+** (with `uv` installed, or use `pip`)
*   **Node.js 18+**
*   **MySQL Server** running locally or in the cloud.
*   **Google Cloud Service Account** with headers/keys.

## Setup

### 1. Google Cloud Credentials (Important)

**Note:** The `credentials.json` file is NOT included in the repository for security. You must generate your own.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a project and enable the **Google Sheets API** and **Google Drive API**.
3.  Go to **IAM & Admin > Service Accounts**.
4.  Create a Service Account.
5.  Go to the **Keys** tab -> **Add Key** -> **Create new key** -> **JSON**.
6.  A JSON file will download. Rename it to `credentials.json`.
7.  Place this `credentials.json` file inside the `backend/` folder.
8.  **Crucial Step:** Open the `credentials.json` file, copy the `client_email` address, and **Share your Google Sheet** with that email (give it Editor/Viewer access).

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

## Running the Application

You need to run **2 separate terminals** (Backend API now handles syncing automatically):

### Terminal 1: Backend API
This starts the server AND the sync process in the background.
```bash
cd backend
uv run FastAPI dev main.py
```

### Terminal 2: Frontend
This runs the Next.js UI.
```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the live dashboard.

## Deployment Guide

### 1. Deploying Backend (e.g., Railway/Render)
The backend needs to run the Python FastAPI server.

1.  **Push your code to GitHub**.
2.  **Create a Project** on [Railway](https://railway.app/) or Render.
3.  **Connect your GitHub Repo**.
4.  **Set Environment Variables** in the Railway Dashboard:
    *   `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Your cloud database details.
    *   `SPREADSHEET_ID`: The ID of your Google Sheet.
    *   `GOOGLE_CREDENTIALS`: **Open your `credentials.json` file, copy the entire content, and paste it as the value for this variable.**
    *   `FRONTEND_URL`: `https://your-frontend-app.vercel.app` (Add this *after* deploying frontend).
5.  Railway will automatically detect the `Procfile` and start the app.

### 2. Deploying Frontend (Vercel)
The frontend is a Next.js app.

1.  **Go to [Vercel](https://vercel.com/)**.
2.  **Import your GitHub Project**.
3.  **Set Environment Variables**:
    *   `NEXT_PUBLIC_API_URL`: The URL of your deployed Backend (e.g., `https://web-production-xyz.up.railway.app`).
4.  **Deploy**.

### 3. Final Step
Once Frontend is deployed, go back to your Backend variables and set `FRONTEND_URL` to your Vercel domain to allow CORS.
