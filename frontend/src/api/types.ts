export type AccountType = "checking" | "savings" | "credit" | "loan" | "investment";
export type CategoryGroup = "needs" | "wants" | "income" | "transfer";

export interface Account {
  id: number;
  name: string;
  institution: string;
  type: AccountType;
  parser_type: string | null;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  group: CategoryGroup;
  monthly_budget: string | null;
}

export interface CategoryRule {
  id: number;
  pattern: string;
  category_id: number;
  priority: number;
}

export interface Transaction {
  id: number;
  account_id: number;
  date: string;
  description: string;
  amount: string;
  category_id: number | null;
  source_category_hint: string | null;
}

export interface ImportSummary {
  total_in_file: number;
  imported: number;
  skipped_duplicates: number;
}

export interface SavingsAllocation {
  id: number;
  name: string;
  monthly_target: string;
  match_pattern: string | null;
}

export interface SavingsProgress {
  allocation_id: number;
  name: string;
  monthly_target: string;
  contributed: string;
}

export interface BudgetSummaryItem {
  category_id: number;
  category_name: string;
  group: CategoryGroup;
  budgeted: string | null;
  spent: string;
}

export interface NetWorth {
  as_of: string;
  assets: string;
  liabilities: string;
  net_worth: string;
}

export interface MonthlyHistoryItem {
  year: number;
  month: number;
  category_id: number;
  category_name: string;
  spent: string;
}

export interface BucketHistoryItem {
  year: number;
  month: number;
  needs: string;
  wants: string;
  savings: string;
}
