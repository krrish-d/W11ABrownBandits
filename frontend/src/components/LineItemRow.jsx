export default function LineItemRow({ item, index, canDelete, onChange, onDelete }) {
  const lineTotal = Number(item.quantity || 0) * Number(item.unit_price || 0);

  return (
    <div className="line-item-row">
      <input
        placeholder="Description"
        value={item.description}
        onChange={(e) => onChange(index, "description", e.target.value)}
      />
      <input
        type="number"
        min="1"
        placeholder="Qty"
        value={item.quantity}
        onChange={(e) => onChange(index, "quantity", Number(e.target.value))}
      />
      <input
        type="number"
        min="0"
        step="0.01"
        placeholder="Unit Price"
        value={item.unit_price}
        onChange={(e) => onChange(index, "unit_price", Number(e.target.value))}
      />
      <input
        type="number"
        min="0"
        max="100"
        placeholder="Tax %"
        value={item.tax_rate}
        onChange={(e) => onChange(index, "tax_rate", Number(e.target.value))}
      />
      <div className="line-total">${lineTotal.toFixed(2)}</div>
      <button type="button" className="btn btn-ghost" onClick={() => onDelete(index)} disabled={!canDelete}>
        Delete
      </button>
    </div>
  );
}
