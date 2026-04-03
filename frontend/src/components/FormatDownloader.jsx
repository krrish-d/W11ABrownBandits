import { useState } from "react";
import toast from "react-hot-toast";
import client, { createBlobUrl, formatApiError } from "../api/client";

const formats = ["json", "ubl", "xml", "csv", "pdf"];

export default function FormatDownloader({ invoiceId }) {
  const [format, setFormat] = useState("json");
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState("");

  const download = async () => {
    try {
      setLoading(true);
      setPreview("");

      if (format === "pdf") {
        const res = await client.get(`/invoices/${invoiceId}?format=pdf`, { responseType: "blob" });
        const url = createBlobUrl(res.data, "application/pdf");
        const a = document.createElement("a");
        a.href = url;
        a.download = `invoice-${invoiceId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        return;
      }

      const responseType = format === "csv" ? "blob" : "text";
      const res = await client.get(`/invoices/${invoiceId}?format=${format}`, { responseType });

      if (format === "csv") {
        const url = createBlobUrl(res.data, "text/csv");
        const a = document.createElement("a");
        a.href = url;
        a.download = `invoice-${invoiceId}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else if (format === "json") {
        setPreview(JSON.stringify(res.data, null, 2));
      } else {
        setPreview(res.data);
      }
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="inline-row">
        <select value={format} onChange={(e) => setFormat(e.target.value)}>
          {formats.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <button className="btn" onClick={download} disabled={loading}>
          {loading ? "Working..." : "Download / Preview"}
        </button>
      </div>
      {preview ? <pre className="code-block">{preview}</pre> : null}
    </div>
  );
}
