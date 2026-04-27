# InvoiceFlow Frontend Build Specification

## Project Overview

InvoiceFlow is the current Next.js frontend for an authenticated invoice management platform aimed at Australian SMB users. The application now covers the full operational workflow around invoices: composing, importing, listing, transforming, validating, sending, tracking payments, managing clients, defining recurring rules, maintaining templates, reviewing analytics, and checking audit history.

The current sprint expands the earlier proof of concept into a broader SaaS-style dashboard. Instead of focusing only on the four original services, the frontend now acts as a central business console for invoice lifecycle management and compliance-focused operations.

## Tech Stack

- Framework: Next.js App Router
- Styling: Tailwind CSS with shared UI components
- Forms: React Hook Form and Zod on the compose page
- HTTP Client: Axios and native fetch
- Charts: Recharts for analytics visualisation
- Icons: Lucide React
- Authentication: token stored in localStorage and cookie, with route guarding in the app shell

## Shared Layout

Elements:

- Responsive application shell with the InvoiceFlow brand and subtitle "Clean invoicing with modern automation"
- Desktop sidebar navigation with links for Dashboard, Invoices, Compose, Clients, Analytics, Payments, Transform, Validate, Templates, Recurring, and Audit
- Mobile top navigation with horizontally scrollable route links
- Active navigation state shown with highlighted styling based on the current route
- Theme switcher in the desktop sidebar
- Login and Logout controls depending on authentication state
- Session check before protected pages render, redirecting unauthenticated users to Login

Reasoning:

The shared layout establishes InvoiceFlow as a single authenticated workspace rather than a collection of disconnected service demos. Keeping the navigation persistent gives SMB users fast access to daily workflows such as creating invoices, checking payments, and reviewing clients, while also exposing more administrative tools like audit logs and recurring rules without hiding them in secondary menus.

The authentication gate is important because invoices, client records, payments, and audit data are business-sensitive. The responsive navigation keeps the interface practical across desktop and smaller screens, while the active route styling helps users stay oriented as they move between closely related invoice tasks.

## Pages

Dashboard:

Elements:

- Sidebar navigation with "Dashboard" highlighted as active
- Page heading "Dashboard" with a personalised welcome message when user details are available
- "New Invoice" primary CTA linking to the Compose page
- Four KPI cards showing Total, Pending, Paid, and Overdue invoice counts
- Financial KPI row showing Total invoiced, Paid this month, and Outstanding balance
- "Validation & transformation" card with quick links to Transform and Validate
- "Needs attention" section showing overdue invoices and invoices due within 7 days
- "Recent invoices" section showing the latest five invoice records with links to invoice details
- Loading skeletons and empty states for invoice data

Reasoning:

The Dashboard now acts as an operational overview rather than only a welcome page. It gives users an immediate view of invoice volume, payment status, outstanding money, and urgent follow-up items, which is more useful for a working SMB than a static product explanation.

The quick links to Transform and Validate preserve the compliance workflow from the previous sprint, while the needs-attention list makes the page action-oriented. Users can quickly spot overdue or due-soon invoices, open a recent record, or start a new invoice from a single central hub.

Login:

Elements:

- Public route outside the protected app workflow
- Card-based login form with Email and Password fields
- Toggle between Login and Create account modes
- Sign up mode adds a Full name field
- Primary submit button that changes between "Login" and "Sign up"
- Loading state displaying "Please wait..."
- Inline error message for failed authentication or signup
- Successful authentication redirects users to the Dashboard

Reasoning:

The Login page supports both returning users and first-time users in a compact interface. Combining login and signup into one card reduces friction for demonstration and testing while still supporting the authenticated data model used by the rest of the app.

Because the main application contains sensitive invoice and client information, the login page is the required entry point for all protected workflows. The simple card layout keeps the authentication step focused and avoids distracting users before they reach the business dashboard.

Compose Invoice:

Elements:

- Sidebar navigation with "Compose" highlighted as active
- Page card titled "Compose invoice" for new invoices or "Edit invoice" when opened with an invoice ID
- Import from file bar accepting JSON, CSV, XML, and PDF files to pre-fill invoice fields
- Client profile dropdown for loading saved buyer details
- Template dropdown for applying saved payment terms into notes
- Two-column seller and buyer input layout including name, email, and address fields
- Issue Date and Due Date date picker fields
- Currency dropdown supporting AUD, USD, GBP, and EUR, defaulting to AUD
- Notes textarea for invoice comments or payment terms
- Dynamic line item rows with Description, Quantity, Unit Price, Tax %, calculated Total, and Remove action
- "Add Line" button for additional invoice rows
- Download format dropdown for JSON, PDF, CSV, XML, and UBL XML
- Primary action button labelled "Create invoice" or "Save changes"
- Success or error message below the form
- Send to client section after invoice creation with recipient email and "Send email" action
- Live email preview card showing seller, buyer, line items, subtotal, tax total, grand total, and due date

Reasoning:

The Compose page is now the main invoice creation and editing workspace. It keeps the original structured invoice data entry flow, but adds current sprint features that make the form more practical for repeated business use: client profiles, reusable templates, file import, live preview, editable invoices, and immediate email sending after creation.

The two-column form layout keeps seller and buyer details scannable, while the dynamic line item section supports the variable number of products or services common in SMB invoicing. The live preview gives users confidence before saving or sending, and the export format selector keeps the page connected to the broader transformation and compliance requirements of the system.

Invoice Library:

Elements:

- Sidebar navigation with "Invoices" highlighted as active
- Page heading "Invoices" with subtitle "Search, filter and inspect all invoice records."
- "Import from file" button accepting JSON, CSV, XML, and PDF, then redirecting to Compose with parsed data
- "New invoice" CTA linking to Compose
- Search input with placeholder "Search by number, client, or email"
- Status filter dropdown with All statuses, Draft, Sent, Viewed, Paid, Overdue, and Cancelled
- Sort field dropdown for Newest, Due date, Amount, and Client
- Sort order dropdown for Desc and Asc
- Invoice list cards showing invoice number, buyer or client name, buyer or client email, total amount, and status badge
- Per-invoice action buttons for Transform, Validate, Send, and Delete
- Inline send row with recipient email, Send email, Cancel, and result message
- Confirm delete state before removing an invoice
- Loading, empty, and error states

Reasoning:

The Invoice Library has evolved from a simple table into a management surface for the whole invoice lifecycle. Search, status filtering, and sorting help users find records quickly as invoice volume grows, while the card layout gives each record enough space for workflow actions without requiring immediate navigation to a detail page.

Placing Transform, Validate, Send, and Delete directly on each invoice supports experienced users who want to perform quick actions from the list. The confirmation step for deletion reduces risk, and the import function supports migration or reuse of invoice data from external formats.

Invoice Detail:

Elements:

- Dynamic route for viewing a single invoice by ID
- Invoice summary card showing invoice number, status badge, client name, email, due date, subtotal, grand total, and outstanding balance
- Lifecycle status controls for Draft, Sent, Viewed, Paid, Overdue, and Cancelled
- Line items section showing description, quantity, unit price, and line total
- Payment tracking section with Amount, Method, Payment Date, and Reference fields
- Payment method dropdown including bank_transfer, credit_card, cash, xero, and other
- "Record payment" primary action
- Existing payment entries shown with amount, method, reference, and date
- Send & reminders card with recipient email input
- "Send Invoice Email" and "Send Reminder" actions
- Communication log showing recipient, sent time, and delivery status
- "Edit invoice" button linking back to Compose in edit mode
- Loading, missing invoice, action message, and error states

Reasoning:

The Invoice Detail page is the operational control centre for a single invoice. It brings together the record itself, lifecycle status, payment tracking, communication history, reminder sending, and edit access, which means users can manage follow-up without jumping between unrelated pages.

This page is especially important for cash-flow management. SMB users often need to know whether an invoice has been sent, viewed, paid, partially paid, or overdue, and they need a simple way to record payments or send reminders. The detail view supports that real-world workflow directly.

Clients:

Elements:

- Sidebar navigation with "Clients" highlighted as active
- Page heading "Clients" with subtitle about reusable client profiles
- Summary cards showing Total clients and With tax ID
- Add client form with Name, Email, Address, Tax ID, Currency, Payment Terms, and Internal Notes
- Currency dropdown supporting AUD, USD, GBP, and EUR, defaulting to AUD
- Payment terms number input defaulting to 30 days
- "Save client" primary action
- Client library section with search by name or email
- Client cards showing name, email, and address
- Loading, empty, success, and error message states

Reasoning:

The Clients page reduces repeated data entry by letting users store common buyer information once and reuse it on the Compose page. This is particularly useful for SMB users with recurring customers, because it helps keep email addresses, payment terms, currencies, and tax identifiers consistent across invoices.

The summary cards give a quick sense of client library completeness, especially whether tax IDs are present. The page is intentionally simple because its main purpose is to make invoice creation faster and less error-prone.

Analytics:

Elements:

- Sidebar navigation with "Analytics" highlighted as active
- Page heading "Analytics" with subtitle "Revenue trends and client performance."
- KPI cards for Total Invoiced (all time), Paid This Month, and Overdue Amount
- Monthly trend bar chart comparing Invoiced, Paid, and Overdue values
- Empty state when no trend data exists
- Top clients table with Client, Invoiced, Paid, and Outstanding columns
- Error message if dashboard analytics data cannot be fetched

Reasoning:

The Analytics page gives business users a higher-level view of invoice performance. The KPI cards summarise the most important revenue figures, while the monthly trend chart makes it easier to see whether invoicing, payments, and overdue amounts are improving or worsening over time.

The top clients table supports practical decision-making by identifying which customers contribute the most revenue and which have outstanding balances. This makes the frontend more useful as a business management tool, not only an invoice generation interface.

Payments:

Elements:

- Sidebar navigation with "Payments" highlighted as active
- Page heading "Payments" with subtitle about tracking paid amounts and outstanding balances
- Invoice selector dropdown populated from invoice records
- Payment summary card showing Total, Paid, and Outstanding amounts for the selected invoice
- Payment history list showing amount, payment method, payment date, and reference
- Empty state when no summary or payment entries exist
- Link to open the selected invoice detail page to record a payment
- Error state for failed invoice or payment summary fetches

Reasoning:

The Payments page gives users a dedicated view for reviewing payment status without opening every invoice individually. It is designed as a lightweight payment monitoring page, while the actual payment recording remains on the Invoice Detail page where the full invoice context is available.

This separation keeps the workflow clear: Payments is for overview and lookup, Invoice Detail is for action. For SMB users, this makes it quicker to check outstanding balances and then jump to the exact invoice when a payment needs to be recorded.

Transform:

Elements:

- Sidebar navigation with "Transform" highlighted as active
- Page heading "Transform" with subtitle about converting between JSON, XML, UBL, CSV, and PDF
- Optional invoice preloading when opened with an invoice ID from the invoice list
- Input format dropdown supporting json, csv, xml, ubl_xml, and pdf
- Output format dropdown supporting json, csv, xml, ubl_xml, and pdf
- XML output type dropdown with ubl and generic options
- File upload input for all formats, with PDF handled as a required file input when selected
- Large Invoice data textarea for non-PDF input, populated by uploaded file text where possible
- "Transform invoice" primary action and secondary Clear action
- Automatic file download for PDF, CSV, XML, and UBL XML outputs
- Inline JSON result textarea when JSON is selected as output
- Result card for downloaded outputs, including "Validate this XML" for XML and UBL XML results
- Error card for transformation failures

Reasoning:

The Transform page has been expanded from a paste-only converter into a more complete interoperability tool. Users can now transform uploaded files or pasted content, preload invoices from the library, and download non-JSON outputs automatically, which better reflects the practical ways invoice data moves between systems.

The page keeps the conversion controls at the top and the invoice content area as the dominant input. Offering a direct validation link after XML output supports the end-to-end compliance flow, where users often need to convert an invoice and immediately check it against UBL, PEPPOL, or Australian rules.

Validate:

Elements:

- Sidebar navigation with "Validate" highlighted as active
- Page heading "Validate" with subtitle about UBL, PEPPOL, and Australian rules
- Validation tool card with Source dropdown
- Source options for Paste XML, Upload XML file, and Select invoice from library
- Ruleset dropdown with ubl, peppol, and australian options
- XML file upload input when upload mode is selected
- Invoice library dropdown when library mode is selected
- Large Invoice XML textarea for pasted, uploaded, or loaded XML
- "Validate invoice" primary action and secondary Clear action
- Validation result card showing ruleset and Valid or Invalid status
- Validation issue cards showing rule, severity, and description
- Empty success state reading "No errors found."
- Error card for failed validation or unreadable XML input

Reasoning:

The Validate page now supports three realistic input paths: pasting XML, uploading a saved file, or selecting an invoice already stored in the library. This flexibility is useful because compliance checks can happen at different points in the workflow, either before sending, after transformation, or when reviewing stored invoices.

The ruleset dropdown keeps the compliance model clear and progressive. Users can choose broad UBL checks, PEPPOL requirements, or Australian-specific validation depending on their target workflow. The result card makes validation output easy to scan by separating each issue into a readable block.

Templates:

Elements:

- Sidebar navigation with "Templates" highlighted as active
- Page heading "Templates" with subtitle about invoice branding templates
- Create template form with Basic info, Branding colours, and Invoice content sections
- Required Template name field
- "Set as default template" checkbox
- Primary colour picker with hex input and preview dot
- Secondary colour picker with hex input and preview dot
- Footer text textarea
- Payment terms textarea
- Bank details textarea
- "Save template" primary action with saving state
- Template library listing saved templates
- Default badge for the default template
- Colour previews for primary and secondary template colours
- Optional footer preview text in each template card
- Loading, empty, success, and error states

Reasoning:

The Templates page helps businesses standardise invoice presentation and payment language. Branding colours, footer copy, payment terms, and bank details are details that usually remain consistent across invoices, so storing them as templates reduces repetition and helps invoices look more professional.

The page also improves the Compose workflow because templates can be applied while creating an invoice. This connects branding and operational invoice creation without forcing users to manually re-enter standard payment terms each time.

Recurring:

Elements:

- Sidebar navigation with "Recurring" highlighted as active
- Page heading "Recurring" with subtitle about auto-generating invoices on a schedule
- Create recurring rule form with Rule name, Frequency, Next run date, and End date
- Frequency dropdown supporting daily, weekly, biweekly, monthly, quarterly, and annually
- Seller and buyer invoice template fields for name, email, and address
- Due date date picker and Currency dropdown
- Notes textarea
- Dynamic line item rows with Description, Quantity, Unit Price, Tax %, calculated Total, and Remove action
- "Add line item" secondary action
- "Save recurring rule" primary action
- Recurring rules library listing rule name, next run date, frequency, and active or paused state
- Delete action for existing recurring rules
- Loading, empty, success, and error message states

Reasoning:

The Recurring page supports invoices that need to be generated repeatedly, such as monthly retainers or regular service agreements. By capturing both schedule information and the invoice template in one form, the page lets users define the business rule and the invoice contents together.

This is valuable for SMB users because recurring billing is easy to forget when handled manually. The rules library also gives visibility into which recurring invoices are active, when they will next run, and how often they repeat.

Audit:

Elements:

- Sidebar navigation with "Audit" highlighted as active
- Page heading "Audit" with subtitle about tracking create, update, and delete events
- Filter audit logs card with Entity type input
- Action input for values such as create, update, and delete
- "Apply filters" button
- Audit log entries card listing returned events
- Each audit entry shows entity type, action, entity ID, changed by, and timestamp
- Loading state while logs are fetched
- Empty state when no audit logs are returned
- Error message for failed audit log requests

Reasoning:

The Audit page adds operational transparency to the application. For a compliance-focused invoice system, users need to understand when records, templates, and recurring rules were created, updated, or deleted, especially if multiple users or automated processes can affect the same business data.

Filtering by entity type and action keeps the page useful as audit volume grows. The page is intentionally record-focused, presenting each event clearly so users can investigate changes without needing to inspect backend logs directly.