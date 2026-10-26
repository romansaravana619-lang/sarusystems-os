import { useState } from "react";
import AuthGate from "./features/auth/AuthGate";
import AuditPage from "./features/audit/AuditPage";
import ClientsPage from "./features/clients/ClientsPage";
import CommandCenterPage from "./features/command-center/CommandCenterPage";
import CompanyPage from "./features/company/CompanyPage";
import CRMPage from "./features/crm/CRMPage";
import FreelancersPage from "./features/freelancers/FreelancersPage";
import FreelancerWorkPage from "./features/freelancer-work/FreelancerWorkPage";
import MarketingPage from "./features/marketing/MarketingPage";
import ContentPage from "./features/content/ContentPage";
import SocialMediaPage from "./features/social-media/SocialMediaPage";
import ProductManagementPage from "./features/products/ProductManagementPage";
import DocumentsKnowledgePage from "./features/documents/DocumentsKnowledgePage";
import RulesEnginePage from "./features/rules/RulesEnginePage";
import ProjectsPage from "./features/projects/ProjectsPage";
import RolesPage from "./features/roles/RolesPage";
import SalesPage from "./features/sales/SalesPage";
import ServicesPage from "./features/services/ServicesPage";
import TasksPage from "./features/tasks/TasksPage";
import UsersPage from "./features/users/UsersPage";
import type { MeResponse } from "./services/api";
type Module = "command"|"company"|"crm"|"sales"|"clients"|"services"|"projects"|"tasks"|"freelancers"|"freelancer-work"|"marketing"|"content"|"social-media"|"products"|"documents"|"rules-engine"|"users"|"roles"|"audit";
function FounderConsole({user,token,signOut}:{user:MeResponse;token:string;signOut:()=>Promise<void>}){
 const [activeModule,setActiveModule]=useState<Module>("command"); const can=(p:string)=>user.permissions.includes(p); const go=(m:Module)=>setActiveModule(m===activeModule?"command":m);
 const nav:[[Module,string,string]]|any=[["command","Command Center","command_center.view"],["company","Company Core","company.view"],["crm","CRM","crm.prospects.view"],["sales","Sales","sales.dashboard.view"],["clients","Clients","clients.view"],["services","Services","services.view"],["projects","Projects","projects.view"],["tasks","Tasks","tasks.view"],["freelancers","Freelancers","freelancers.view"],["freelancer-work","Freelancer Work","freelancer_work.view"],["marketing","Marketing","marketing.dashboard.view"],["content","Content","content.dashboard.view"],["social-media","Social Media","social_media.dashboard.view"],["products","Products","products.dashboard.view"],["documents","Documents & Knowledge","documents.dashboard.view"],["rules-engine","SOP & Business Rules","rules_engine.dashboard.view"],["users","Users","users.view"],["roles","Roles & Permissions","roles.view"],["audit","Audit","audit.view"]];
 const content=activeModule==="company"&&can("company.view")?<CompanyPage token={token}/>:activeModule==="crm"&&can("crm.prospects.view")?<CRMPage token={token}/>:activeModule==="sales"&&can("sales.dashboard.view")?<SalesPage token={token}/>:activeModule==="clients"&&can("clients.view")?<ClientsPage token={token}/>:activeModule==="services"&&can("services.view")?<ServicesPage token={token}/>:activeModule==="projects"&&can("projects.view")?<ProjectsPage token={token}/>:activeModule==="tasks"&&can("tasks.view")?<TasksPage token={token}/>:activeModule==="freelancers"&&can("freelancers.view")?<FreelancersPage token={token}/>:activeModule==="freelancer-work"&&can("freelancer_work.view")?<FreelancerWorkPage token={token}/>:activeModule==="marketing"&&can("marketing.dashboard.view")?<MarketingPage token={token}/>:activeModule==="content"&&can("content.dashboard.view")?<ContentPage token={token}/>:activeModule==="social-media"&&can("social_media.dashboard.view")?<SocialMediaPage token={token}/>:activeModule==="products"&&can("products.dashboard.view")?<ProductManagementPage token={token}/>:activeModule==="documents"&&can("documents.dashboard.view")?<DocumentsKnowledgePage token={token}/>:activeModule==="rules-engine"&&can("rules_engine.dashboard.view")?<RulesEnginePage token={token}/>:activeModule==="users"&&can("users.view")?<UsersPage token={token} companyId={user.company_id}/>:activeModule==="roles"&&can("roles.view")?<RolesPage token={token}/>:activeModule==="audit"&&can("audit.view")?<AuditPage token={token}/>:can("command_center.view")?<CommandCenterPage token={token}/>:<section className="module-panel"><p>You do not have permission to view the Founder Command Center.</p></section>;
 return <main className="console-shell"><header className="console-header"><div><p className="eyebrow">SARU SYSTEMS</p><h1>Founder Command Center</h1></div><div className="header-actions">{nav.filter((x:[Module,string,string])=>can(x[2])).map(([m,label]:[Module,string,string])=><button className="secondary-button" type="button" key={m} onClick={()=>go(m)}>{label}</button>)}<button className="secondary-button" type="button" onClick={()=>void signOut()}>Sign out</button></div></header>{content}</main>
}
function App(){return <AuthGate>{(user,token,signOut)=><FounderConsole user={user} token={token} signOut={signOut}/>}</AuthGate>}
export default App;
