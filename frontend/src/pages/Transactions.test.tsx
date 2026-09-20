import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { Transactions } from "./Transactions";

vi.mock("../api/client", () => ({
  api: {
    categories: { list: vi.fn() },
    accounts: { list: vi.fn() },
    transactions: { list: vi.fn(), recategorize: vi.fn(), create: vi.fn() },
  },
}));

const CATEGORIES = [
  { id: 1, name: "Groceries", group: "needs" as const, monthly_budget: "400" },
  { id: 2, name: "Coffee/Dessert", group: "wants" as const, monthly_budget: "40" },
];

const ACCOUNTS = [
  {
    id: 1,
    name: "Checking",
    institution: "BoA",
    type: "checking" as const,
    parser_type: "boa_checking",
    created_at: "2026-01-01T00:00:00Z",
  },
];

const TRANSACTIONS = [
  {
    id: 10,
    account_id: 1,
    date: "2026-09-03",
    description: "SAMPLE GROCERY STORE #123 AUSTIN TX",
    amount: "-150.00",
    category_id: null,
    source_category_hint: null,
  },
];

beforeEach(() => {
  vi.mocked(api.categories.list).mockResolvedValue(CATEGORIES);
  vi.mocked(api.accounts.list).mockResolvedValue(ACCOUNTS);
  vi.mocked(api.transactions.list).mockResolvedValue(TRANSACTIONS);
});

describe("Transactions page", () => {
  it("lists transactions with their descriptions and amounts", async () => {
    render(<Transactions />);
    expect(await screen.findByText(/SAMPLE GROCERY STORE/)).toBeInTheDocument();
    expect(screen.getByText("-$150.00")).toBeInTheDocument();
  });

  it("recategorizing via the dropdown calls the API without creating a rule", async () => {
    vi.mocked(api.transactions.recategorize).mockResolvedValue({
      ...TRANSACTIONS[0],
      category_id: 1,
    });
    const user = userEvent.setup();
    render(<Transactions />);

    await screen.findByText(/SAMPLE GROCERY STORE/);
    const select = screen.getByRole("combobox", { name: "Category" }) as HTMLSelectElement;
    await user.selectOptions(select, "1");

    expect(api.transactions.recategorize).toHaveBeenCalledWith(10, {
      category_id: 1,
      create_rule: false,
      pattern: undefined,
    });
  });

  it("saving a rule sends the edited pattern text, not a silently cleaned merchant name", async () => {
    vi.mocked(api.transactions.recategorize).mockResolvedValue({
      ...TRANSACTIONS[0],
      category_id: 1,
    });
    const user = userEvent.setup();
    render(<Transactions />);

    await screen.findByText(/SAMPLE GROCERY STORE/);
    await user.click(screen.getByText("always categorize like this?"));

    const patternInput = screen.getByDisplayValue("SAMPLE GROCERY STORE #123 AUSTIN TX");
    await user.clear(patternInput);
    await user.type(patternInput, "SAMPLE GROCERY STORE");

    const ruleSelect = screen.getByText("Save rule as category…").closest("select")!;
    await user.selectOptions(ruleSelect, "1");

    await waitFor(() =>
      expect(api.transactions.recategorize).toHaveBeenCalledWith(10, {
        category_id: 1,
        create_rule: true,
        pattern: "SAMPLE GROCERY STORE",
      }),
    );
  });

  it("adding a new transaction calls the API with the selected account and category", async () => {
    vi.mocked(api.transactions.create).mockResolvedValue({
      id: 20,
      account_id: 1,
      date: "2026-09-05",
      description: "Cash tip",
      amount: "-10.00",
      category_id: 2,
      source_category_hint: null,
    });
    const user = userEvent.setup();
    render(<Transactions />);

    await screen.findByText(/SAMPLE GROCERY STORE/);
    await user.type(screen.getByPlaceholderText("Description"), "Cash tip");
    await user.type(screen.getByPlaceholderText("Amount (negative = spend)"), "-10");
    await user.selectOptions(screen.getByRole("combobox", { name: "New transaction category" }), "2");
    await user.click(screen.getByText("Add transaction"));

    expect(api.transactions.create).toHaveBeenCalledWith(
      expect.objectContaining({ account_id: 1, description: "Cash tip", amount: "-10", category_id: 2 }),
    );
    expect(await screen.findByText("Cash tip")).toBeInTheDocument();
  });
});
