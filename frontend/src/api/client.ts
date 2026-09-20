import type {
  Account,
  BucketHistoryItem,
  BudgetSummaryItem,
  Category,
  CategoryGroup,
  CategoryRule,
  ImportSummary,
  MonthlyHistoryItem,
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
    const body = await response.text();
    // FastAPI error responses are {"detail": "..."} - surface just the
    // message when present, instead of raw JSON, since this text is shown
    // directly to the user in several places.
    let message = body;
    try {
      const parsed = JSON.parse(body);
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // not JSON - fall back to the raw body
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  accounts: {
    list: () => request<Account[]>("/accounts"),
    create: (data: { name: string; institution: string; type: string; parser_type?: string | null }) =>
      request<Account>("/accounts", { method: "POST", body: JSON.stringify(data) }),
    update: (
      id: number,
      data: Partial<{ name: string; institution: string; type: string; parser_type: string | null }>,
    ) => request<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  },
  categories: {
    list: () => request<Category[]>("/categories"),
    create: (data: { name: string; group: CategoryGroup; monthly_budget?: string | null }) =>
      request<Category>("/categories", { method: "POST", body: JSON.stringify(data) }),
    update: (
      id: number,
      data: Partial<{ name: string; group: CategoryGroup; monthly_budget: string | null }>,
    ) => request<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/categories/${id}`, { method: "DELETE" }),
  },
  categoryRules: {
    list: () => request<CategoryRule[]>("/category-rules"),
    create: (data: { pattern: string; category_id: number; priority?: number }) =>
      request<CategoryRule>("/category-rules", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<{ pattern: string; category_id: number; priority: number }>) =>
      request<CategoryRule>(`/category-rules/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/category-rules/${id}`, { method: "DELETE" }),
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
    monthlyHistory: (months: number) =>
      request<MonthlyHistoryItem[]>(`/reports/monthly-history?months=${months}`),
    bucketHistory: (months: number) =>
      request<BucketHistoryItem[]>(`/reports/bucket-history?months=${months}`),
    archiveMonth: (year: number, month: number) =>
      request<BudgetSummaryItem[]>("/reports/archive-month", {
        method: "POST",
        body: JSON.stringify({ year, month }),
      }),
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
