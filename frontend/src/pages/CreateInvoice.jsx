import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import client, { createBlobUrl, formatApiError } from "../api/client";
import LineItemRow from "../components/LineItemRow";

const emptyLine = { description: "", quantity: 1, unit_price: 0, tax_rate: 10 };
const formatMap = { ubl_xml: "ubl", generic_xml: "xml", json: "json", csv: "csv", pdf: "pdf" };

export default function CreateInvoice() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    sellerName: "",
    sellerEmail: "",
    buyerName: "",
    buyerEmail: "",
    dueDate: "",
    currency: "AUD",
    outputFormat: "ubl_xml",
    lineItems: [{ ...emptyLine }],
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState(null);
  const [output, setOutput] = useState("");

  const totals = useMemo(() => {
    const subtotal = form.lineItems.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0);
    const totalTax = form.lineItems.reduce(
      (sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0) * (Number(item.tax_rate || 0) / 100),
      0
    );
    return { subtotal, totalTax, grandTotal: subtotal + totalTax };
  }, [form.lineItems]);

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const updateLine = (index, key, value) => {
    setForm((prev) => {
      const next = [...prev.lineItems];
      next[index] = { ...next[index], [key]: value };
      return { ...prev, lineItems: next };
    });
  };

  const addLine = () => setForm((prev) => ({ ...prev, lineItems: [...prev.lineItems, { ...emptyLine }] }));
  const removeLine = (index) =>
    setForm((prev) => ({ ...prev, lineItems: prev.lineItems.filter((_, i) => i !== index) }));

  const validate = () => {
    const nextErrors = {};
    if (!form.sellerName.trim()) nextErrors.sellerName = "Required";
    if (!form.sellerEmail.trim()) nextErrors.sellerEmail = "Required";
    if (!form.buyerName.trim()) nextErrors.buyerName = "Required";
    if (!form.buyerEmail.trim()) nextErrors.buyerEmail = "Required";
    if (!form.dueDate) nextErrors.dueDate = "Required";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const fetchOutput = async (invoiceId, outputFormat) => {
    const apiFormat = formatMap[outputFormat] || "json";
    if (apiFormat === "pdf") {
      const res = await client.get(`/invoice/fetch/${invoiceId}?format=pdf`, { responseType: "blob" });
      const url = createBlobUrl(res.data, "application/pdf");
      setOutput(`PDF ready: ${url}`);
      return;
    }
    if (apiFormat === "csv") {
      const res = await client.get(`/invoice/fetch/${invoiceId}?format=csv`, { responseType: "text" });
      setOutput(res.data);
      return;
    }
    const res = await client.get(`/invoice/fetch/${invoiceId}?format=${apiFormat}`, {
      responseType: apiFormat === "json" ? "json" : "text",
    });
    setOutput(apiFormat === "json" ? JSON.stringify(res.data, null, 2) : res.data);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      setLoading(true);
      setOutput("");

      const payload = {
        client_name: form.buyerName,
        client_email: form.buyerEmail,
        due_date: form.dueDate,
        currency: form.currency,
        notes: `Seller: ${form.sellerName} (${form.sellerEmail})`,
        items: form.lineItems.map((item) => ({
          description: item.description || "Line Item",
          quantity: Number(item.quantity || 1),
          unit_price: Number(item.unit_price || 0),
          tax_rate: Number(item.tax_rate || 0),
        })),
      };

      const { data } = await client.post("/invoice/create", payload);
      setCreated(data);
      toast.success("Invoice created successfully");
      await fetchOutput(data.invoice_id, form.outputFormat);
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stack">
      <form className="card stack" onSubmit={submit}>
        <h3>Create Invoice</h3>
        <div className="grid-2">
          <div>
            <label>Seller Name</label>
            <input value={form.sellerName} onChange={(e) => updateField("sellerName", e.target.value)} />
            {errors.sellerName ? <small className="error-text">{errors.sellerName}</small> : null}
          </div>
          <div>
            <label>Seller Email</label>
            <input type="email" value={form.sellerEmail} onChange={(e) => updateField("sellerEmail", e.target.value)} />
            {errors.sellerEmail ? <small className="error-text">{errors.sellerEmail}</small> : null}
          </div>
          <div>
            <label>Buyer Name</label>
            <input value={form.buyerName} onChange={(e) => updateField("buyerName", e.target.value)} />
            {errors.buyerName ? <small className="error-text">{errors.buyerName}</small> : null}
          </div>
          <div>
            <label>Buyer Email</label>
            <input type="email" value={form.buyerEmail} onChange={(e) => updateField("buyerEmail", e.target.value)} />
            {errors.buyerEmail ? <small className="error-text">{errors.buyerEmail}</small> : null}
          </div>
          <div>
            <label>Due Date</label>
            <input type="date" value={form.dueDate} onChange={(e) => updateField("dueDate", e.target.value)} />
            {errors.dueDate ? <small className="error-text">{errors.dueDate}</small> : null}
          </div>
          <div>
            <label>Currency</label>
            <select value={form.currency} onChange={(e) => updateField("currency", e.target.value)}>
              {["AUD", "USD", "GBP", "EUR"].map((currency) => (
                <option key={currency} value={currency}>
                  {currency}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Output Format</label>
            <select value={form.outputFormat} onChange={(e) => updateField("outputFormat", e.target.value)}>
              {["ubl_xml", "json", "csv", "pdf", "generic_xml"].map((format) => (
                <option key={format} value={format}>
                  {format}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <h4>Line Items</h4>
          {form.lineItems.map((item, index) => (
            <LineItemRow
              key={`${index}-${item.description}`}
              item={item}
              index={index}
              onChange={updateLine}
              onDelete={removeLine}
              canDelete={form.lineItems.length > 1}
            />
          ))}
          <button type="button" className="btn btn-ghost" onClick={addLine}>
            Add Line Item
          </button>
        </div>

        <div className="totals">
          <div>Subtotal: {form.currency} {totals.subtotal.toFixed(2)}</div>
          <div>Tax: {form.currency} {totals.totalTax.toFixed(2)}</div>
          <div>Invoice Total: {form.currency} {totals.grandTotal.toFixed(2)}</div>
        </div>

        <button className="btn" disabled={loading}>
          {loading ? "Generating..." : "Generate Invoice"}
        </button>
      </form>

      {created ? (
        <section className="card stack">
          <p className="ok-text">Created successfully. Invoice ID: {created.invoice_id}</p>
          {output.startsWith("PDF ready:") ? (
            <a className="btn" href={output.replace("PDF ready: ", "")} download={`invoice-${created.invoice_id}.pdf`}>
              Download PDF
            </a>
          ) : (
            <pre className="code-block">{output}</pre>
          )}
          <div className="inline-row">
            <Link className="btn btn-ghost" to="/invoices">
              View All Invoices
            </Link>
            <button className="btn btn-ghost" onClick={() => navigate(`/validate`)}>
              Validate this Invoice
            </button>
            <button className="btn btn-ghost" onClick={() => navigate(`/send`)}>
              Send this Invoice
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
