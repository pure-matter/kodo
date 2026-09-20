import { describe, expect, it } from "vitest";
import { aggregateByBucket, toCategoryRows } from "./spendAggregation";

const BUDGET = [
  { category_id: 1, category_name: "Groceries", group: "needs" as const, budgeted: "400", spent: "150" },
  { category_id: 5, category_name: "Housing", group: "needs" as const, budgeted: "1500", spent: "1500" },
  { category_id: 2, category_name: "Entertainment", group: "wants" as const, budgeted: "150", spent: "50" },
  { category_id: 3, category_name: "Misc", group: "wants" as const, budgeted: null, spent: "0" },
];

const SAVINGS = [
  { allocation_id: 1, name: "Robinhood", monthly_target: "150", contributed: "150" },
  { allocation_id: 2, name: "FID", monthly_target: "850", contributed: "400" },
];

describe("aggregateByBucket", () => {
  it("sums spent and budgeted across all categories in each group", () => {
    const result = aggregateByBucket(BUDGET, SAVINGS);
    const needs = result.find((r) => r.name === "Needs")!;
    const wants = result.find((r) => r.name === "Wants")!;

    expect(needs.spent).toBe(1650); // 150 + 1500
    expect(needs.budgeted).toBe(1900); // 400 + 1500
    expect(wants.spent).toBe(50);
    expect(wants.budgeted).toBe(150); // Misc has no budget, contributes 0 not null
  });

  it("builds the Savings bucket from allocation progress, not a category group", () => {
    const result = aggregateByBucket(BUDGET, SAVINGS);
    const savings = result.find((r) => r.name === "Savings")!;

    expect(savings.spent).toBe(550); // 150 + 400 contributed
    expect(savings.budgeted).toBe(1000); // 150 + 850 target
  });

  it("tags Needs/Wants as 'spend' and Savings as 'savings', for inverted status coloring", () => {
    const result = aggregateByBucket(BUDGET, SAVINGS);
    expect(result.find((r) => r.name === "Needs")!.kind).toBe("spend");
    expect(result.find((r) => r.name === "Wants")!.kind).toBe("spend");
    expect(result.find((r) => r.name === "Savings")!.kind).toBe("savings");
  });

  it("returns null budgeted for a bucket where nothing has a budget set", () => {
    const result = aggregateByBucket(
      [{ category_id: 9, category_name: "Books", group: "wants", budgeted: null, spent: "10" }],
      [],
    );
    const wants = result.find((r) => r.name === "Wants")!;
    expect(wants.budgeted).toBeNull();
  });

  it("always returns exactly 3 rows, even with no data", () => {
    expect(aggregateByBucket([], [])).toHaveLength(3);
  });
});

describe("toCategoryRows", () => {
  it("filters out categories with no spend", () => {
    const result = toCategoryRows(BUDGET);
    expect(result.map((r) => r.name)).not.toContain("Misc");
  });

  it("sorts by spend descending", () => {
    const result = toCategoryRows(BUDGET);
    expect(result.map((r) => r.name)).toEqual(["Housing", "Groceries", "Entertainment"]);
  });
});
