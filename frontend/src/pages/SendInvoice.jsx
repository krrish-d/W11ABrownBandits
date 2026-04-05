import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import client, { formatApiError } from "../api/client";

const emailRegex = /\S+@\S+\.\S+/;

export default function SendInvoice() {
  const [mode, setMode] = useState("stored");
  const [invoices, setInvoices] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [xml, setXml] = useState("");
  const [recipient, setRecipient] = useState("");
  const [senderName, setSenderName] = useState("");
  const [subject, setSubject] = useState("");
  const [messageBody, setMessageBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    client
      .get("/invoice/list")
      .then(({ data }) => {
        setInvoices(data);
        if (data.length) setSelectedId(data[0].invoice_id);
      })
      .catch(() => {
        // Keep page usable for raw XML mode even when invoices fail.
      });
  }, []);

  const send = async () => {
    if (!emailRegex.test(recipient)) {
      toast.error("Enter a valid recipient email.");
      return;
    }

    try {
      setLoading(true);
      setSuccess(null);

      let xmlContent = xml;
      if (mode === "stored") {
        if (!selectedId) {
          toast.error("Select an invoice first.");
          return;
        }
        const res = await client.get(`/invoice/fetch/${selectedId}?format=ubl`, { responseType: "text" });
        xmlContent = res.data;
      }

      if (!xmlContent.trim()) {
        toast.error("Invoice XML is empty.");
        return;
      }

      const payload = {
        xml_content: xmlContent,
        recipient_email: recipient,
        sender_name: senderName,
        subject,
        message_body: messageBody,
      };

      let result;
      try {
        result = await client.post("/send", payload);
      } catch {
        result = await client.post("/communicate/send", payload);
      }

      setSuccess({
        recipient,
        invoiceId: mode === "stored" ? selectedId : "raw-xml",
        timestamp: new Date().toISOString(),
        details: result.data,
      });
      toast.success("Invoice sent successfully");
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stack">
      <section className="card stack">
        <div className="inline-row">
          <button className={`btn ${mode === "stored" ? "" : "btn-ghost"}`} onClick={() => setMode("stored")}>
            Select Stored Invoice
          </button>
          <button className={`btn ${mode === "raw" ? "" : "btn-ghost"}`} onClick={() => setMode("raw")}>
            Paste Raw UBL XML
          </button>
        </div>

        {mode === "stored" ? (
          <div>
            <label>Invoice</label>
            <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              {invoices.map((invoice) => (
                <option key={invoice.invoice_id} value={invoice.invoice_id}>
                  {invoice.invoice_number} - {invoice.client_name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label>UBL XML</label>
            <textarea rows={10} value={xml} onChange={(e) => setXml(e.target.value)} />
          </div>
        )}

        <div className="grid-2">
          <div>
            <label>Recipient Email</label>
            <input value={recipient} onChange={(e) => setRecipient(e.target.value)} />
          </div>
          <div>
            <label>Sender Name</label>
            <input value={senderName} onChange={(e) => setSenderName(e.target.value)} />
          </div>
          <div>
            <label>Subject</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Invoice from [Seller Name]" />
          </div>
        </div>
        <div>
          <label>Message Body</label>
          <textarea rows={5} value={messageBody} onChange={(e) => setMessageBody(e.target.value)} />
        </div>

        <button className="btn" onClick={send} disabled={loading}>
          {loading ? "Sending..." : "Send Invoice"}
        </button>
      </section>

      {success ? (
        <section className="card">
          <p className="ok-text">Sent successfully</p>
          <p>Recipient: {success.recipient}</p>
          <p>Invoice ID: {success.invoiceId}</p>
          <p>Timestamp: {success.timestamp}</p>
        </section>
      ) : null}
    </div>
  );
}
