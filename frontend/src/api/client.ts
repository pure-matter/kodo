import type {
  Account,
  BudgetSummaryItem,
  Category,
  CategoryRule,
  ImportSummary,
  NetWorth,
  SavingsAllocation,
  SavingsProgress,
  Transaction,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  accounts: {
    list: () => request<Account[]>("/accounts"),
    create: (data: { name: string; institution: string; type: string; parser_type?: string | null }) =>
      request<Account>("/accounts", { method: "POST", body: JSON.stringify(data) }),
  },
  categories: {
    list: () => request<Category[]>("/categories"),
  },
  categoryRules: {
    list: () => request<CategoryRule[]>("/category-rules"),
  },
  transactions: {
    list: (params?: { account_id?: number; category_id?: number; uncategorized_only?: boolean }) => {
      const query = new URLSearchParams();
      if (params?.account_id != null) query.set("account_id", String(params.account_id));
      if (params?.category_id != null) query.set("category_id", String(params.category_id));
      if (params?.uncategorized_only) query.set("uncategorized_only", "true");
      const qs = query.toString();
      return request<Transaction[]>(`/transactions${qs ? `?${qs}` : ""}`);
    },
    recategorize: (
      id: number,
      data: { category_id: number; create_rule?: boolean; pattern?: string },
    ) => request<Transaction>(`/transactions/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    create: (data: { account_id: number; date: string; description: string; amount: string; category_id?: number | null }) =>
      request<Transaction>("/transactions", { method: "POST", body: JSON.stringify(data) }),
  },
  imports: {
    upload: (accountId: number, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<ImportSummary>(`/accounts/${accountId}/import`, {
        method: "POST",
        body: formData,
      });
    },
  },
  reports: {
    budgetSummary: (year: number, month: number) =>
      request<BudgetSummaryItem[]>(`/reports/budget-summary?year=${year}&month=${month}`),
  },
  savings: {
    list: () => request<SavingsAllocation[]>("/savings-allocations"),
    progress: (year: number, month: number) =>
      request<SavingsProgress[]>(`/savings-allocations/progress?year=${year}&month=${month}`),
  },
  netWorth: {
    get: () => request<NetWorth>("/net-worth"),
    addBalanceSnapshot: (accountId: number, data: { date: string; balance: string }) =>
      request(`/accounts/${accountId}/balance-snapshots`, { method: "POST", body: JSON.stringify(data) }),
  },
};
