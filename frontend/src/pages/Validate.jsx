import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import client, { formatApiError } from "../api/client";
import ValidationResults from "../components/ValidationResults";

export default function Validate() {
  const [rulesets, setRulesets] = useState([]);
  const [descriptions, setDescriptions] = useState({});
  const [ruleset, setRuleset] = useState("ubl");
  const [xml, setXml] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    client
      .get("/validate/rulesets")
      .then(({ data }) => {
        setRulesets(data.rulesets || []);
        setDescriptions(data.descriptions || {});
        setRuleset(data.default || "ubl");
      })
      .catch((error) => toast.error(formatApiError(error)));
  }, []);

  const loadXmlFile = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsText(file);
    });

  const runValidation = async () => {
    if (!xml.trim()) {
      toast.error("Paste or upload XML first.");
      return;
    }
    try {
      setLoading(true);
      const { data } = await client.post("/validate", { invoice_xml: xml, ruleset });
      setReport(data);
      toast.success("Validation complete");
    } catch (error) {
      toast.error(formatApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stack">
      <section className="card stack">
        <h3>Ruleset</h3>
        <div className="ruleset-list">
          {rulesets.map((item) => (
            <label key={item} className="radio-card">
              <input type="radio" checked={ruleset === item} onChange={() => setRuleset(item)} />
              <div>
                <strong>{item}</strong>
                <p>{descriptions[item]}</p>
              </div>
            </label>
          ))}
        </div>

        <div>
          <label>XML Input</label>
          <textarea value={xml} onChange={(e) => setXml(e.target.value)} rows={12} />
        </div>
        <input
          type="file"
          accept=".xml"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const content = await loadXmlFile(file);
            setXml(String(content));
          }}
        />

        <button className="btn" onClick={runValidation} disabled={loading}>
          {loading ? "Validating..." : "Validate"}
        </button>
      </section>

      <ValidationResults report={report} />
    </div>
  );
}
