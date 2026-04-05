import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import client, { formatApiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";

const services = [
  { key: "api", label: "Core API", endpoint: "/health" },
  { key: "invoice", label: "Invoice Service", endpoint: "/invoice/list" },
  { key: "transform", label: "Transform Service", endpoint: "/transform/formats" },
  { key: "validate", label: "Validation Service", endpoint: "/validate/rulesets" },
];

const quickActions = [
  { title: "Create", description: "Generate invoice data from a simple form.", link: "/create" },
  { title: "Transform", description: "Convert invoices between JSON/XML/CSV/PDF.", link: "/transform" },
  { title: "Validate", description: "Run UBL, PEPPOL, or AU checks.", link: "/validate" },
  { title: "Send", description: "Email invoice XML to a recipient.", link: "/send" },
];

export default function Dashboard() {
  const [status, setStatus] = useState({});

  useEffect(() => {
    const load = async () => {
      const results = {};

      for (const service of services) {
        try {
          await client.get(service.endpoint);
          results[service.key] = true;
        } catch {
          results[service.key] = false;
        }
      }

      if (Object.values(results).includes(false)) {
        toast.error("Some services are offline. Check API URL.");
      }
      setStatus(results);
    };

    load().catch((error) => toast.error(formatApiError(error)));
  }, []);

  return (
    <div className="stack">
      <section className="hero card">
        <h2>Compliant E-Invoicing for Australian SMBs</h2>
        <p className="muted">
          Create, transform, validate, and send invoices without touching raw XML unless you need to.
        </p>
        <div className="inline-row">
          <Link className="btn" to="/create">
            Create Invoice
          </Link>
          <Link className="btn btn-ghost" to="/invoices">
            View Invoices
          </Link>
        </div>
      </section>

      <section className="card">
        <h3>Pipeline</h3>
        <div className="pipeline">
          <span>Create</span>
          <span>Transform</span>
          <span>Validate</span>
          <span>Send</span>
        </div>
      </section>

      <section className="card">
        <h3>Quick Actions</h3>
        <div className="grid-4">
          {quickActions.map((action) => (
            <Link key={action.title} to={action.link} className="quick-card">
              <h4>{action.title}</h4>
              <p>{action.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Health Status</h3>
        <div className="grid-4">
          {services.map((service) => (
            <div key={service.key} className="health-item">
              <span>{service.label}</span>
              <StatusBadge ok={Boolean(status[service.key])} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
