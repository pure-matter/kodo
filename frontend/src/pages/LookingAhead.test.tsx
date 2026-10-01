import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { LookingAhead } from "./LookingAhead";

vi.mock("../api/client", () => ({
  api: {
    accounts: { list: vi.fn() },
    lookingAhead: { summary: vi.fn() },
    savingsGoals: {
      create: vi.fn(),
      remove: vi.fn(),
      addContribution: vi.fn(),
      listContributions: vi.fn(),
    },
    holdings: { create: vi.fn(), remove: vi.fn(), refreshPrice: vi.fn() },
    uninvestedCash: { log: vi.fn() },
    recurringInvestments: { create: vi.fn(), remove: vi.fn() },
  },
}));

const ACCOUNTS = [
  { id: 1, name: "Fidelity", institution: "Fidelity", type: "investment", parser_type: null, created_at: "2026-01-01T00:00:00Z" },
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
  investment_type: "stock",
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
});

const goalCardName = () => screen.findByText("Emergency fund", { selector: "span.goal-card-name" });

describe("Looking Ahead page", () => {
  it("shows active goals with progress and required monthly contribution", async () => {
    render(<LookingAhead />);
    expect(await goalCardName()).toBeInTheDocument();
    expect(screen.getByText(/\$1,000\.00 \/ \$5,000\.00/)).toBeInTheDocument();
    expect(screen.getByText(/need \$333\.33\/month/)).toBeInTheDocument();
  });

  it("shows achieved goals with a met badge, separate from active goals", async () => {
    render(<LookingAhead />);
    await goalCardName();
    expect(screen.getByText("New laptop")).toBeInTheDocument();
    expect(screen.getByText("✓ met")).toBeInTheDocument();
  });

  it("lists holdings grouped by type with their current value", async () => {
    render(<LookingAhead />);
    expect(await screen.findByText("Apple", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("$1,500.00")).toBeInTheDocument();
  });

  it("creating a goal calls the API with the entered fields", async () => {
    vi.mocked(api.savingsGoals.create).mockResolvedValue(ACTIVE_GOAL);
    const user = userEvent.setup();
    render(<LookingAhead />);

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

    await screen.findByText("Apple", { selector: "td" });
    await user.click(screen.getByText("check price"));

    expect(api.holdings.refreshPrice).toHaveBeenCalledWith(1);
  });
});
