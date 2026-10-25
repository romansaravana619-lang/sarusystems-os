import { useEffect, useState } from "react";

import { listAuditLogs, type AuditRecord } from "../../services/api";

type AuditPageProps = { token: string };

function AuditPage({ token }: AuditPageProps) {
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listAuditLogs(token)
      .then(setLogs)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load audit history."))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <section className="module-panel">
      <div className="module-header">
        <div>
          <p className="eyebrow">GOVERNANCE</p>
          <h2>Audit History</h2>
          <p className="module-subtitle">Recent critical system actions, preserved for Founder review.</p>
        </div>
      </div>
      {error && <p className="form-error module-error">{error}</p>}
      {loading ? <p className="empty-state">Loading audit history…</p> : logs.length === 0 ? <p className="empty-state">No audit activity recorded yet.</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Action</th><th>Entity</th><th>Actor</th><th>Details</th></tr></thead>
            <tbody>{logs.map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.created_at).toLocaleString()}</td>
                <td><strong>{log.action}</strong></td>
                <td>{log.entity_type}{log.entity_id ? ` · ${log.entity_id.slice(0, 8)}` : ""}</td>
                <td>{log.actor_user_id ? log.actor_user_id.slice(0, 8) : "System"}</td>
                <td>{log.details ?? "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default AuditPage;
