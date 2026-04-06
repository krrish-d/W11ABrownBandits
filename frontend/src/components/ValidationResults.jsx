export default function ValidationResults({ report }) {
  if (!report) return null;

  const errors = report.errors || [];
  const warningCount = errors.filter((e) => e.severity === "Warning").length;
  const criticalCount = errors.filter((e) => e.severity === "Critical").length;

  return (
    <div className="card">
      <div className={`big-status ${report.valid ? "valid" : "invalid"}`}>
        {report.valid ? "VALID" : "INVALID"}
      </div>
      <p className="muted">
        {criticalCount} critical issues, {warningCount} warnings
      </p>

      {errors.length === 0 ? (
        <p className="ok-text">All checks passed.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Rule</th>
              <th>Severity</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {errors.map((error, idx) => (
              <tr key={`${error.rule}-${idx}`} className={error.severity === "Critical" ? "row-critical" : "row-warning"}>
                <td>{error.rule}</td>
                <td>{error.severity}</td>
                <td>{error.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <details>
        <summary>Raw Response</summary>
        <pre className="code-block">{JSON.stringify(report, null, 2)}</pre>
      </details>
    </div>
  );
}
