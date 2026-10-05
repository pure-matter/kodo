export type AccountType = "checking" | "savings" | "credit" | "loan" | "investment";
export type CategoryGroup = "needs" | "wants" | "income" | "transfer";
export type InvestmentType = "stock" | "etf" | "retirement_401k" | "roth_ira" | "real_estate" | "other";
export type RecurringFrequency = "weekly" | "biweekly" | "monthly";

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
  is_reviewed: boolean;
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

export interface AvailableMonth {
  year: number;
  month: number;
}

export interface IncomeSummary {
  year: number;
  month: number;
  income: string;
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

export interface Holding {
  id: number;
  account_id: number;
  investment_type: InvestmentType;
  name: string;
  symbol: string | null;
  shares: string | null;
  cost_basis: string;
  purchase_date: string | null;
  current_price: string | null;
  current_price_updated_at: string | null;
  manual_value: string | null;
  manual_apy: string | null;
  projection_years: number | null;
  target_projected_value: string | null;
  current_value: string;
  computed_projected_value: string | null;
}

export interface SavingsGoal {
  id: number;
  name: string;
  target_amount: string;
  target_date: string | null;
  linked_account_id: number | null;
  manual_apy: string | null;
  created_at: string;
  achieved_at: string | null;
  contributed: string;
  required_monthly_contribution: string | null;
}

export interface GoalContribution {
  id: number;
  goal_id: number;
  date: string;
  amount: string;
}

export interface RecurringInvestment {
  id: number;
  name: string;
  amount: string;
  frequency: RecurringFrequency;
  goal_id: number | null;
  holding_id: number | null;
  active: boolean;
}

export interface UninvestedCash {
  id: number;
  account_id: number;
  date: string;
  amount: string;
}

export interface PortfolioSlice {
  label: string;
  value: string;
  percent_of_total: string;
}

export interface LookingAheadSummary {
  goals: SavingsGoal[];
  achieved_goals: SavingsGoal[];
  holdings: Holding[];
  by_type: PortfolioSlice[];
  by_account: PortfolioSlice[];
  uninvested_cash: UninvestedCash[];
  recurring_investments: RecurringInvestment[];
  total_portfolio_value: string;
}
