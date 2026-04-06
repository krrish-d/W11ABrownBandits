import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import client, { createBlobUrl, formatApiError } from "../api/client";

export default function Transform() {
  const [formats, setFormats] = useState({ input_formats: [], output_formats: [] });
  const [inputFormat, setInputFormat] = useState("json");
  const [outputFormat, setOutputFormat] = useState("ubl_xml");
  const [xmlType, setXmlType] = useState("ubl");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    client
      .get("/transform/formats")
      .then(({ data }) => {
        setFormats(data);
        setInputFormat(data.input_formats?.[0] || "json");
        setOutputFormat(data.output_formats?.[0] || "ubl_xml");
      })
      .catch((error) => toast.error(formatApiError(error)));
  }, []);

  const parseFileAsText = (selected) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsText(selected);
    });

  const parseFileAsBase64 = (selected) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = String(reader.result).split(",")[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(selected);
    });

  const convert = async () => {
    try {
      setLoading(true);
      setResult("");
      setDownloadUrl("");

      let payload = { input_format: inputFormat, output_format: outputFormat, xml_type: xmlType };
      if (inputFormat === "pdf") {
        if (!file) {
          toast.error("Upload a PDF first.");
          return;
        }
        payload.invoice_data_base64 = await parseFileAsBase64(file);
      } else if (inputFormat === "csv") {
        if (!file) {
          toast.error("Upload a CSV file first.");
          return;
        }
        payload.invoice_data = await parseFileAsText(file);
      } else {
        if (!text.trim()) {
          toast.error("Paste invoice data first.");
          return;
        }
        payload.invoice_data = text;
      }

      if (outputFormat === "pdf") {
        const res = await client.post("/transform", payload, { responseType: "blob" });
        setDownloadUrl(createBlobUrl(res.data, "application/pdf"));
      } else if (outputFormat === "csv") {
        const res = await client.post("/transform", payload, { responseType: "text" });
        setResult(res.data);
      } else if (outputFormat === "json") {
        const res = await client.post("/transform", payload);
        setResult(JSON.stringify(res.data, null, 2));
      } else {
        const res = await client.post("/transform", payload, { responseType: "text" });
        setResult(res.data);
      }
      toast.success("Transformation complete");
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const incompatible = inputFormat === outputFormat;

  return (
    <div className="stack">
      <section className="card stack">
        <div className="grid-2">
          <div>
            <label>Input Format</label>
            <select value={inputFormat} onChange={(e) => setInputFormat(e.target.value)}>
              {(formats.input_formats || []).map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Output Format</label>
            <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
              {(formats.output_formats || []).map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label>XML Type (used when output is xml)</label>
          <select value={xmlType} onChange={(e) => setXmlType(e.target.value)}>
            {(formats.xml_type_options || ["ubl", "generic"]).map((xmlOpt) => (
              <option key={xmlOpt} value={xmlOpt}>{xmlOpt}</option>
            ))}
          </select>
        </div>

        {inputFormat === "csv" || inputFormat === "pdf" ? (
          <div>
            <label>Upload {inputFormat.toUpperCase()} File</label>
            <input type="file" accept={inputFormat === "csv" ? ".csv" : ".pdf"} onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
        ) : (
          <div>
            <label>Paste Invoice Content</label>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} />
          </div>
        )}

        {incompatible ? <p className="warning-text">Input and output formats are the same.</p> : null}

        <button className="btn" onClick={convert} disabled={loading || incompatible}>
          {loading ? "Converting..." : "Convert"}
        </button>
      </section>

      {downloadUrl ? (
        <section className="card">
          <a className="btn" href={downloadUrl} download="transformed-invoice.pdf">Download PDF</a>
        </section>
      ) : null}
      {result ? (
        <section className="card">
          <pre className="code-block">{result}</pre>
        </section>
      ) : null}
    </div>
  );
}
