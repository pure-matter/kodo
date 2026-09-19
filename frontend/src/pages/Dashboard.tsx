import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { BudgetSummaryItem, NetWorth, SavingsProgress } from "../api/types";
import { Card } from "../components/Card";
import { ProgressBar } from "../components/ProgressBar";
import { STATUS_COLORS, getBudgetStatus } from "../lib/budgetStatus";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

function BudgetGroup({ title, items }: { title: string; items: BudgetSummaryItem[] }) {
  return (
    <Card title={title}>
      {items.map((item) => {
        const spent = Number(item.spent);
        const budgeted = item.budgeted !== null ? Number(item.budgeted) : null;
        const status = getBudgetStatus(spent, budgeted);
        const valueLabel = budgeted !== null ? `${currency(spent)} / ${currency(budgeted)}` : currency(spent);
        return (
          <ProgressBar
            key={item.category_id}
            label={item.category_name}
            value={spent}
            target={budgeted}
            fillColor={STATUS_COLORS[status]}
            valueLabel={valueLabel}
          />
        );
      })}
    </Card>
  );
}

export function Dashboard() {
  const [budgetSummary, setBudgetSummary] = useState<BudgetSummaryItem[] | null>(null);
  const [savingsProgress, setSavingsProgress] = useState<SavingsProgress[] | null>(null);
  const [netWorth, setNetWorth] = useState<NetWorth | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;

    Promise.all([
      api.reports.budgetSummary(year, month),
      api.savings.progress(year, month),
      api.netWorth.get(),
    ])
      .then(([budget, savings, worth]) => {
        setBudgetSummary(budget);
        setSavingsProgress(savings);
        setNetWorth(worth);
      })
      .catch((err) => setError(String(err)));
  }, []);

  if (error) return <Card>Couldn't load the dashboard: {error}</Card>;
  if (!budgetSummary || !savingsProgress || !netWorth) return <Card>Loading…</Card>;

  const needs = budgetSummary.filter((item) => item.group === "needs");
  const wants = budgetSummary.filter((item) => item.group === "wants");

  return (
    <>
      <Card>
        <div className="stat-tile">
          <span className="stat-label">Net worth</span>
          <span className="stat-value">{currency(Number(netWorth.net_worth))}</span>
          <span className="stat-sub">
            {currency(Number(netWorth.assets))} assets &minus; {currency(Number(netWorth.liabilities))} liabilities
          </span>
        </div>
      </Card>

      <BudgetGroup title="Needs" items={needs} />
      <BudgetGroup title="Wants" items={wants} />

      <Card title="Savings">
        {savingsProgress.map((item) => (
          <ProgressBar
            key={item.allocation_id}
            label={item.name}
            value={Number(item.contributed)}
            target={Number(item.monthly_target)}
            fillColor="var(--brand)"
            valueLabel={`${currency(Number(item.contributed))} / ${currency(Number(item.monthly_target))}`}
          />
        ))}
      </Card>
    </>
  );
}
