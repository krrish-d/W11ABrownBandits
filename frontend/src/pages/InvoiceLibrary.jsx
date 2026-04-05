import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import client, { formatApiError } from "../api/client";
import InvoiceTable from "../components/InvoiceTable";

export default function InvoiceLibrary() {
  const [invoices, setInvoices] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const { data } = await client.get("/invoice/list");
      setInvoices(data);
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return invoices;
    return invoices.filter((invoice) =>
      [invoice.invoice_id, invoice.invoice_number, invoice.client_name, invoice.client_email]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query))
    );
  }, [invoices, search]);

  const deleteInvoice = async (invoice) => {
    const ok = window.confirm(`Delete invoice ${invoice.invoice_number || invoice.invoice_id}?`);
    if (!ok) return;

    try {
      await client.delete(`/invoice/delete/${invoice.invoice_id}`);
      toast.success("Invoice deleted");
      setInvoices((prev) => prev.filter((i) => i.invoice_id !== invoice.invoice_id));
    } catch (error) {
      toast.error(formatApiError(error));
    }
  };

  return (
    <div className="stack">
      <section className="card">
        <input
          placeholder="Search by ID, buyer or email"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </section>
      <InvoiceTable invoices={filtered} loading={loading} onDelete={deleteInvoice} />
    </div>
  );
}
