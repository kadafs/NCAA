# 🛠️ Development Setup & Server Guide

This guide provides step-by-step instructions for starting the NCAA API development environment, including the backend, frontend, and Python analysis tools.

---

## 📋 Prerequisites

Ensure you have the following installed on your system:
- **[Bun](https://bun.sh/)**: Required for the backend and package management.
- **[Node.js](https://nodejs.org/) (v18+)**: Required for the Next.js frontend.
- **[Python](https://www.python.org/) (3.10+)**: Required for the statistical engines.
- **Git**: To manage the codebase.

---

## 🚀 Starting the Servers

The project is split into a **Backend (API)** and a **Frontend (UI)**. You should run both in separate terminal windows.

### 1. Backend (ElysiaJS + Bun)
The backend handles data fetching, scraping, and serving the API routes.

- **Directory**: Project Root (`/`)
- **Command**:
  ```bash
  bun dev
  ```
- **Default Port**: `3000`
- **Verification**: Open [http://localhost:3000](http://localhost:3000) in your browser.

### 2. Frontend (Next.js + Turbopack)
The frontend provides the visual dashboard for predictions and analytics.

- **Directory**: `/frontend`
- **Command**:
  ```bash
  cd frontend
  npm run dev
  ```
- **Default Port**: `3001`
- **Verification**: Open [http://localhost:3001](http://localhost:3001) in your browser.

---

## 🐍 Python Analysis Tools

The core statistical logic is written in Python. These scripts generate the data that the backend serves.

### Environment Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Install dependencies: `pip install -r requirements.txt`

### Running Universal Projections
To run a full analysis for a specific league:
```bash
python run_universal.py --league ncaa --mode full --trace
```

---

## 🔍 Troubleshooting

- **Port Conflict**: If port 3000 or 3001 is in use, you can kill existing processes using:
  ```powershell
  Get-Process | Where-Object { $_.ProcessName -match "bun" -or $_.ProcessName -match "node" } | Stop-Process -Force
  ```
- **Missing Data**: Ensure you have a `.env` file in the root directory with the necessary API keys and database credentials if required.
- **Lockfile Warnings**: You may see a warning about multiple lockfiles; this is normal due to the monorepo-style structure.

---

## 📚 Further Reading
- [SCRIPTS.md](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/SCRIPTS.md): Detailed reference for Python scripts.
- [PERFORMANCE_SETUP.md](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/PERFORMANCE_SETUP.md): Optimization tips for high-volume data fetching.
