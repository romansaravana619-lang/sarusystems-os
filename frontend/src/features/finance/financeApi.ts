import { apiRequest } from "../../services/http";

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
export type ProjectProfitability = { project_id: string; project_name: string; revenue: number; expenses: number; profitability: number };
export type PaymentMilestone = { id: string; name: string; amount: number; paid_amount: number; due_date?: string | null; status: string; client_id?: string | null; project_id?: string | null };
export type Transaction = { id: string; transaction_type: string; category: string; description: string; amount: number; transaction_date: string; status: string; client_id?: string | null; project_id?: string | null; freelancer_id?: string | null };

export const financeApi = {
  dashboard: (token: string) => apiRequest<FinanceDashboard>(token, "/finance/dashboard"),
  milestones: (token: string) => apiRequest<PaymentMilestone[]>(token, "/finance/milestones"),
  transactions: (token: string) => apiRequest<Transaction[]>(token, "/finance/transactions"),
  profitability: (token: string) => apiRequest<ProjectProfitability[]>(token, "/finance/profitability"),
  createTransaction: (token: string, payload: unknown) => apiRequest<Transaction>(token, "/finance/transactions", { method: "POST", body: JSON.stringify(payload) }),
  createMilestone: (token: string, payload: unknown) => apiRequest<PaymentMilestone>(token, "/finance/milestones", { method: "POST", body: JSON.stringify(payload) }),
  recordPayment: (token: string, id: string, payload: unknown) => apiRequest<PaymentMilestone>(token, `/finance/milestones/${id}/payments`, { method: "POST", body: JSON.stringify(payload) }),
};
