import { describe, expect, it } from "vitest";
import { getBudgetStatus } from "./budgetStatus";

describe("getBudgetStatus", () => {
  it("is neutral when there's no budget set", () => {
    expect(getBudgetStatus(50, null)).toBe("neutral");
    expect(getBudgetStatus(50, 0)).toBe("neutral");
  });

  it("is good comfortably under budget", () => {
    expect(getBudgetStatus(50, 100)).toBe("good");
  });

  it("is warning close to budget", () => {
    expect(getBudgetStatus(85, 100)).toBe("warning");
  });

  it("is critical at or over budget", () => {
    expect(getBudgetStatus(100, 100)).toBe("critical");
    expect(getBudgetStatus(150, 100)).toBe("critical");
  });

  it("treats the 80% boundary as warning, not good", () => {
    expect(getBudgetStatus(80, 100)).toBe("warning");
  });
});
