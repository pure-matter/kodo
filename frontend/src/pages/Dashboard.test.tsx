import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { Dashboard } from "./Dashboard";

vi.mock("../api/client", () => ({
  api: {
    reports: {
      budgetSummary: vi.fn(),
      availableMonths: vi.fn(),
      incomeSummary: vi.fn(),
      monthlyHistory: vi.fn(),
      bucketHistory: vi.fn(),
      reallocations: { list: vi.fn(), create: vi.fn(), remove: vi.fn() },
    },
    savings: { progress: vi.fn() },
  },
}));

const BUDGET = [
  { category_id: 1, category_name: "Groceries", group: "needs" as const, budgeted: "400", spent: "150" },
  { category_id: 2, category_name: "Entertainment", group: "wants" as const, budgeted: "150", spent: "50" },
];

const SAVINGS = [{ allocation_id: 1, name: "Robinhood", monthly_target: "150", contributed: "150" }];

// "Groceries" also appears as an option in the Reallocate budget selects -
// this scopes the wait condition to the actual budget-row label.
const groceriesLabel = () => screen.findByText("Groceries", { selector: "span.progress-label" });

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  const today = new Date();
  vi.mocked(api.reports.availableMonths).mockResolvedValue([
    { year: today.getFullYear(), month: today.getMonth() + 1 },
    { year: today.getFullYear(), month: today.getMonth() || 12 },
  ]);
  vi.mocked(api.reports.budgetSummary).mockResolvedValue(BUDGET);
  vi.mocked(api.reports.incomeSummary).mockResolvedValue({
    year: today.getFullYear(),
    month: today.getMonth() + 1,
    income: "3000",
  });
  vi.mocked(api.savings.progress).mockResolvedValue(SAVINGS);
  vi.mocked(api.reports.monthlyHistory).mockResolvedValue([
    { year: 2026, month: 9, category_id: 1, category_name: "Groceries", spent: "150" },
  ]);
  vi.mocked(api.reports.bucketHistory).mockResolvedValue([
    { year: 2026, month: 9, needs: "150", wants: "50", savings: "150" },
  ]);
  vi.mocked(api.reports.reallocations.list).mockResolvedValue([]);
});

describe("Dashboard page", () => {
  it("shows spending vs. income and budget groups in the Overview tab by default", async () => {
    renderDashboard();
    expect(await screen.findByText("$2,800.00")).toBeInTheDocument();
    expect(screen.getByText("$200.00 spent · $3,000.00 income")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Wants" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Savings" })).toBeInTheDocument();
    expect(await groceriesLabel()).toBeInTheDocument();
  });

  it("shows each bucket's spent/planned total", async () => {
    renderDashboard();
    await groceriesLabel();

    const needsCard = screen.getByRole("heading", { name: "Needs" }).closest("section")!;
    expect(within(needsCard).getByText("$150.00 spent / $400.00 planned")).toBeInTheDocument();

    const savingsCard = screen.getByRole("heading", { name: "Savings" }).closest("section")!;
    expect(within(savingsCard).getByText("$150.00 spent / $150.00 planned")).toBeInTheDocument();
  });

  it("defaults the month picker to the current month", async () => {
    renderDashboard();
    await groceriesLabel();

    const today = new Date();
    const expectedLabel = today.toLocaleString("en-US", { month: "long", year: "numeric" });
    expect(screen.getByRole("combobox", { name: "Month" })).toHaveValue(`${today.getFullYear()}-${today.getMonth() + 1}`);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });

  it("switching the month re-fetches budget summary and savings progress for it", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await groceriesLabel();

    const today = new Date();
    const otherMonth = today.getMonth() || 12;
    await user.selectOptions(screen.getByRole("combobox", { name: "Month" }), `${today.getFullYear()}-${otherMonth}`);

    await waitFor(() => expect(api.reports.budgetSummary).toHaveBeenCalledWith(today.getFullYear(), otherMonth));
    expect(api.savings.progress).toHaveBeenCalledWith(today.getFullYear(), otherMonth);
  });

  it("switching to the Spending tab shows the spend chart with its segmented control", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await groceriesLabel();

    await user.click(screen.getByText("Spending"));

    const spendCard = (await screen.findByText("Spending by category")).closest("section")!;
    const byCategoryButton = within(spendCard).getByText("By category");
    const byBucketButton = within(spendCard).getByText("By bucket");
    expect(byCategoryButton).toHaveClass("segmented-active");

    await user.click(byBucketButton);
    expect(byBucketButton).toHaveClass("segmented-active");
    expect(byCategoryButton).not.toHaveClass("segmented-active");
  });

  it("shows existing reallocations for the month with an undo link", async () => {
    vi.mocked(api.reports.reallocations.list).mockResolvedValue([
      {
        id: 1,
        year: 2026,
        month: 9,
        from_category_id: 2,
        from_category_name: "Entertainment",
        to_category_id: 1,
        to_category_name: "Groceries",
        amount: "50.00",
      },
    ]);
    renderDashboard();
    await groceriesLabel();

    expect(await screen.findByText(/\$50\.00: Entertainment/)).toBeInTheDocument();
    expect(screen.getByText("undo")).toBeInTheDocument();
  });

  it("submitting the reallocation form calls the API with the selected categories and amount", async () => {
    vi.mocked(api.reports.reallocations.create).mockResolvedValue({
      id: 2,
      year: 2026,
      month: 9,
      from_category_id: 2,
      to_category_id: 1,
      from_category_name: "Entertainment",
      to_category_name: "Groceries",
      amount: "25.00",
    });
    const user = userEvent.setup();
    renderDashboard();
    await groceriesLabel();

    const reallocateCard = screen.getByText("Reallocate budget").closest("section")!;
    await user.type(within(reallocateCard).getByPlaceholderText("Amount"), "25");
    await user.click(within(reallocateCard).getByText("Reallocate"));

    await waitFor(() =>
      expect(api.reports.reallocations.create).toHaveBeenCalledWith(
        expect.objectContaining({ from_category_id: 1, to_category_id: 2, amount: "25" }),
      ),
    );
  });

  it("clicking undo on a reallocation removes it and refreshes the budget", async () => {
    vi.mocked(api.reports.reallocations.list).mockResolvedValue([
      {
        id: 1,
        year: 2026,
        month: 9,
        from_category_id: 2,
        from_category_name: "Entertainment",
        to_category_id: 1,
        to_category_name: "Groceries",
        amount: "50.00",
      },
    ]);
    vi.mocked(api.reports.reallocations.remove).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderDashboard();
    await groceriesLabel();

    await user.click(await screen.findByText("undo"));

    expect(api.reports.reallocations.remove).toHaveBeenCalledWith(1);
  });

  it("the Spending tab's history chart segmented control toggles between category and bucket views", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await groceriesLabel();
    await user.click(screen.getByText("Spending"));

    const historyCard = (await screen.findByText("Spending history")).closest("section")!;
    await within(historyCard).findByText("Groceries");

    const byCategoryButton = within(historyCard).getByText("By category");
    const byBucketButton = within(historyCard).getByText("By bucket");
    expect(byCategoryButton).toHaveClass("segmented-active");

    await user.click(byBucketButton);
    expect(byBucketButton).toHaveClass("segmented-active");
    expect(byCategoryButton).not.toHaveClass("segmented-active");
  });
});
