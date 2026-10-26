export type FinanceDashboard = {
  revenue: number;
  expenses: number;
  outstanding: number;
  freelancer_payments: number;
  project_profitability: number;
};

export type PaymentMilestone = {
  id: string;
  name: string;
  amount: number;
  paid_amount: number;
  due_date?: string | null;
  status: string;
  client_id?: string | null;
  project_id?: string | null;
};

const request = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, { credentials: "include", ...options, headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) } });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

export const financeApi = {
  dashboard: () => request<FinanceDashboard>("/finance/dashboard"),
  milestones: () => request<PaymentMilestone[]>("/finance/milestones"),
};
