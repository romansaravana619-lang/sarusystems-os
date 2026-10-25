import { FormEvent, useEffect, useState } from "react";

import { convertProspect, createOpportunity, createProspect, listContacts, listOpportunities, listProspects, type ContactRecord, type OpportunityRecord, type ProspectRecord } from "../../services/api";

type Tab = "prospects" | "contacts" | "opportunities";

export default function CRMPage({ token }: { token: string }) {
  const [tab, setTab] = useState<Tab>("prospects");
  const [prospects, setProspects] = useState<ProspectRecord[]>([]);
  const [contacts, setContacts] = useState<ContactRecord[]>([]);
  const [opportunities, setOpportunities] = useState<OpportunityRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [source, setSource] = useState("");
  const [opportunityName, setOpportunityName] = useState("");
  const [service, setService] = useState("");
  const [contactId, setContactId] = useState("");
  const [estimatedValue, setEstimatedValue] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [prospectData, contactData, opportunityData] = await Promise.all([listProspects(token), listContacts(token), listOpportunities(token)]);
      setProspects(prospectData); setContacts(contactData); setOpportunities(opportunityData);
      if (!contactId && contactData[0]) setContactId(contactData[0].id);
    } catch (err) { setError((err as Error).message); } finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, [token]);

  const submitProspect = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError(""); setSuccess("");
    try { await createProspect(token, { name, company_name: companyName || undefined, email: email || undefined, source: source || undefined }); setName(""); setCompanyName(""); setEmail(""); setSource(""); setSuccess("Prospect created successfully."); await load(); }
    catch (err) { setError((err as Error).message); } finally { setSaving(false); }
  };

  const submitOpportunity = async (event: FormEvent) => {
    event.preventDefault(); if (!contactId) return;
    setSaving(true); setError(""); setSuccess("");
    try { await createOpportunity(token, { contact_id: contactId, name: opportunityName, service: service || undefined, estimated_value: estimatedValue ? Number(estimatedValue) : undefined }); setOpportunityName(""); setService(""); setEstimatedValue(""); setSuccess("Opportunity created successfully."); await load(); }
    catch (err) { setError((err as Error).message); } finally { setSaving(false); }
  };

  const convert = async (prospectId: string) => {
    setSaving(true); setError(""); setSuccess("");
    try { await convertProspect(token, prospectId); setSuccess("Prospect converted to contact. Existing prospect history is preserved."); await load(); }
    catch (err) { setError((err as Error).message); } finally { setSaving(false); }
  };

  if (loading) return <section className="module-panel"><p>Loading CRM…</p></section>;

  return <section className="module-panel crm-page">
    <div className="module-header"><div><p className="eyebrow">REVENUE & RELATIONSHIPS</p><h2>CRM</h2><p className="module-subtitle">Prospect → Contact → Opportunity</p></div></div>
    {error && <p className="form-error">{error}</p>}
    {success && <p className="success-message">{success}</p>}
    <div className="crm-tabs">{(["prospects", "contacts", "opportunities"] as Tab[]).map((item) => <button key={item} className={`secondary-button ${tab === item ? "selected-tab" : ""}`} type="button" onClick={() => setTab(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</div>

    {tab === "prospects" && <>
      <form className="create-panel" onSubmit={submitProspect}><h3>Add prospect</h3><div className="form-grid"><label>Name<input required value={name} onChange={(e) => setName(e.target.value)} /></label><label>Business<input value={companyName} onChange={(e) => setCompanyName(e.target.value)} /></label><label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label><label>Source<input value={source} onChange={(e) => setSource(e.target.value)} placeholder="Instagram, referral, website…" /></label></div><button className="primary-button" disabled={saving}>Create Prospect</button></form>
      <div className="table-wrap"><table><thead><tr><th>Name</th><th>Business</th><th>Status</th><th>Source</th><th>Action</th></tr></thead><tbody>{prospects.length ? prospects.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.company_name ?? "—"}</td><td><span className="status-pill active">{item.status}</span></td><td>{item.source ?? "—"}</td><td><button className="secondary-button" type="button" disabled={saving || item.status === "qualified"} onClick={() => void convert(item.id)}>{item.status === "qualified" ? "Converted" : "Convert"}</button></td></tr>) : <tr><td colSpan={5}><p className="empty-state">No prospects yet.</p></td></tr>}</tbody></table></div>
    </>}

    {tab === "contacts" && <div className="table-wrap"><table><thead><tr><th>Name</th><th>Business</th><th>Email</th><th>Source Prospect</th></tr></thead><tbody>{contacts.length ? contacts.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.company_name ?? "—"}</td><td>{item.email ?? "—"}</td><td>{item.prospect_id ? "Converted prospect" : "Direct contact"}</td></tr>) : <tr><td colSpan={4}><p className="empty-state">No contacts yet.</p></td></tr>}</tbody></table></div>}

    {tab === "opportunities" && <>
      <form className="create-panel" onSubmit={submitOpportunity}><h3>Add opportunity</h3><div className="form-grid"><label>Contact<select required value={contactId} onChange={(e) => setContactId(e.target.value)}><option value="">Select contact</option>{contacts.map((item) => <option key={item.id} value={item.id}>{item.name}{item.company_name ? ` — ${item.company_name}` : ""}</option>)}</select></label><label>Opportunity<input required value={opportunityName} onChange={(e) => setOpportunityName(e.target.value)} /></label><label>Service<input value={service} onChange={(e) => setService(e.target.value)} /></label><label>Estimated value<input type="number" min="0" value={estimatedValue} onChange={(e) => setEstimatedValue(e.target.value)} /></label></div><button className="primary-button" disabled={saving || !contactId}>Create Opportunity</button></form>
      <div className="table-wrap"><table><thead><tr><th>Opportunity</th><th>Service</th><th>Stage</th><th>Value</th></tr></thead><tbody>{opportunities.length ? opportunities.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.service ?? "—"}</td><td><span className="status-pill active">{item.stage}</span></td><td>{item.estimated_value == null ? "—" : `₹${item.estimated_value.toLocaleString("en-IN")}`}</td></tr>) : <tr><td colSpan={4}><p className="empty-state">No opportunities yet.</p></td></tr>}</tbody></table></div>
    </>}
  </section>;
}
