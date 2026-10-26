export type FinanceDashboard = {
  revenue: number;
  expenses: number;
  outstanding: number;
  freelancer_payments: number;
  project_profitability: number;
  software_expenses: number;
  marketing_expenses: number;
  operating_expenses: number;
  project_reports: ProjectProfitability[];
};
export type ProjectProfitability={project_id:string;project_name:string;revenue:number;expenses:number;profitability:number};
export type PaymentMilestone={id:string;name:string;amount:number;paid_amount:number;due_date?:string|null;status:string;client_id?:string|null;project_id?:string|null};
export type Transaction={id:string;transaction_type:string;category:string;description:string;amount:number;transaction_date:string;status:string;client_id?:string|null;project_id?:string|null;freelancer_id?:string|null};

const request=async<T>(token:string,path:string,options?:RequestInit):Promise<T>=>{const response=await fetch(path,{...options,headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json",...(options?.headers??{})}});if(!response.ok)throw new Error(await response.text());return response.json()};
export const financeApi={
 dashboard:(token:string)=>request<FinanceDashboard>(token,"/finance/dashboard"),
 milestones:(token:string)=>request<PaymentMilestone[]>(token,"/finance/milestones"),
 transactions:(token:string)=>request<Transaction[]>(token,"/finance/transactions"),
 profitability:(token:string)=>request<ProjectProfitability[]>(token,"/finance/profitability"),
 createTransaction:(token:string,payload:unknown)=>request<Transaction>(token,"/finance/transactions",{method:"POST",body:JSON.stringify(payload)}),
 createMilestone:(token:string,payload:unknown)=>request<PaymentMilestone>(token,"/finance/milestones",{method:"POST",body:JSON.stringify(payload)}),
 recordPayment:(token:string,id:string,payload:unknown)=>request<PaymentMilestone>(token,`/finance/milestones/${id}/payments`,{method:"POST",body:JSON.stringify(payload)}),
};
