import { Link } from "react-router-dom";

export default function InvoiceTable({ invoices, onDelete, loading = false }) {
  if (loading) {
    return (
      <div className="card">
        {[1, 2, 3].map((row) => (
          <div key={row} className="skeleton-row" />
        ))}
      </div>
    );
  }

  if (!invoices.length) {
    return <div className="card empty-state">No invoices yet - create your first one.</div>;
  }

  return (
    <div className="card table-wrap">
      <table>
        <thead>
          <tr>
            <th>Invoice ID</th>
            <th>Buyer Name</th>
            <th>Buyer Email</th>
            <th>Due Date</th>
            <th>Total</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.invoice_id}>
              <td>{invoice.invoice_number || invoice.invoice_id}</td>
              <td>{invoice.client_name}</td>
              <td>{invoice.client_email}</td>
              <td>{invoice.due_date}</td>
              <td>
                {invoice.currency} {Number(invoice.grand_total || 0).toFixed(2)}
              </td>
              <td className="actions-cell">
                <Link className="btn btn-ghost" to={`/invoices/${invoice.invoice_id}`}>
                  View
                </Link>
                <button className="btn btn-danger" onClick={() => onDelete(invoice)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
