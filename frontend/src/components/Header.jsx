const routeTitles = {
  "/": "Dashboard",
  "/create": "Create Invoice",
  "/invoices": "Invoice Library",
  "/transform": "Transform",
  "/validate": "Validate",
  "/send": "Send Invoice",
};

export default function Header({ pathname }) {
  const isInvoiceDetail = pathname.startsWith("/invoices/") && pathname !== "/invoices";
  const title = isInvoiceDetail ? "Invoice Detail" : routeTitles[pathname] || "InvoiceFlow";
  const crumb = isInvoiceDetail ? `Invoices / ${pathname.split("/")[2]}` : title;

  return (
    <header className="top-header">
      <div>
        <p className="breadcrumb">{crumb}</p>
        <h1 className="page-title">{title}</h1>
      </div>
    </header>
  );
}
