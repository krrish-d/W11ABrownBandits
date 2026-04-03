import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import client, { formatApiError } from "../api/client";
import FormatDownloader from "../components/FormatDownloader";

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState({ client_name: "", client_email: "", due_date: "", currency: "AUD", notes: "" });

  const fetchInvoice = async () => {
    try {
      setLoading(true);
      const { data } = await client.get(`/invoices/${id}`);
      setInvoice(data);
      setEditData({
        client_name: data.client_name || "",
        client_email: data.client_email || "",
        due_date: data.due_date || "",
        currency: data.currency || "AUD",
        notes: data.notes || "",
      });
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoice();
  }, [id]);

  const deleteInvoice = async () => {
    if (!window.confirm("Delete this invoice?")) return;
    try {
      await client.delete(`/invoices/${id}`);
      toast.success("Invoice deleted");
      navigate("/invoices");
    } catch (error) {
      toast.error(formatApiError(error));
    }
  };

  const updateInvoice = async () => {
    try {
      await client.put(`/invoices/${id}`, editData);
      toast.success("Invoice updated");
      setEditOpen(false);
      fetchInvoice();
    } catch (error) {
      toast.error(formatApiError(error));
    }
  };

  if (loading) return <div className="card">Loading invoice...</div>;
  if (!invoice) return <div className="card">Invoice not found.</div>;

  return (
    <div className="stack">
      <section className="card">
        <h3>{invoice.invoice_number}</h3>
        <p>Buyer: {invoice.client_name} ({invoice.client_email})</p>
        <p>Due: {invoice.due_date}</p>
        <p>Total: {invoice.currency} {Number(invoice.grand_total).toFixed(2)}</p>
      </section>

      <section className="card table-wrap">
        <h3>Line Items</h3>
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Tax</th>
              <th>Line Total</th>
            </tr>
          </thead>
          <tbody>
            {(invoice.items || []).map((item) => (
              <tr key={item.item_id}>
                <td>{item.description}</td>
                <td>{item.quantity}</td>
                <td>{invoice.currency} {Number(item.unit_price).toFixed(2)}</td>
                <td>{item.tax_rate}%</td>
                <td>{invoice.currency} {Number(item.line_total).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card stack">
        <h3>Download / Preview</h3>
        <FormatDownloader invoiceId={id} />
      </section>

      <section className="card inline-row">
        <button className="btn btn-ghost" onClick={() => navigate("/validate")}>Validate</button>
        <button className="btn btn-ghost" onClick={() => navigate("/send")}>Send</button>
        <button className="btn btn-ghost" onClick={() => setEditOpen(true)}>Edit</button>
        <button className="btn btn-danger" onClick={deleteInvoice}>Delete</button>
      </section>

      {editOpen ? (
        <section className="card stack">
          <h3>Edit Invoice</h3>
          <div className="grid-2">
            <div>
              <label>Buyer Name</label>
              <input value={editData.client_name} onChange={(e) => setEditData((p) => ({ ...p, client_name: e.target.value }))} />
            </div>
            <div>
              <label>Buyer Email</label>
              <input value={editData.client_email} onChange={(e) => setEditData((p) => ({ ...p, client_email: e.target.value }))} />
            </div>
            <div>
              <label>Due Date</label>
              <input type="date" value={editData.due_date} onChange={(e) => setEditData((p) => ({ ...p, due_date: e.target.value }))} />
            </div>
            <div>
              <label>Currency</label>
              <select value={editData.currency} onChange={(e) => setEditData((p) => ({ ...p, currency: e.target.value }))}>
                {["AUD", "USD", "GBP", "EUR"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label>Notes</label>
            <textarea value={editData.notes} onChange={(e) => setEditData((p) => ({ ...p, notes: e.target.value }))} />
          </div>
          <div className="inline-row">
            <button className="btn" onClick={updateInvoice}>Save</button>
            <button className="btn btn-ghost" onClick={() => setEditOpen(false)}>Cancel</button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
