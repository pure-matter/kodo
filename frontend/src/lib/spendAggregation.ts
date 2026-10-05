import type { BudgetSummaryItem, SavingsProgress } from "../api/types";

export interface SpendRow {
  name: string;
  spent: number;
  budgeted: number | null;
  /** "savings" gets the inverse status logic (meeting/exceeding the
   * target is good, not critical) - see getSavingsStatus. Distinguishing
   * by this field rather than matching on `name === "Savings"` keeps the
   * rendering layer from depending on a magic label string. */
  kind: "spend" | "savings";
  /** Set only on a single-category row (toCategoryRows) - lets the chart
   * link a bar to that category's filtered transaction list. Bucket rows
   * (aggregateByBucket) roll up multiple categories, so there's no one
   * category to link to. */
  category_id: number | null;
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
      kind: "spend",
      category_id: null,
    };
  };

  const savingsContributed = savings.reduce((sum, s) => sum + Number(s.contributed), 0);
  const savingsTarget = savings.reduce((sum, s) => sum + Number(s.monthly_target), 0);

  return [
    sumGroup("needs"),
    sumGroup("wants"),
    {
      name: "Savings",
      spent: savingsContributed,
      budgeted: savingsTarget || null,
      kind: "savings",
      category_id: null,
    },
  ];
}

export function toCategoryRows(budget: BudgetSummaryItem[]): SpendRow[] {
  return budget
    .map((r) => ({
      name: r.category_name,
      spent: Number(r.spent),
      budgeted: r.budgeted !== null ? Number(r.budgeted) : null,
      kind: "spend" as const,
      category_id: r.category_id,
    }))
    .filter((r) => r.spent > 0)
    .sort((a, b) => b.spent - a.spent);
}
