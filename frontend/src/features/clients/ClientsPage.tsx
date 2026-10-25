import { useEffect, useState } from "react";

import {
  listClients,
  startClientOnboarding,
  type ClientRecord,
} from "../../services/api";

type ClientStatus = "onboarding" | "active" | "at_risk" | "inactive" | "archived";

const statusLabels: Record<ClientStatus, string> = {
  onboarding: "Onboarding",
  active: "Active",
  at_risk: "At Risk",
  inactive: "Inactive",
  archived: "Archived",
};

function statusClass(status: string): string {
  if (status === "active") return "active";
  if (status === "at_risk") return "warning";
  if (status === "inactive" || status === "archived") return "muted";
  return "pending";
}

export default function ClientsPage({ token }: { token: string }) {
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setClients(await listClients(token));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [token]);

  const startOnboarding = async (clientId: string) => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await startClientOnboarding(token, clientId);
      setSuccess("Client onboarding started.");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <section className="module-panel"><p>Loading clients…</p></section>;

  const selected = clients.find((client) => client.id === selectedClientId) ?? null;
  const onboarding = clients.filter((client) => client.status === "onboarding").length;
  const active = clients.filter((client) => client.status === "active").length;
  const attention = clients.filter((client) => client.status === "at_risk" || client.status === "inactive").length;

  return (
    <section className="module-panel clients-page">
      <div className="module-header">
        <div>
          <p className="eyebrow">REVENUE & RELATIONSHIPS</p>
          <h2>Clients</h2>
          <p className="module-subtitle">Converted opportunities → onboarding → active client relationship</p>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}
      {success && <p className="success-message">{success}</p>}

      <div className="stats-grid">
        <div className="stat-card"><span>Total clients</span><strong>{clients.length}</strong></div>
        <div className="stat-card"><span>Onboarding</span><strong>{onboarding}</strong></div>
        <div className="stat-card"><span>Active</span><strong>{active}</strong></div>
        <div className="stat-card"><span>Attention</span><strong>{attention}</strong></div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Client</th><th>Company</th><th>Code</th><th>Status</th><th>Onboarding</th><th>Action</th></tr>
          </thead>
          <tbody>
            {clients.length ? clients.map((client) => (
              <tr key={client.id} onClick={() => setSelectedClientId(client.id)} className="clickable-row">
                <td><strong>{client.name}</strong><br /><span className="table-muted">{client.email ?? client.phone ?? "No contact detail"}</span></td>
                <td>{client.company_name ?? "—"}</td>
                <td>{client.code}</td>
                <td><span className={`status-pill ${statusClass(client.status)}`}>{statusLabels[client.status as ClientStatus] ?? client.status}</span></td>
                <td>{client.onboarding_started_at ? new Date(client.onboarding_started_at).toLocaleDateString("en-IN") : "Not started"}</td>
                <td>
                  {client.status === "onboarding" && !client.onboarding_started_at ? (
                    <button className="secondary-button" type="button" disabled={saving} onClick={(event) => { event.stopPropagation(); void startOnboarding(client.id); }}>Start onboarding</button>
                  ) : <button className="secondary-button" type="button" onClick={(event) => { event.stopPropagation(); setSelectedClientId(client.id); }}>View</button>}
                </td>
              </tr>
            )) : <tr><td colSpan={6}><p className="empty-state">No clients yet. A won opportunity can be converted into a client from the Client API workflow.</p></td></tr>}
          </tbody>
        </table>
      </div>

      {selected && (
        <aside className="detail-panel">
          <div className="module-header">
            <div><p className="eyebrow">CLIENT RECORD</p><h3>{selected.name}</h3><p className="module-subtitle">{selected.code} · {selected.company_name ?? "Independent client"}</p></div>
            <button className="secondary-button" type="button" onClick={() => setSelectedClientId(null)}>Close</button>
          </div>
          <div className="detail-grid">
            <div><span>Status</span><strong>{statusLabels[selected.status as ClientStatus] ?? selected.status}</strong></div>
            <div><span>Email</span><strong>{selected.email ?? "—"}</strong></div>
            <div><span>Phone</span><strong>{selected.phone ?? "—"}</strong></div>
            <div><span>Owner</span><strong>{selected.owner_user_id ?? "Unassigned"}</strong></div>
          </div>
          {selected.notes && <div className="record-notes"><span>Notes</span><p>{selected.notes}</p></div>}
        </aside>
      )}
    </section>
  );
}
