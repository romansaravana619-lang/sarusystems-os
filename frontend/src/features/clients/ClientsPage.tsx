import { FormEvent, useEffect, useState } from "react";

import {
  completeClientOnboarding,
  createClientAgreement,
  createClientContact,
  createClientDocument,
  createClientOnboardingItem,
  createClientRelation,
  getClientWorkspace,
  listClients,
  startClientOnboarding,
  updateClientHealth,
  updateClientOnboardingItem,
  type ClientRecord,
  type ClientWorkspaceResponse,
} from "../../services/api";

type ClientStatus = "onboarding" | "active" | "at_risk" | "inactive" | "archived";
const statusLabels: Record<ClientStatus, string> = { onboarding: "Onboarding", active: "Active", at_risk: "At Risk", inactive: "Inactive", archived: "Archived" };
const relationTypes = ["project", "payment", "communication", "support"] as const;

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
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactRole, setContactRole] = useState("");
  const [agreementTitle, setAgreementTitle] = useState("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentType, setDocumentType] = useState("Agreement");
  const [itemTitle, setItemTitle] = useState("");
  const [relationType, setRelationType] = useState<(typeof relationTypes)[number]>("communication");
  const [relationId, setRelationId] = useState("");
  const [relationLabel, setRelationLabel] = useState("");
  const [relationNotes, setRelationNotes] = useState("");

  const loadClients = async () => {
    setLoading(true); setError("");
    try { setClients(await listClients(token)); } catch (err) { setError((err as Error).message); } finally { setLoading(false); }
  };
  const openClient = async (clientId: string) => {
    setError("");
    try { setWorkspace(await getClientWorkspace(token, clientId)); } catch (err) { setError((err as Error).message); }
  };
  useEffect(() => { void loadClients(); }, [token]);

  const refreshWorkspace = async () => {
    if (!workspace) return;
    await openClient(workspace.client.id);
    await loadClients();
  };
  const run = async (action: () => Promise<unknown>, message: string) => {
    setSaving(true); setError(""); setSuccess("");
    try { await action(); setSuccess(message); await refreshWorkspace(); } catch (err) { setError((err as Error).message); } finally { setSaving(false); }
  };
  const handle = async (event: FormEvent, action: () => Promise<unknown>, message: string) => { event.preventDefault(); await run(action, message); };

  if (loading) return <section className="module-panel"><p>Loading clients…</p></section>;
  const onboarding = clients.filter((client) => client.status === "onboarding").length;
  const active = clients.filter((client) => client.status === "active").length;
  const attention = clients.filter((client) => client.status === "at_risk" || client.status === "inactive").length;

  return (
    <section className="module-panel clients-page">
      <div className="module-header"><div><p className="eyebrow">REVENUE & RELATIONSHIPS</p><h2>Client Management</h2><p className="module-subtitle">One source of truth for the complete client relationship lifecycle.</p></div></div>
      {error && <p className="form-error">{error}</p>}{success && <p className="success-message">{success}</p>}
      <div className="stats-grid"><div className="stat-card"><span>Total clients</span><strong>{clients.length}</strong></div><div className="stat-card"><span>Onboarding</span><strong>{onboarding}</strong></div><div className="stat-card"><span>Active</span><strong>{active}</strong></div><div className="stat-card"><span>Attention</span><strong>{attention}</strong></div></div>
      <div className="table-wrap"><table><thead><tr><th>Client</th><th>Company</th><th>Code</th><th>Status</th><th>Health</th><th>Action</th></tr></thead><tbody>
        {clients.length ? clients.map((client) => <tr key={client.id} className="clickable-row" onClick={() => void openClient(client.id)}><td><strong>{client.name}</strong><br /><span className="table-muted">{client.email ?? client.phone ?? "No contact detail"}</span></td><td>{client.company_name ?? "—"}</td><td>{client.code}</td><td><span className={`status-pill ${statusClass(client.status)}`}>{statusLabels[client.status as ClientStatus] ?? client.status}</span></td><td><span className={`status-pill ${statusClass(client.health_status)}`}>{client.health_status} · {client.health_score}</span></td><td><button className="secondary-button" type="button" onClick={(event) => { event.stopPropagation(); void openClient(client.id); }}>Open workspace</button></td></tr>) : <tr><td colSpan={6}><p className="empty-state">No clients yet. Convert a won opportunity through the Client workflow.</p></td></tr>}
      </tbody></table></div>

      {workspace && <aside className="detail-panel">
        <div className="module-header"><div><p className="eyebrow">CLIENT WORKSPACE</p><h3>{workspace.client.name}</h3><p className="module-subtitle">{workspace.client.code} · {workspace.client.company_name ?? "Independent client"}</p></div><button className="secondary-button" type="button" onClick={() => setWorkspace(null)}>Close</button></div>
        <div className="detail-grid"><div><span>Status</span><strong>{statusLabels[workspace.client.status as ClientStatus] ?? workspace.client.status}</strong></div><div><span>Health</span><strong>{workspace.client.health_status} · {workspace.client.health_score}/100</strong></div><div><span>Primary email</span><strong>{workspace.client.email ?? "—"}</strong></div><div><span>Primary phone</span><strong>{workspace.client.phone ?? "—"}</strong></div><div><span>Industry</span><strong>{workspace.client.industry ?? "—"}</strong></div><div><span>Preferred channel</span><strong>{workspace.client.preferred_contact_channel ?? "—"}</strong></div></div>

        <div className="record-notes"><span>Client health</span><div className="button-row">{["healthy", "watch", "at_risk", "critical"].map((health) => <button key={health} className="secondary-button" disabled={saving} onClick={() => void run(() => updateClientHealth(token, workspace.client.id, { health_status: health, health_score: health === "healthy" ? 100 : health === "watch" ? 70 : health === "at_risk" ? 40 : 15 }), `Client health updated to ${health}.`)}>{health}</button>)}</div>{workspace.client.health_reason && <p>{workspace.client.health_reason}</p>}</div>

        <div className="record-notes"><span>Onboarding · {workspace.onboarding_required_remaining} required remaining</span>{workspace.client.status === "onboarding" && !workspace.client.onboarding_started_at && <button className="secondary-button" disabled={saving} onClick={() => void run(() => startClientOnboarding(token, workspace.client.id), "Client onboarding started.")}>Start onboarding</button>}<div className="checklist-list">{workspace.onboarding_items.length ? workspace.onboarding_items.map((item) => <label key={item.id} className="checklist-item"><input type="checkbox" checked={item.status === "completed"} onChange={(event) => void run(() => updateClientOnboardingItem(token, workspace.client.id, item.id, { status: event.target.checked ? "completed" : "pending" }), "Onboarding item updated.")} />{item.title}{item.required ? " · required" : ""}</label>) : <p className="table-muted">No onboarding checklist items configured.</p>}</div>{workspace.client.status === "onboarding" && workspace.onboarding_required_remaining === 0 && <button className="secondary-button" disabled={saving} onClick={() => void run(() => completeClientOnboarding(token, workspace.client.id), "Onboarding completed; client is now active.")}>Complete onboarding → Active</button>}
          <form className="inline-form" onSubmit={(event) => void handle(event, async () => { await createClientOnboardingItem(token, workspace.client.id, { title: itemTitle, required: true }); setItemTitle(""); }, "Onboarding item added.")}><input value={itemTitle} onChange={(event) => setItemTitle(event.target.value)} placeholder="Add required onboarding item" required /><button className="secondary-button" disabled={saving}>Add</button></form>
        </div>

        <div className="record-notes"><span>Contacts · {workspace.contacts.length}</span><div className="list-stack">{workspace.contacts.map((contact) => <div className="list-row" key={contact.id}><strong>{contact.name}{contact.is_primary ? " · Primary" : ""}</strong><span>{contact.role ?? "Contact"} · {contact.email ?? contact.phone ?? "No detail"}</span></div>)}</div><form className="inline-form" onSubmit={(event) => void handle(event, async () => { await createClientContact(token, workspace.client.id, { name: contactName, email: contactEmail || undefined, role: contactRole || undefined, is_primary: workspace.contacts.length === 0 }); setContactName(""); setContactEmail(""); setContactRole(""); }, "Client contact added.")}><input value={contactName} onChange={(event) => setContactName(event.target.value)} placeholder="Name" required /><input value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} placeholder="Email" type="email" /><input value={contactRole} onChange={(event) => setContactRole(event.target.value)} placeholder="Role" /><button className="secondary-button" disabled={saving}>Add contact</button></form></div>

        <div className="record-notes"><span>Agreements · {workspace.agreements.length}</span><div className="list-stack">{workspace.agreements.map((agreement) => <div className="list-row" key={agreement.id}><strong>{agreement.title}</strong><span>{agreement.status}{agreement.document_id ? ` · ${agreement.document_id}` : ""}</span></div>)}</div><form className="inline-form" onSubmit={(event) => void handle(event, async () => { await createClientAgreement(token, workspace.client.id, { title: agreementTitle }); setAgreementTitle(""); }, "Agreement added.")}><input value={agreementTitle} onChange={(event) => setAgreementTitle(event.target.value)} placeholder="Agreement title" required /><button className="secondary-button" disabled={saving}>Add agreement</button></form></div>

        <div className="record-notes"><span>Documents · {workspace.documents.length}</span><div className="list-stack">{workspace.documents.map((document) => <div className="list-row" key={document.id}><strong>{document.title}</strong><span>{document.document_type} · {document.status}</span></div>)}</div><form className="inline-form" onSubmit={(event) => void handle(event, async () => { await createClientDocument(token, workspace.client.id, { title: documentTitle, document_type: documentType }); setDocumentTitle(""); }, "Client document metadata added.")}><input value={documentTitle} onChange={(event) => setDocumentTitle(event.target.value)} placeholder="Document title" required /><input value={documentType} onChange={(event) => setDocumentType(event.target.value)} placeholder="Type" required /><button className="secondary-button" disabled={saving}>Add document</button></form></div>

        <div className="record-notes"><span>Relationship history · {workspace.relations.length}</span><div className="list-stack">{workspace.relations.map((relation) => <div className="list-row" key={relation.id}><strong>{relation.relation_type} · {relation.label ?? relation.related_entity_id.slice(0, 8)}</strong><span>{relation.status ?? "Recorded"} · {relation.notes ?? "No notes"}</span></div>)}</div><form className="inline-form" onSubmit={(event) => void handle(event, async () => { await createClientRelation(token, workspace.client.id, { relation_type: relationType, related_entity_id: relationId, label: relationLabel || undefined, notes: relationNotes || undefined }); setRelationId(""); setRelationLabel(""); setRelationNotes(""); }, "Client relationship history recorded.")}><select value={relationType} onChange={(event) => setRelationType(event.target.value as (typeof relationTypes)[number])}>{relationTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select><input value={relationId} onChange={(event) => setRelationId(event.target.value)} placeholder="Related record UUID" required /><input value={relationLabel} onChange={(event) => setRelationLabel(event.target.value)} placeholder="Label" /><input value={relationNotes} onChange={(event) => setRelationNotes(event.target.value)} placeholder="Notes" /><button className="secondary-button" disabled={saving}>Record</button></form><p className="table-muted">Project, payment, communication and support records remain authoritative in their downstream modules; this client index preserves the relationship/history without duplicating those primary records.</p></div>

        {workspace.client.notes && <div className="record-notes"><span>Notes</span><p>{workspace.client.notes}</p></div>}
      </aside>}
    </section>
  );
}
