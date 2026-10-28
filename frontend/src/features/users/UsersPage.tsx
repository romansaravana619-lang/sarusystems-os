import { useEffect, useState, type FormEvent } from "react";

import {
  createUser,
  listRoles,
  listUsers,
  type RoleRecord,
  type UserRecord,
} from "../../services/api";

type UsersPageProps = {
  token: string;
  companyId: string;
};

function UsersPage({ token, companyId }: UsersPageProps) {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<RoleRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ fullName: "", email: "", password: "", roleId: "" });

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [nextUsers, nextRoles] = await Promise.all([listUsers(token), listRoles(token)]);
      setUsers(nextUsers);
      setRoles(nextRoles.filter((role) => role.is_active));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await createUser(token, {
        company_id: companyId,
        full_name: form.fullName,
        email: form.email,
        password: form.password,
        role_ids: form.roleId ? [form.roleId] : [],
      });
      setForm({ fullName: "", email: "", password: "", roleId: "" });
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user.");
    }
  }

  return (
    <section className="module-panel">
      <div className="module-header">
        <div>
          <p className="eyebrow">ACCESS CONTROL</p>
          <h2>Users</h2>
          <p className="module-subtitle">Manage people who can operate inside SaruSystems OS.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => setShowCreate((value) => !value)}>
          {showCreate ? "Close" : "Add user"}
        </button>
      </div>

      {error && <p className="form-error module-error">{error}</p>}

      {showCreate && (
        <form className="create-panel" onSubmit={submit}>
          <div className="form-grid">
            <label>Name<input required value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} /></label>
            <label>Email<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <label>Password<input required minLength={8} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
            <label>Role<select value={form.roleId} onChange={(e) => setForm({ ...form, roleId: e.target.value })}><option value="">No role</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select></label>
          </div>
          <button className="primary-button" type="submit">Create user</button>
        </form>
      )}

      <div className="table-wrap">
        {loading ? <p className="empty-state">Loading users…</p> : users.length === 0 ? <p className="empty-state">No users found.</p> : (
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Status</th></tr></thead>
            <tbody>{users.map((user) => (
              <tr key={user.id}><td>{user.full_name}</td><td>{user.email}</td><td><span className={`status-pill ${user.is_active ? "active" : "inactive"}`}>{user.is_active ? "Active" : "Inactive"}</span></td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export default UsersPage;
