import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { LookingAhead } from "./LookingAhead";

vi.mock("../api/client", () => ({
  api: {
    accounts: { list: vi.fn() },
    lookingAhead: { summary: vi.fn() },
    netWorth: { get: vi.fn() },
    savingsGoals: {
      create: vi.fn(),
      remove: vi.fn(),
      addContribution: vi.fn(),
      listContributions: vi.fn(),
    },
    holdings: { create: vi.fn(), update: vi.fn(), remove: vi.fn(), refreshPrice: vi.fn() },
    uninvestedCash: { log: vi.fn() },
    recurringInvestments: { create: vi.fn(), remove: vi.fn() },
  },
}));

const ACCOUNTS = [
  { id: 1, name: "Fidelity", institution: "Fidelity", type: "investment" as const, parser_type: null, created_at: "2026-01-01T00:00:00Z" },
];

const ACTIVE_GOAL = {
  id: 1,
  name: "Emergency fund",
  target_amount: "5000.00",
  target_date: "2027-01-01",
  linked_account_id: null,
  manual_apy: null,
  created_at: "2026-01-01T00:00:00Z",
  achieved_at: null,
  contributed: "1000.00",
  required_monthly_contribution: "333.33",
};

const ACHIEVED_GOAL = {
  ...ACTIVE_GOAL,
  id: 2,
  name: "New laptop",
  target_amount: "1000.00",
  target_date: null,
  achieved_at: "2026-05-01T00:00:00Z",
  contributed: "1000.00",
  required_monthly_contribution: null,
};

const HOLDING = {
  id: 1,
  account_id: 1,
  investment_type: "stock" as const,
  name: "Apple",
  symbol: "AAPL",
  shares: "10",
  cost_basis: "100.00",
  purchase_date: "2025-01-01",
  current_price: "150.00",
  current_price_updated_at: "2026-01-01T00:00:00Z",
  manual_value: null,
  manual_apy: null,
  projection_years: null,
  target_projected_value: null,
  current_value: "1500.00",
  computed_projected_value: null,
};

const NET_WORTH = { as_of: "2026-10-01", assets: "10000", liabilities: "2000", net_worth: "8000" };

const SUMMARY = {
  goals: [ACTIVE_GOAL],
  achieved_goals: [ACHIEVED_GOAL],
  holdings: [HOLDING],
  by_type: [{ label: "stock", value: "1500.00", percent_of_total: "100.00" }],
  by_account: [{ label: "Fidelity", value: "1500.00", percent_of_total: "100.00" }],
  uninvested_cash: [],
  recurring_investments: [],
  total_portfolio_value: "1500.00",
};

beforeEach(() => {
  vi.mocked(api.accounts.list).mockResolvedValue(ACCOUNTS);
  vi.mocked(api.lookingAhead.summary).mockResolvedValue(SUMMARY);
  vi.mocked(api.netWorth.get).mockResolvedValue(NET_WORTH);
});

const goalCardName = () => screen.findByText("Emergency fund", { selector: "span.goal-card-name" });

async function goToTab(user: ReturnType<typeof userEvent.setup>, label: "Savings" | "Investments") {
  await screen.findByText("Net worth");
  await user.click(screen.getByText(label));
}

describe("Looking Ahead page", () => {
  it("shows net worth and the portfolio breakdown in the Overview tab by default", async () => {
    render(<LookingAhead />);
    expect(await screen.findByText("$8,000.00")).toBeInTheDocument();
    expect(screen.getByText("Portfolio breakdown")).toBeInTheDocument();
    expect(screen.getByText(/Total portfolio value: \$1,500\.00/)).toBeInTheDocument();
  });

  it("shows active goals with progress and required monthly contribution on the Savings tab", async () => {
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Savings");

    expect(await goalCardName()).toBeInTheDocument();
    expect(screen.getByText(/\$1,000\.00 \/ \$5,000\.00/)).toBeInTheDocument();
    expect(screen.getByText(/need \$333\.33\/month/)).toBeInTheDocument();
  });

  it("shows achieved goals with a met badge, separate from active goals", async () => {
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Savings");
    await goalCardName();

    expect(screen.getByText("New laptop")).toBeInTheDocument();
    expect(screen.getByText("✓ met")).toBeInTheDocument();
  });

  it("lists holdings grouped by type with their current value on the Investments tab", async () => {
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Investments");

    expect(await screen.findByText("Apple", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("$1,500.00")).toBeInTheDocument();
  });

  it("flags a holding's value as a rough estimate when there's no live price or manual override", async () => {
    const unpriced = {
      ...HOLDING,
      id: 2,
      name: "Fidelity low priced",
      symbol: "FLPSX",
      current_price: null,
      current_price_updated_at: null,
      current_value: "1000.00",
    };
    vi.mocked(api.lookingAhead.summary).mockResolvedValue({ ...SUMMARY, holdings: [unpriced] });
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Investments");

    await screen.findByText("Fidelity low priced", { selector: "td" });
    expect(screen.getByText("(rough estimate)")).toBeInTheDocument();
  });

  it("does not flag a holding's value once a manual override is set", async () => {
    const overridden = { ...HOLDING, current_price: null, current_price_updated_at: null, manual_value: "6000.00" };
    vi.mocked(api.lookingAhead.summary).mockResolvedValue({ ...SUMMARY, holdings: [overridden] });
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Investments");

    await screen.findByText("Apple", { selector: "td" });
    expect(screen.queryByText("(rough estimate)")).not.toBeInTheDocument();
  });

  it("editing a holding's manual value calls the API with the override", async () => {
    vi.mocked(api.holdings.update).mockResolvedValue({ ...HOLDING, manual_value: "9500.00" });
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Investments");

    await screen.findByText("Apple", { selector: "td" });
    await user.click(screen.getByText("manage"));
    const editForm = screen.getByText("Edit holding").closest("div")!;
    await user.type(within(editForm).getByPlaceholderText("Current total value (optional)"), "9500");
    await user.click(within(editForm).getByText("Save"));

    await waitFor(() =>
      expect(api.holdings.update).toHaveBeenCalledWith(1, expect.objectContaining({ manual_value: "9500" })),
    );
  });

  it("creating a goal calls the API with the entered fields", async () => {
    vi.mocked(api.savingsGoals.create).mockResolvedValue(ACTIVE_GOAL);
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Savings");

    await goalCardName();
    await user.type(screen.getByPlaceholderText("Goal name"), "House down payment");
    await user.type(screen.getByPlaceholderText("Target amount"), "20000");
    await user.click(screen.getByText("Add goal"));

    await waitFor(() =>
      expect(api.savingsGoals.create).toHaveBeenCalledWith(
        expect.objectContaining({ name: "House down payment", target_amount: "20000" }),
      ),
    );
  });

  it("checking a holding's price calls refreshPrice with its id", async () => {
    vi.mocked(api.holdings.refreshPrice).mockResolvedValue(HOLDING);
    const user = userEvent.setup();
    render(<LookingAhead />);
    await goToTab(user, "Investments");

    await screen.findByText("Apple", { selector: "td" });
    await user.click(screen.getByText("check price"));

    expect(api.holdings.refreshPrice).toHaveBeenCalledWith(1);
  });
});
