import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { Categories } from "./Categories";

vi.mock("../api/client", () => ({
  api: {
    categories: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
    categoryRules: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
    reports: { budgetSummary: vi.fn(), monthlyHistory: vi.fn(), archiveMonth: vi.fn() },
  },
}));

const CATEGORIES = [
  { id: 1, name: "Groceries", group: "needs" as const, monthly_budget: "400" },
  { id: 2, name: "Entertainment", group: "wants" as const, monthly_budget: "150" },
];

const RULES = [{ id: 1, pattern: "TRADER JOE", category_id: 1, priority: 100 }];

// "Groceries" is both category id=1's name AND the default selection in the
// add-rule/rule-row <select>s, so getByDisplayValue alone is ambiguous -
// this narrows to the actual <input> (the editable category name field).
function getCategoryNameInput(name: string): HTMLInputElement {
  return screen
    .getAllByDisplayValue(name)
    .find((el): el is HTMLInputElement => el.tagName === "INPUT")!;
}

beforeEach(() => {
  vi.mocked(api.categories.list).mockResolvedValue(CATEGORIES);
  vi.mocked(api.categoryRules.list).mockResolvedValue(RULES);
  vi.mocked(api.reports.budgetSummary).mockResolvedValue([]);
  vi.mocked(api.reports.monthlyHistory).mockResolvedValue([]);
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("Categories page", () => {
  it("lists categories grouped by Needs/Wants", async () => {
    render(<Categories />);
    await screen.findByRole("heading", { name: "Needs" });
    expect(getCategoryNameInput("Groceries")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Entertainment")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Wants" })).toBeInTheDocument();
  });

  it("adding a category calls the API", async () => {
    vi.mocked(api.categories.create).mockResolvedValue({
      id: 3,
      name: "Pets",
      group: "wants",
      monthly_budget: "50",
    });
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByRole("heading", { name: "Needs" });
    await user.type(screen.getByPlaceholderText("Category name"), "Pets");
    await user.type(screen.getByPlaceholderText("Monthly budget (optional)"), "50");
    await user.click(screen.getByText("Add category"));

    expect(api.categories.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Pets", monthly_budget: "50" }),
    );
    expect(await screen.findByDisplayValue("Pets")).toBeInTheDocument();
  });

  it("editing a category's budget saves via the API", async () => {
    vi.mocked(api.categories.update).mockResolvedValue({ ...CATEGORIES[0], monthly_budget: "500" });
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByRole("heading", { name: "Needs" });
    const budgetInput = screen.getByDisplayValue("400");
    await user.clear(budgetInput);
    await user.type(budgetInput, "500");
    await user.click(screen.getAllByText("save")[0]);

    expect(api.categories.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ monthly_budget: "500" }),
    );
  });

  it("deleting a category asks for confirmation and calls the API", async () => {
    vi.mocked(api.categories.remove).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByRole("heading", { name: "Needs" });
    await user.click(screen.getAllByText("delete")[0]);

    expect(window.confirm).toHaveBeenCalled();
    expect(api.categories.remove).toHaveBeenCalledWith(1);
  });

  it("shows a server error when deletion is blocked (category in use)", async () => {
    vi.mocked(api.categories.remove).mockRejectedValue(
      new Error("400: This category still has transactions assigned to it"),
    );
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByRole("heading", { name: "Needs" });
    await user.click(screen.getAllByText("delete")[0]);

    expect(await screen.findByText(/still has transactions/)).toBeInTheDocument();
  });

  it("lists rules and adding one calls the API", async () => {
    vi.mocked(api.categoryRules.create).mockResolvedValue({
      id: 2,
      pattern: "SHELL",
      category_id: 1,
      priority: 100,
    });
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByDisplayValue("TRADER JOE");
    await user.type(screen.getByPlaceholderText("Match text"), "SHELL");
    await user.click(screen.getByText("Add rule"));

    expect(api.categoryRules.create).toHaveBeenCalledWith(
      expect.objectContaining({ pattern: "SHELL" }),
    );
    expect(await screen.findByDisplayValue("SHELL")).toBeInTheDocument();
  });

  it("deleting a rule calls the API", async () => {
    vi.mocked(api.categoryRules.remove).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByDisplayValue("TRADER JOE");
    await user.click(screen.getAllByText("delete").at(-1)!);

    expect(api.categoryRules.remove).toHaveBeenCalledWith(1);
  });

  it("archiving a month confirms, then calls the API with the selected year/month", async () => {
    vi.mocked(api.reports.archiveMonth).mockResolvedValue([]);
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByRole("heading", { name: "Needs" });
    await user.click(screen.getByText("Archive & clear month"));

    expect(window.confirm).toHaveBeenCalled();
    expect(api.reports.archiveMonth).toHaveBeenCalled();
    expect(await screen.findByText(/Archived/)).toBeInTheDocument();
  });

  it("does not call the archive API if the user cancels the confirmation", async () => {
    vi.mocked(window.confirm).mockReturnValue(false);
    const user = userEvent.setup();
    render(<Categories />);

    await screen.findByRole("heading", { name: "Needs" });
    await user.click(screen.getByText("Archive & clear month"));

    expect(api.reports.archiveMonth).not.toHaveBeenCalled();
  });
});
