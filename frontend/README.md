# InvoiceFlow Frontend (POC)

Simple React frontend for the E-Invoice API project.

## Setup

1. Open a terminal in `frontend/`
2. Install dependencies:
   - `npm install`
3. Copy env file:
   - `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`)
4. Update `VITE_API_BASE_URL` in `.env` if your backend is not on localhost

## Run

- Dev server: `npm run dev`
- Production build: `npm run build`
- Preview build: `npm run preview`

## Deploy on Vercel (frontend only)

This app is a static Vite build. The FastAPI backend should run elsewhere (Railway, Render, Fly, etc.); the UI calls it via `VITE_API_BASE_URL`.

1. Import the Git repo in Vercel.
2. Set **Root Directory** to `frontend`.
3. Framework is detected as Vite; build output is `dist` (see `vercel.json` for SPA rewrites so React Router paths work on refresh).
4. In **Project → Settings → Environment Variables**, add `VITE_API_BASE_URL` with your public API base URL (must be `https://` in production).
5. Redeploy after changing env vars.

`vercel.json` rewrites unknown paths to `index.html` so routes like `/invoices` load the app instead of 404.

## Implemented Pages

- Dashboard
- Create Invoice
- Invoice Library
- Invoice Detail
- Transform
- Validate
- Send Invoice

## Known Gaps (Intentional POC/unfinished)

- UI is intentionally simple and not fully polished.
- Mobile responsiveness is basic, not deeply optimized.
- Send flow depends on backend routes (`/send` or `/communicate/send`) that may not exist yet.
- Seller vs buyer data model is adapted in frontend to fit current backend schema (`client_name`, `client_email`).
- Advanced edge-case handling is limited; happy path is prioritized.
