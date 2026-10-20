# LinkPulse + LinkGuard — Error 404
React + Tailwind, Flask and PostgreSQL (SQLite fallback locally).

## Features
- Create short links, custom aliases, campaigns, expiry and click limits
- Redirect validation and persisted click events
- Real click analytics, device/browser/referrer breakdown, weekly chart
- Pause/resume, QR download, CSV export, search/filter
- LinkGuard transparent heuristics for traffic bursts and bot-like user agents
- Responsive dashboard

## Local run
Backend:
```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```
Frontend in another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open the Vite URL. Backend runs on port 5000.

`DATABASE_URL` may be left blank for local SQLite. For deployment set it to a PostgreSQL connection URL. Never commit `.env`.

## Deploy
Backend: Render, root directory `backend`, build `pip install -r requirements.txt`, start `gunicorn app:app`.
Set `DATABASE_URL`, `BASE_URL` (public backend URL), `FRONTEND_URL`.
Frontend: Vercel, root directory `frontend`, build `npm run build`, output `dist`. Set `VITE_API_BASE` to backend URL. CORS is open for demo; restrict origins before production.

## Demo
Create a short link, open it a few times in another tab, refresh analytics, test expiry/click limit, and show LinkGuard signals. Heuristics are explainable flags, not proof of malicious activity. No fake click numbers are used.

Team Error 404: Dhruv Vats, Isha, Krish Kulshrestha, Kushagra Agarwal — Graphic Era Hill University, Dehradun.
