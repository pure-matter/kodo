import type { BudgetSummaryItem, SavingsProgress } from "../api/types";

export interface SpendRow {
  name: string;
  spent: number;
  budgeted: number | null;
}

/** Rolls category-level budget rows up into three buckets - Needs, Wants,
 * and Savings (from savings allocation progress, not a Category group) -
 * matching the Needs/Wants/Savings shape of the user's original budget
 * spreadsheet. A bucket's budgeted total sums only the categories/
 * allocations that have one set, rather than treating "no budget" as 0. */
export function aggregateByBucket(
  budget: BudgetSummaryItem[],
  savings: SavingsProgress[],
): SpendRow[] {
  const sumGroup = (group: "needs" | "wants"): SpendRow => {
    const rows = budget.filter((r) => r.group === group);
    return {
      name: group === "needs" ? "Needs" : "Wants",
      spent: rows.reduce((sum, r) => sum + Number(r.spent), 0),
      budgeted: rows.reduce((sum, r) => sum + (r.budgeted !== null ? Number(r.budgeted) : 0), 0) || null,
    };
  };

  const savingsContributed = savings.reduce((sum, s) => sum + Number(s.contributed), 0);
  const savingsTarget = savings.reduce((sum, s) => sum + Number(s.monthly_target), 0);

  return [
    sumGroup("needs"),
    sumGroup("wants"),
    { name: "Savings", spent: savingsContributed, budgeted: savingsTarget || null },
  ];
}

export function toCategoryRows(budget: BudgetSummaryItem[]): SpendRow[] {
  return budget
    .map((r) => ({
      name: r.category_name,
      spent: Number(r.spent),
      budgeted: r.budgeted !== null ? Number(r.budgeted) : null,
    }))
    .filter((r) => r.spent > 0)
    .sort((a, b) => b.spent - a.spent);
}
