# E-Invoice API — Frontend Build Specification

## Project Overview

This is the frontend for an **E-Invoice API ecosystem** built for small and medium businesses (SMBs). The system handles the full invoice lifecycle: creating UBL 2.1 XML invoices, transforming between formats, validating against compliance rulesets, and sending invoices via email — all without the user needing any XML knowledge.

The frontend is a **proof-of-concept web application** that demonstrates all four API services in a unified interface.

---

## Tech Stack Recommendation

- **Framework**: React (Vite)
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios or native fetch
- **Icons**: Lucide React
- **Routing**: React Router v6
- **Notifications/Toasts**: react-hot-toast
- **File Download**: Native browser API
- **Code/XML Display**: react-syntax-highlighter (optional, for showing XML output)

---

## Design Direction

**Aesthetic**: Clean, professional, utilitarian — but with personality. Think a well-designed SaaS dashboard: dark navy sidebar, white content area, sharp typography, subtle card shadows. Not corporate-bland, not flashy. Functional but polished.

**Fonts**:
- Display/headings: `DM Serif Display` or `Playfair Display`
- Body/UI: `DM Sans` or `Outfit`

**Colour Palette**:
```css
--primary: #1a56db        /* Blue — CTAs, active states */
--primary-dark: #1e429f
--surface: #ffffff
--surface-muted: #f8fafc
--border: #e2e8f0
--text: #0f172a
--text-muted: #64748b
--success: #10b981
--warning: #f59e0b
--error: #ef4444
--sidebar-bg: #0f172a      /* Dark navy sidebar */
--sidebar-text: #cbd5e1
--sidebar-active: #1a56db
```

**Layout**: Fixed left sidebar (240px), main content area scrollable. Top header bar with page title and breadcrumb.

---

## Pages & Routes

| Route | Page Name | Description |
|---|---|---|
| `/` | Dashboard | Overview / landing with pipeline explainer |
| `/create` | Create Invoice | Form to create a new invoice |
| `/invoices` | Invoice Library | List all stored invoices |
| `/invoices/:id` | Invoice Detail | View/download a single invoice |
| `/transform` | Transform | Convert invoice between formats |
| `/validate` | Validate | Upload and validate a UBL XML invoice |
| `/send` | Send Invoice | Email an invoice to a recipient |

---

## API Base URL

```js
const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://your-api.railway.app"
```

Store this in a `.env` file:
```
VITE_API_BASE_URL=https://your-railway-url.up.railway.app
```

---

## Page Specifications

---

### 1. Dashboard (`/`)

**Purpose**: Welcome screen explaining the product and showing system status.

**Layout**:
- Hero section: headline ("Compliant E-Invoicing for Australian SMBs"), subheading, two CTA buttons ("Create Invoice" → `/create`, "View Invoices" → `/invoices`)
- Pipeline diagram: visual 4-step flow showing `Create → Transform → Validate → Send` with icons
- "Quick Actions" cards: 4 cards for each service with short description and a link
- Health status row: shows live status of each service by calling `/health` on each

**API Calls**:
```
GET /health   → show green/red dot for service status
```

**Notes**:
- Health check should auto-run on page load
- Pipeline diagram can be SVG or pure CSS/HTML — no external chart libs needed

---

### 2. Create Invoice (`/create`)

**Purpose**: Fill in invoice details and generate a UBL 2.1 invoice.

**Form Fields**:

**Seller Details**
- Seller Name (text, required)
- Seller Email (email, required)

**Buyer Details**
- Buyer Name (text, required)
- Buyer Email (email, required)

**Invoice Settings**
- Due Date (date picker, required)
- Currency Code (select: AUD, USD, GBP, EUR — default AUD)
- Output Format (select: `ubl_xml`, `json`, `csv`, `pdf`, `generic_xml` — default `ubl_xml`)

**Line Items** (dynamic — start with 1, allow "Add Line Item" button)
Each line item row:
- Description (text)
- Quantity (number, min 1)
- Unit Price (number, min 0)
- Tax % (number, default 10)
- [Delete row button] — disabled if only 1 row

Auto-calculated display (read-only):
- Line Total = Quantity × Unit Price
- Invoice Total (sum of all line totals + tax)

**Submit Button**: "Generate Invoice"

**On Success**:
- Show a success banner with the returned Invoice ID
- Display the output (XML/JSON rendered in a code block, or PDF download link, or CSV download)
- Show buttons: "View All Invoices", "Validate this Invoice", "Send this Invoice"

**API Call**:
```
POST /invoices
Body: {
  seller_name, seller_email,
  buyer_name, buyer_email,
  due_date,
  currency_code,
  tax_percentage,         // from first line item or global
  line_items: [{ description, quantity, unit_price, tax_percentage }],
  format                  // query param or body field — check your API
}
```

**Error Handling**:
- Show inline validation for empty required fields before submit
- Show API error message in a red banner if the request fails

---

### 3. Invoice Library (`/invoices`)

**Purpose**: Browse all stored invoices.

**Layout**:
- Search bar (filter by ID or buyer/seller name client-side)
- Table or card grid of invoices with columns:
  - Invoice ID
  - Buyer Name
  - Seller Name
  - Due Date
  - Total Amount
  - Actions: [View] [Delete]
- Empty state illustration if no invoices

**API Calls**:
```
GET /invoices              → list all invoices
DELETE /invoices/{id}      → delete an invoice (with confirm dialog)
```

**Notes**:
- Clicking a row or "View" navigates to `/invoices/:id`
- Delete should ask for confirmation before calling the API
- Show a loading skeleton while fetching

---

### 4. Invoice Detail (`/invoices/:id`)

**Purpose**: View a specific invoice and download in multiple formats.

**Layout**:
- Invoice summary card (buyer, seller, due date, total, currency)
- Line items table (description, qty, unit price, tax, line total)
- Download section: format selector dropdown + "Download" button
- Action buttons: "Validate", "Send", "Edit", "Delete"

**API Calls**:
```
GET /invoices/{id}?format=ubl_xml    → get invoice in chosen format
PUT /invoices/{id}                   → update invoice (opens edit modal)
DELETE /invoices/{id}                → delete invoice
```

**Edit Modal**:
- Pre-filled with current invoice data
- Same fields as the Create form (simplified — no line item add/remove needed)
- On save: PATCH/PUT the invoice and refresh

**Download Logic**:
- For XML/JSON: open in new tab or trigger browser download via Blob
- For PDF: trigger download
- For CSV: trigger download

---

### 5. Transform (`/transform`)

**Purpose**: Upload an invoice file and convert it to another format.

**Layout**:
- Two dropdowns side by side: "Input Format" and "Output Format"
  - Supported inputs: `json`, `csv`, `ubl_xml`
  - Supported outputs: `ubl_xml`, `json`, `csv`, `pdf`
- File upload area (drag-and-drop style) OR text area for paste
  - If JSON or XML selected as input: show a textarea for paste
  - If CSV selected: show file upload
- "Convert" button
- Result area: show output in code block (XML/JSON/CSV) or download button (PDF)

**API Calls**:
```
GET /transform/formats         → populate the dropdown options dynamically
POST /transform                → send { input_format, output_format, content/file }
```

**Notes**:
- Fetch supported formats on page load from `/transform/formats`
- Disable incompatible output formats based on selected input
- Show a loading spinner during conversion

---

### 6. Validate (`/validate`)

**Purpose**: Upload a UBL XML invoice and get a validation report.

**Layout**:
- Ruleset selector (radio buttons or tabs): `ubl` | `peppol` | `australian`
  - Short description under each option explaining what it checks
- XML input area: textarea for paste OR file upload (`.xml`)
- "Validate" button
- Results panel (shown after submit):
  - Big status badge: ✅ VALID or ❌ INVALID
  - Summary: "X errors found, Y warnings"
  - Results table:
    - Columns: Rule ID | Severity | Description
    - Severity badge: red for Critical, yellow for Warning
  - Expandable "Raw Response" section (JSON toggle)

**API Calls**:
```
GET /validate/rulesets          → populate ruleset options with descriptions
POST /validate?ruleset=ubl      → { xml_content: "..." }
```

**Notes**:
- Fetch rulesets on page load
- Colour-code the results table rows by severity
- If valid, show a green "All checks passed" message instead of an empty table

---

### 7. Send Invoice (`/send`)

**Purpose**: Email a UBL XML invoice to a recipient.

**Layout**:
- Option A: Select from stored invoices (dropdown populated from `/invoices`)
- Option B: Paste raw UBL XML directly (toggle/tab)
- Recipient Email (text, required)
- Sender Name (text, optional)
- Subject Line (text, optional, placeholder: "Invoice from [Seller Name]")
- Message Body (textarea, optional)
- "Send Invoice" button

**On Success**:
- Show confirmation card with:
  - ✅ Sent successfully
  - Recipient email
  - Invoice ID
  - Timestamp

**API Call**:
```
POST /send   (or /communicate/send — check your API route)
Body: {
  xml_content,        // UBL XML string
  recipient_email,
  sender_name,
  subject,
  message_body
}
```

**Notes**:
- Validate email format client-side before submitting
- Show clear error if the email send fails

---

## Shared Components

### Sidebar Navigation
```
Logo: "InvoiceFlow" (or your team's product name)
Nav items (with icons):
  - Dashboard         (LayoutDashboard icon)
  - Create Invoice    (FilePlus icon)
  - Invoice Library   (FileText icon)
  - Transform         (ArrowLeftRight icon)
  - Validate          (ShieldCheck icon)
  - Send Invoice      (Send icon)
```

Active state: highlight with `--primary` colour and left border indicator.

### Top Header Bar
- Page title (dynamic, based on current route)
- Optional: breadcrumb (e.g. "Invoices / INV-0042")

### Toast Notifications
Use `react-hot-toast` for:
- ✅ Success: "Invoice created successfully"
- ❌ Error: "Failed to connect to API — check your configuration"

### Loading States
- Button spinners during API calls (disable button while loading)
- Skeleton loaders for tables (3 placeholder rows)

### Empty States
- Show a helpful message + icon when tables are empty
- e.g. "No invoices yet — create your first one"

### Error Boundary / API Error Banner
If the API base URL is not configured or returns 5xx:
- Show a yellow warning banner at the top of the page
- "Could not reach the API. Check your VITE_API_BASE_URL setting."

---

## File Structure

```
src/
├── api/
│   └── client.js              # Axios instance + base URL config
├── components/
│   ├── Sidebar.jsx
│   ├── Header.jsx
│   ├── LineItemRow.jsx
│   ├── InvoiceTable.jsx
│   ├── ValidationResults.jsx
│   ├── FormatDownloader.jsx
│   └── StatusBadge.jsx
├── pages/
│   ├── Dashboard.jsx
│   ├── CreateInvoice.jsx
│   ├── InvoiceLibrary.jsx
│   ├── InvoiceDetail.jsx
│   ├── Transform.jsx
│   ├── Validate.jsx
│   └── SendInvoice.jsx
├── App.jsx                    # Router setup
├── main.jsx
└── index.css                  # Tailwind imports + CSS variables
```

---

## API Client Setup (`src/api/client.js`)

```js
import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// If your API requires an API key:
// client.defaults.headers.common['X-API-Key'] = import.meta.env.VITE_API_KEY;

export default client;
```

---

## Environment Variables (`.env.example`)

```
VITE_API_BASE_URL=https://your-api.railway.app
# VITE_API_KEY=your-api-key-here   # uncomment if auth is required
```

---

## Key UX Notes

1. **The Create Invoice page is the most important** — make sure the dynamic line items work cleanly and totals update in real time.
2. **Validate page should feel like a proper report** — not just raw JSON. Table format with coloured severity badges is important.
3. **Transform page** needs clear feedback when formats are incompatible.
4. **All forms** should have client-side validation that gives feedback before hitting the API.
5. **Don't block the UI** — always show loading state while API calls are in flight.

---

## Notes for Cursor

- This is a **proof-of-concept** — full error handling for every edge case is not required, but the happy path must work end-to-end.
- The API is a FastAPI backend deployed on Railway. Endpoints follow REST conventions.
- Check the actual API's Swagger docs for exact request/response shapes before wiring up each page — field names may differ slightly from what's described here.
- The API may require authentication via an API key header (see NFR8). If so, add it to the Axios client.
- For PDF output, the API returns a binary file — handle with `responseType: 'blob'` in Axios and use `URL.createObjectURL` for download.
- For XML/text output, the API likely returns `Content-Type: application/xml` or `text/plain` — read as text and display in a `<pre>` block.