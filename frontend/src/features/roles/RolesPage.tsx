import { useEffect, useState } from "react";

import {
  createRole,
  listPermissions,
  listRoles,
  replaceRolePermissions,
  type PermissionRecord,
  type RoleRecord,
} from "../../services/api";

type RolesPageProps = { token: string };

function RolesPage({ token }: RolesPageProps) {
  const [roles, setRoles] = useState<RoleRecord[]>([]);
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [nextRoles, nextPermissions] = await Promise.all([listRoles(token), listPermissions(token)]);
      setRoles(nextRoles);
      setPermissions(nextPermissions);
      const current = nextRoles.find((role) => role.id === selectedRoleId) ?? nextRoles[0];
      setSelectedRoleId(current?.id ?? "");
      setSelectedPermissions(current?.permission_ids ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load roles and permissions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  function selectRole(role: RoleRecord) {
    setSelectedRoleId(role.id);
    setSelectedPermissions(role.permission_ids);
    setMessage("");
  }

  function togglePermission(permissionId: string) {
    setSelectedPermissions((current) => current.includes(permissionId)
      ? current.filter((id) => id !== permissionId)
      : [...current, permissionId]);
  }

  async function savePermissions() {
    if (!selectedRoleId) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await replaceRolePermissions(token, selectedRoleId, selectedPermissions);
      setRoles((current) => current.map((role) => role.id === selectedRoleId ? { ...role, permission_ids: selectedPermissions } : role));
      setMessage("Permissions updated and audited.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update permissions.");
    } finally {
      setSaving(false);
    }
  }

  async function submitCreate(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const created = await createRole(token, { name: form.name, description: form.description, permission_ids: [] });
      setRoles((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedRoleId(created.id);
      setSelectedPermissions([]);
      setForm({ name: "", description: "" });
      setShowCreate(false);
      setMessage("Role created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create role.");
    } finally {
      setSaving(false);
    }
  }

  const selectedRole = roles.find((role) => role.id === selectedRoleId);

  return (
    <section className="module-panel">
      <div className="module-header">
        <div>
          <p className="eyebrow">ACCESS CONTROL</p>
          <h2>Roles & Permissions</h2>
          <p className="module-subtitle">Define what each role can do inside the approved RBAC model.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Close" : "Add role"}</button>
      </div>

      {error && <p className="form-error module-error">{error}</p>}
      {message && <p className="success-message">{message}</p>}

      {showCreate && (
        <form className="create-panel" onSubmit={submitCreate}>
          <div className="form-grid">
            <label>Role name<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
            <label>Description<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          </div>
          <button className="primary-button" disabled={saving} type="submit">Create role</button>
        </form>
      )}

      {loading ? <p className="empty-state">Loading access control…</p> : (
        <div className="roles-layout">
          <aside className="role-list">
            {roles.map((role) => (
              <button key={role.id} className={`role-item ${role.id === selectedRoleId ? "selected" : ""}`} type="button" onClick={() => selectRole(role)}>
                <strong>{role.name}</strong><span>{role.permission_ids.length} permissions</span>
              </button>
            ))}
          </aside>
          <div className="permission-panel">
            {selectedRole ? <>
              <div className="permission-header"><div><h3>{selectedRole.name}</h3><p>{selectedRole.description ?? "No description"}</p></div><button className="primary-button" disabled={saving} type="button" onClick={() => void savePermissions()}>{saving ? "Saving…" : "Save permissions"}</button></div>
              <div className="permission-grid">
                {permissions.map((permission) => (
                  <label className="permission-item" key={permission.id}>
                    <input type="checkbox" checked={selectedPermissions.includes(permission.id)} onChange={() => togglePermission(permission.id)} />
                    <span><strong>{permission.code}</strong><small>{permission.description ?? "No description"}</small></span>
                  </label>
                ))}
              </div>
            </> : <p className="empty-state">No roles available.</p>}
          </div>
        </div>
      )}
    </section>
  );
}

export default RolesPage;
