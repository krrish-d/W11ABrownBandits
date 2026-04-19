# InvoiceFlow Frontend (Next.js)

Modern Next.js App Router frontend for the E-Invoice API.

## Setup

1. Open terminal in `frontend/`
2. Install packages: `npm install`
3. Copy env file:
   - PowerShell: `Copy-Item .env.example .env`
4. Set API URL in `.env`:
   - `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`

## Run

- Dev: `npm run dev`
- Build: `npm run build`
- Start: `npm run start`
- Lint: `npm run lint`

## Features

- Dashboard with live invoice stats
- Searchable/filterable invoice list
- Invoice detail with send/reminder panel and comms log view
- Compose/edit invoice form with RHF + Zod validation and live email preview

## Deploy (Vercel)

1. Import repo in Vercel
2. Set project root directory to `frontend`
3. Add env var: `NEXT_PUBLIC_API_BASE_URL` with your production API base root (`https://api.example.com`)
4. Deploy

This frontend expects the FastAPI backend to be hosted separately.
