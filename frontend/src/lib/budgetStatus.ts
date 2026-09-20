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

/** How close a savings allocation is to its monthly target. Deliberately
 * the inverse of getBudgetStatus: for spend, low-relative-to-budget is
 * good (room left); for savings, low-relative-to-target is the opposite
 * of good (behind on contributing), and meeting or exceeding the target
 * is what "good" means here. */
export function getSavingsStatus(contributed: number, target: number | null): BudgetStatus {
  if (target === null || target === 0) return "neutral";
  const ratio = contributed / target;
  if (ratio >= 1.0) return "good";
  if (ratio >= 0.5) return "warning";
  return "critical";
}

export const STATUS_COLORS: Record<BudgetStatus, string> = {
  good: "var(--status-good)",
  warning: "var(--status-warning)",
  critical: "var(--status-critical)",
  neutral: "var(--text-muted)",
};
