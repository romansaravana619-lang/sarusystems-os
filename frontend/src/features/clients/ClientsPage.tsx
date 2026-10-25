import { useEffect, useState } from "react";

import {
  completeClientOnboarding,
  getClientWorkspace,
  startClientOnboarding,
  updateClientHealth,
  updateClientOnboardingItem,
  type ClientWorkspaceResponse,
  type ClientRecord,
} from "../../services/api";

type ClientStatus = "onboarding" | "active" | "at_risk" | "inactive" | "archived";
const statusLabels: Record<ClientStatus, string> = { onboarding: "Onboarding", active: "Active", at_risk: "At Risk", inactive: "Inactive", archived: "Archived" };

function statusClass(status: string): string {
  if (status === "active" || status === "healthy") return "active";
  if (status === "at_risk" || status === "watch" || status === "critical") return "warning";
  if (status === "inactive" || status === "archived") return "muted";
  return "pending";
}

export default function ClientsPage({ token }: { token: string }) {
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [workspace, setWorkspace] = useState<ClientWorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadClients = async () => {
    setLoading(true); setError("");
    try { setClients(await (await import("../../services/api")).listClients(token)); }
    catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  };

  const openClient = async (clientId: string) => {
    setError("");
    try { setWorkspace(await getClientWorkspace(token, clientId)); }
    catch (err) { setError((err as Error).message); }
  };

  useEffect(() => { void loadClients(); }, [token]);

  const startOnboarding = async () => {
    if (!workspace) return;
    setSaving(true); setError(""); setSuccess("");
    try { await startClientOnboarding(token, workspace.client.id); setSuccess("Client onboarding started."); await openClient(workspace.client.id); await loadClients(); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const completeOnboarding = async () => {
    if (!workspace) return;
    setSaving(true); setError(""); setSuccess("");
    try { await completeClientOnboarding(token, workspace.client.id); setSuccess("Client onboarding completed; client is now active."); await openClient(workspace.client.id); await loadClients(); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const setHealth = async (healthStatus: string) => {
    if (!workspace) return;
    setSaving(true); setError("");
    try { await updateClientHealth(token, workspace.client.id, { health_status: healthStatus, health_score: healthStatus === "healthy" ? 100 : healthStatus === "watch" ? 70 : healthStatus === "at_risk" ? 40 : 15 }); await openClient(workspace.client.id); await loadClients(); }
    catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  };

  const toggleOnboardingItem = async (itemId: string, completed: boolean) => {
    if (!workspace) return;
    try { await updateClientOnboardingItem(token, workspace.client.id, itemId, { status: completed ? "completed" : "pending" }); await openClient(workspace.client.id); }
    catch (err) { setError((err as Error).message); }
  };

  if (loading) return <section className="module-panel"><p>Loading clients…</p></section>;

  const onboarding = clients.filter((client) => client.status === "onboarding").length;
  const active = clients.filter((client) => client.status === "active").length;
  const attention = clients.filter((client) => client.status === "at_risk" || client.status === "inactive").length;

  return (
    <section className="module-panel clients-page">
      <div className="module-header"><div><p className="eyebrow">REVENUE & RELATIONSHIPS</p><h2>Client Management</h2><p className="module-subtitle">One source of truth for the complete client relationship lifecycle.</p></div></div>
      {error && <p className="form-error">{error}</p>}{success && <p className="success-message">{success}</p>}

      <div className="stats-grid">
        <div className="stat-card"><span>Total clients</span><strong>{clients.length}</strong></div>
        <div className="stat-card"><span>Onboarding</span><strong>{onboarding}</strong></div>
        <div className="stat-card"><span>Active</span><strong>{active}</strong></div>
        <div className="stat-card"><span>Attention</span><strong>{attention}</strong></div>
      </div>

      <div className="table-wrap"><table><thead><tr><th>Client</th><th>Company</th><th>Code</th><th>Status</th><th>Health</th><th>Action</th></tr></thead><tbody>
        {clients.length ? clients.map((client) => (
          <tr key={client.id} className="clickable-row" onClick={() => void openClient(client.id)}>
            <td><strong>{client.name}</strong><br /><span className="table-muted">{client.email ?? client.phone ?? "No contact detail"}</span></td>
            <td>{client.company_name ?? "—"}</td><td>{client.code}</td>
            <td><span className={`status-pill ${statusClass(client.status)}`}>{statusLabels[client.status as ClientStatus] ?? client.status}</span></td>
            <td><span className={`status-pill ${statusClass(client.health_status)}`}>{client.health_status} · {client.health_score}</span></td>
            <td><button className="secondary-button" type="button" onClick={(event) => { event.stopPropagation(); void openClient(client.id); }}>Open workspace</button></td>
          </tr>
        )) : <tr><td colSpan={6}><p className="empty-state">No clients yet. Convert a won opportunity through the Client API workflow.</p></td></tr>}
      </tbody></table></div>

      {workspace && (
        <aside className="detail-panel">
          <div className="module-header"><div><p className="eyebrow">CLIENT WORKSPACE</p><h3>{workspace.client.name}</h3><p className="module-subtitle">{workspace.client.code} · {workspace.client.company_name ?? "Independent client"}</p></div><button className="secondary-button" type="button" onClick={() => setWorkspace(null)}>Close</button></div>
          <div className="detail-grid">
            <div><span>Status</span><strong>{statusLabels[workspace.client.status as ClientStatus] ?? workspace.client.status}</strong></div>
            <div><span>Health</span><strong>{workspace.client.health_status} · {workspace.client.health_score}/100</strong></div>
            <div><span>Primary email</span><strong>{workspace.client.email ?? "—"}</strong></div>
            <div><span>Primary phone</span><strong>{workspace.client.phone ?? "—"}</strong></div>
            <div><span>Industry</span><strong>{workspace.client.industry ?? "—"}</strong></div>
            <div><span>Preferred channel</span><strong>{workspace.client.preferred_contact_channel ?? "—"}</strong></div>
          </div>

          <div className="record-notes"><span>Client health</span><div className="button-row"><button className="secondary-button" disabled={saving} onClick={() => void setHealth("healthy")}>Healthy</button><button className="secondary-button" disabled={saving} onClick={() => void setHealth("watch")}>Watch</button><button className="secondary-button" disabled={saving} onClick={() => void setHealth("at_risk")}>At risk</button><button className="secondary-button" disabled={saving} onClick={() => void setHealth("critical")}>Critical</button></div>{workspace.client.health_reason && <p>{workspace.client.health_reason}</p>}</div>

          <div className="record-notes"><span>Onboarding · {workspace.onboarding_required_remaining} required remaining</span>
            {workspace.client.status === "onboarding" && !workspace.client.onboarding_started_at && <button className="secondary-button" disabled={saving} onClick={() => void startOnboarding()}>Start onboarding</button>}
            <div className="checklist-list">{workspace.onboarding_items.length ? workspace.onboarding_items.map((item) => <label key={item.id} className="checklist-item"><input type="checkbox" checked={item.status === "completed"} onChange={(event) => void toggleOnboardingItem(item.id, event.target.checked)} />{item.title}{item.required ? " · required" : ""}</label>) : <p className="table-muted">No onboarding checklist items configured yet.</p>}</div>
            {workspace.client.status === "onboarding" && workspace.onboarding_required_remaining === 0 && <button className="secondary-button" disabled={saving} onClick={() => void completeOnboarding()}>Complete onboarding → Active</button>}
          </div>

          <div className="detail-grid">
            <div><span>Contacts</span><strong>{workspace.contacts.length}</strong></div>
            <div><span>Agreements</span><strong>{workspace.agreements.length}</strong></div>
            <div><span>Documents</span><strong>{workspace.documents.length}</strong></div>
            <div><span>Linked history</span><strong>{workspace.relations.length}</strong></div>
          </div>
          {workspace.notes && <div className="record-notes"><span>Notes</span><p>{workspace.client.notes}</p></div>}
        </aside>
      )}
    </section>
  );
}
