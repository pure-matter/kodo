export type BudgetStatus = "good" | "warning" | "critical" | "neutral";

/** How much of a category's budget has been used this month.
 * No budget set at all -> neutral (nothing to compare against). */
export function getBudgetStatus(spent: number, budgeted: number | null): BudgetStatus {
  if (budgeted === null || budgeted === 0) return "neutral";
  const ratio = spent / budgeted;
  if (ratio < 0.8) return "good";
  if (ratio < 1.0) return "warning";
  return "critical";
}

export const STATUS_COLORS: Record<BudgetStatus, string> = {
  good: "var(--status-good)",
  warning: "var(--status-warning)",
  critical: "var(--status-critical)",
  neutral: "var(--text-muted)",
};
