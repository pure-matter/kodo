import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { Accounts } from "./Accounts";

vi.mock("../api/client", () => ({
  api: {
    accounts: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
    netWorth: { addBalanceSnapshot: vi.fn() },
  },
}));

const GTBANK = {
  id: 1,
  name: "GTBank",
  institution: "Guaranty Trust Bank",
  type: "checking" as const,
  parser_type: null,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.mocked(api.accounts.list).mockResolvedValue([GTBANK]);
});

describe("Accounts page - manage panel", () => {
  it("opens edit and balance forms for an account", async () => {
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("GTBank");
    await user.click(screen.getByText("manage"));

    expect(screen.getByText("Edit account")).toBeInTheDocument();
    expect(screen.getByText(/Log a balance/)).toBeInTheDocument();
  });

  it("editing an account calls the API and reflects the update", async () => {
    vi.mocked(api.accounts.update).mockResolvedValue({ ...GTBANK, name: "GTBank Savings" });
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("GTBank");
    await user.click(screen.getByText("manage"));

    const nameInput = screen.getByDisplayValue("GTBank");
    await user.clear(nameInput);
    await user.type(nameInput, "GTBank Savings");
    await user.click(screen.getByText("Save"));

    expect(api.accounts.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ name: "GTBank Savings", institution: "Guaranty Trust Bank" }),
    );
    expect(await screen.findByText("GTBank Savings")).toBeInTheDocument();
  });

  it("submitting a balance snapshot calls the API for the right account", async () => {
    vi.mocked(api.netWorth.addBalanceSnapshot).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<Accounts />);

    await screen.findByText("GTBank");
    await user.click(screen.getByText("manage"));

    await user.type(screen.getByPlaceholderText("Balance"), "300");
    await user.click(screen.getByText("Log balance"));

    expect(api.netWorth.addBalanceSnapshot).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ balance: "300" }),
    );
  });
});
