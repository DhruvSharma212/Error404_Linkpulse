# LinkPulse + LinkGuard — Team Error 404

**A smart URL shortening and link intelligence platform built for INNOVISTA 2026.**

🌐 **Live Demo:** https://error404-linkpulse.vercel.app  
💻 **GitHub Repository:** https://github.com/DhruvSharma212/Error404_Linkpulse

## Problem Statement

Long URLs are difficult to share, manage, and track. Basic URL shorteners may provide limited insights into click activity and may not clearly flag suspicious traffic patterns.

## Our Solution

LinkPulse makes URL management easier by generating short links and providing click analytics. LinkGuard adds explainable heuristic signals to highlight unusual traffic patterns, helping users investigate potentially suspicious activity.

These signals are indicators for investigation, not proof of malicious behaviour.

## Features

- Create short links with custom aliases.
- Configure campaigns, expiry dates, and click limits.
- Validate redirects and persist click events.
- View click analytics, including device, browser, and referrer breakdowns.
- Visualize weekly click activity.
- Pause and resume links.
- Download QR codes and export click data as CSV.
- Search and filter links.
- Identify traffic bursts and bot-like user agents using LinkGuard heuristics.
- Responsive dashboard.

## Tech Stack

- **Frontend:** React, Tailwind CSS, Vite
- **Backend:** Python, Flask
- **Database:** PostgreSQL (Neon for deployment, SQLite fallback locally)
- **Frontend Hosting:** Vercel
- **Backend Hosting:** Render

## Live Demo

Visit: https://error404-linkpulse.vercel.app

Suggested demo flow:

1. Sign up or log in.
2. Create a short URL.
3. Open the generated link to test redirection.
4. Refresh analytics and inspect click activity.
5. Demonstrate available LinkGuard traffic signals.

Only demonstrate features that have been tested successfully.

## Screenshots

Add actual screenshots of your running application here.

Suggested screenshots:
- Login / Signup
- Main Dashboard
- Short Link Creation
- Click Analytics
- LinkGuard Traffic Signals

Example Markdown after uploading an image to the repository:

`![LinkPulse Dashboard](screenshots/dashboard.png)`

## Local Setup Instructions

### Prerequisites

- Python
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/DhruvSharma212/Error404_Linkpulse.git
cd Error404_Linkpulse
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies and configure the environment:

```bash
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Configure `DATABASE_URL` in `.env` if using PostgreSQL. Leave it blank only if the application's SQLite fallback is configured and supported.

The backend runs on port `5000`, according to the current project configuration.

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal.

Configure `VITE_API_BASE` if the frontend requires a custom backend API URL.

## Deployment

### Backend — Render

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Configure the required environment variables using the names expected by the backend code. Never commit their secret values.

### Frontend — Vercel

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Configure `VITE_API_BASE` with the deployed backend URL.

Restrict CORS to trusted origins before production use.

## Security Notes

- Never commit `.env` files, database credentials, or secret keys.
- LinkGuard heuristic signals are not definitive proof of malicious activity.
- Review redirect validation and access controls before production use.

## Team

**Team Name:** Error 404  
**Institution:** Graphic Era Hill University, Dehradun

- Dhruv Vats
- Isha
- Krish Kulshrestha
- Kushagra Agarwal

## Demo Testing

- Create a short link and test redirection.
- Open it multiple times and inspect click analytics.
- Test expiry and click limits.
- Review LinkGuard signals using available test scenarios.

No fabricated click numbers are used.
