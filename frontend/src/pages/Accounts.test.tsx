import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { Accounts } from "./Accounts";

vi.mock("../api/client", () => ({
  api: {
    accounts: { list: vi.fn(), create: vi.fn() },
    categories: { list: vi.fn() },
    transactions: { create: vi.fn() },
    netWorth: { addBalanceSnapshot: vi.fn() },
  },
}));

const MANUAL_ACCOUNT = {
  id: 1,
  name: "GTBank",
  institution: "Guaranty Trust Bank",
  type: "checking" as const,
  parser_type: null,
  created_at: "2026-01-01T00:00:00Z",
};

const IMPORTED_ACCOUNT = {
  id: 2,
  name: "Checking",
  institution: "Bank of America",
  type: "checking" as const,
  parser_type: "boa_checking",
  created_at: "2026-01-01T00:00:00Z",
};

const CATEGORIES = [{ id: 1, name: "Education", group: "needs" as const, monthly_budget: "250" }];

beforeEach(() => {
  vi.mocked(api.accounts.list).mockResolvedValue([MANUAL_ACCOUNT, IMPORTED_ACCOUNT]);
  vi.mocked(api.categories.list).mockResolvedValue(CATEGORIES);
});

describe("Accounts page - manage panel", () => {
  it("shows a manual transaction form only for accounts with no parser", async () => {
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("GTBank");
    const manageButtons = screen.getAllByText("manage");
    await user.click(manageButtons[0]); // GTBank row

    expect(screen.getByText("Add a transaction")).toBeInTheDocument();
    expect(screen.getByText(/Log a balance/)).toBeInTheDocument();
  });

  it("does not show the manual transaction form for an account with a parser", async () => {
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("Checking");
    const manageButtons = screen.getAllByText("manage");
    await user.click(manageButtons[1]); // BoA checking row

    expect(screen.queryByText("Add a transaction")).not.toBeInTheDocument();
    expect(screen.getByText(/Log a balance/)).toBeInTheDocument();
  });

  it("submitting a manual transaction calls the API with the account id", async () => {
    vi.mocked(api.transactions.create).mockResolvedValue({
      id: 99,
      account_id: 1,
      date: "2026-09-01",
      description: "School fee",
      amount: "-100.00",
      category_id: null,
      source_category_hint: null,
    });
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("GTBank");
    await user.click(screen.getAllByText("manage")[0]);

    await user.type(screen.getByPlaceholderText("Description"), "School fee");
    await user.type(screen.getByPlaceholderText("Amount (negative = spend)"), "-100");
    await user.click(screen.getByText("Add"));

    expect(api.transactions.create).toHaveBeenCalledWith(
      expect.objectContaining({ account_id: 1, description: "School fee", amount: "-100", category_id: null }),
    );
  });

  it("submitting a balance snapshot calls the API for the right account", async () => {
    vi.mocked(api.netWorth.addBalanceSnapshot).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("Checking");
    await user.click(screen.getAllByText("manage")[1]); // BoA checking (has a parser)

    await user.type(screen.getByPlaceholderText("Balance"), "2000");
    await user.click(screen.getByText("Log balance"));

    expect(api.netWorth.addBalanceSnapshot).toHaveBeenCalledWith(
      2,
      expect.objectContaining({ balance: "2000" }),
    );
  });
});
