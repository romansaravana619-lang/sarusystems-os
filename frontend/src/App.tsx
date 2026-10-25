import { useState } from "react";
import AuthGate from "./features/auth/AuthGate";
import AuditPage from "./features/audit/AuditPage";
import ClientsPage from "./features/clients/ClientsPage";
import CommandCenterPage from "./features/command-center/CommandCenterPage";
import CompanyPage from "./features/company/CompanyPage";
import CRMPage from "./features/crm/CRMPage";
import RolesPage from "./features/roles/RolesPage";
import SalesPage from "./features/sales/SalesPage";
import ServicesPage from "./features/services/ServicesPage";
import TasksPage from "./features/tasks/TasksPage";
import UsersPage from "./features/users/UsersPage";
import type { MeResponse } from "./services/api";
type Module = "command" | "company" | "crm" | "sales" | "clients" | "services" | "tasks" | "users" | "roles" | "audit";
function FounderConsole({ user, token, signOut }: { user: MeResponse; token: string; signOut: () => Promise<void> }) {
  const [activeModule,setActiveModule]=useState<Module>("command");
  const canViewCommandCenter=user.permissions.includes("command_center.view"),canViewCompany=user.permissions.includes("company.view"),canViewCRM=user.permissions.includes("crm.prospects.view"),canViewSales=user.permissions.includes("sales.dashboard.view"),canViewClients=user.permissions.includes("clients.view"),canViewServices=user.permissions.includes("services.view"),canViewTasks=user.permissions.includes("tasks.view"),canManageUsers=user.permissions.includes("users.view"),canManageRoles=user.permissions.includes("roles.view"),canViewAudit=user.permissions.includes("audit.view");
  const go=(module:Module)=>setActiveModule(module===activeModule?"command":module);
  return <main className="console-shell"><header className="console-header"><div><p className="eyebrow">SARU SYSTEMS</p><h1>Founder Command Center</h1></div><div className="header-actions">{canViewCommandCenter&&<button className="secondary-button" type="button" onClick={()=>go("command")}>Command Center</button>}{canViewCompany&&<button className="secondary-button" type="button" onClick={()=>go("company")}>Company Core</button>}{canViewCRM&&<button className="secondary-button" type="button" onClick={()=>go("crm")}>CRM</button>}{canViewSales&&<button className="secondary-button" type="button" onClick={()=>go("sales")}>Sales</button>}{canViewClients&&<button className="secondary-button" type="button" onClick={()=>go("clients")}>Clients</button>}{canViewServices&&<button className="secondary-button" type="button" onClick={()=>go("services")}>Services</button>}{canViewTasks&&<button className="secondary-button" type="button" onClick={()=>go("tasks")}>Tasks</button>}{canManageUsers&&<button className="secondary-button" type="button" onClick={()=>go("users")}>Users</button>}{canManageRoles&&<button className="secondary-button" type="button" onClick={()=>go("roles")}>Roles & Permissions</button>}{canViewAudit&&<button className="secondary-button" type="button" onClick={()=>go("audit")}>Audit</button>}<button className="secondary-button" type="button" onClick={()=>void signOut()}>Sign out</button></div></header>{activeModule==="company"&&canViewCompany?<CompanyPage token={token}/>:activeModule==="crm"&&canViewCRM?<CRMPage token={token}/>:activeModule==="sales"&&canViewSales?<SalesPage token={token}/>:activeModule==="clients"&&canViewClients?<ClientsPage token={token}/>:activeModule==="services"&&canViewServices?<ServicesPage token={token}/>:activeModule==="tasks"&&canViewTasks?<TasksPage token={token}/>:activeModule==="users"&&canManageUsers?<UsersPage token={token} companyId={user.company_id}/>:activeModule==="roles"&&canManageRoles?<RolesPage token={token}/>:activeModule==="audit"&&canViewAudit?<AuditPage token={token}/>:canViewCommandCenter?<CommandCenterPage token={token}/>:<section className="module-panel"><p>You do not have permission to view the Founder Command Center.</p></section>}</main>;
}
function App(){return <AuthGate>{(user,token,signOut)=><FounderConsole user={user} token={token} signOut={signOut}/>}</AuthGate>}
export default App;
