import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type {
  AvailableMonth,
  BudgetSummaryItem,
  MonthlyHistoryItem,
  SavingsProgress,
} from "../api/types";
import { Card } from "../components/Card";
import { ProgressBar } from "../components/ProgressBar";
import { STATUS_COLORS, getBudgetStatus, getSavingsStatus } from "../lib/budgetStatus";
import { aggregateByBucket, toCategoryRows, type SpendRow } from "../lib/spendAggregation";
import "./Dashboard.css";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

const monthName = (month: number) =>
  new Date(2000, month - 1, 1).toLocaleString("en-US", { month: "short" });

const monthOptionLabel = (year: number, month: number) =>
  new Date(year, month - 1, 1).toLocaleString("en-US", { month: "long", year: "numeric" });

function bucketTotalLabel(row: SpendRow | undefined) {
  if (!row) return null;
  return (
    <>
      {currency(row.spent)} spent
      {row.budgeted !== null && <> / {currency(row.budgeted)} planned</>}
    </>
  );
}

function BudgetGroup({
  title,
  items,
  bucketTotal,
}: {
  title: string;
  items: BudgetSummaryItem[];
  bucketTotal: SpendRow | undefined;
}) {
  return (
    <Card title={title} headerExtra={bucketTotalLabel(bucketTotal)}>
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

function MonthPicker({
  months,
  year,
  month,
  onChange,
}: {
  months: AvailableMonth[];
  year: number;
  month: number;
  onChange: (year: number, month: number) => void;
}) {
  return (
    <select
      className="month-picker"
      value={`${year}-${month}`}
      onChange={(e) => {
        const [y, m] = e.target.value.split("-").map(Number);
        onChange(y, m);
      }}
    >
      {months.map((m) => (
        <option key={`${m.year}-${m.month}`} value={`${m.year}-${m.month}`}>
          {monthOptionLabel(m.year, m.month)}
        </option>
      ))}
    </select>
  );
}

type ChartView = "category" | "bucket";

function SpendChart({ year, month }: { year: number; month: number }) {
  const navigate = useNavigate();
  const [budget, setBudget] = useState<BudgetSummaryItem[] | null>(null);
  const [savings, setSavings] = useState<SavingsProgress[] | null>(null);
  const [view, setView] = useState<ChartView>("category");

  useEffect(() => {
    Promise.all([api.reports.budgetSummary(year, month), api.savings.progress(year, month)]).then(
      ([b, s]) => {
        setBudget(b);
        setSavings(s);
      },
    );
  }, [year, month]);

  if (!budget || !savings) return <span>Loading…</span>;

  const data = view === "category" ? toCategoryRows(budget) : aggregateByBucket(budget, savings);

  return (
    <>
      <div className="segmented-control">
        <button
          className={view === "category" ? "segmented-active" : ""}
          onClick={() => setView("category")}
        >
          By category
        </button>
        <button className={view === "bucket" ? "segmented-active" : ""} onClick={() => setView("bucket")}>
          By bucket
        </button>
      </div>
      {data.length === 0 ? (
        <span className="muted">No spending recorded this month yet.</span>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(data.length * 36, 120)}>
          <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
            <CartesianGrid horizontal={false} stroke="var(--border-hairline)" />
            <XAxis type="number" tickFormatter={(v) => currency(v)} tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value) => currency(Number(value))} />
            <Bar
              dataKey="spent"
              radius={4}
              style={{ cursor: "pointer" }}
              onClick={(bar) => {
                const row = bar.payload as SpendRow;
                if (row.category_id) navigate(`/transactions?category_id=${row.category_id}`);
              }}
            >
              {data.map((row) => {
                const status =
                  row.kind === "savings"
                    ? getSavingsStatus(row.spent, row.budgeted)
                    : getBudgetStatus(row.spent, row.budgeted);
                return <Cell key={row.name} fill={STATUS_COLORS[status]} />;
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </>
  );
}

type HistoryView = "category" | "bucket";

interface BucketHistoryRow {
  label: string;
  Needs: number;
  Wants: number;
  Savings: number;
}

function HistoryChart() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<MonthlyHistoryItem[] | null>(null);
  const [bucketHistory, setBucketHistory] = useState<BucketHistoryRow[] | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [view, setView] = useState<HistoryView>("category");

  useEffect(() => {
    api.reports.monthlyHistory(6).then(setHistory);
    api.reports.bucketHistory(6).then((rows) => {
      setBucketHistory(
        rows
          .slice()
          .sort((a, b) => (a.year === b.year ? a.month - b.month : a.year - b.year))
          .map((r) => ({
            label: `${monthName(r.month)} ${r.year}`,
            Needs: Number(r.needs),
            Wants: Number(r.wants),
            Savings: Number(r.savings),
          })),
      );
    });
  }, []);

  if (!history || !bucketHistory) return <span>Loading…</span>;

  const categoryOptions = Array.from(
    new Map(history.map((h) => [h.category_id, h.category_name])).entries(),
  );
  const selected = categoryId ?? categoryOptions[0]?.[0];
  const categoryRows = history
    .filter((h) => h.category_id === selected)
    .sort((a, b) => (a.year === b.year ? a.month - b.month : a.year - b.year))
    .map((h) => ({ label: `${monthName(h.month)} ${h.year}`, spent: Number(h.spent) }));

  return (
    <>
      <div className="segmented-control">
        <button
          className={view === "category" ? "segmented-active" : ""}
          onClick={() => setView("category")}
        >
          By category
        </button>
        <button className={view === "bucket" ? "segmented-active" : ""} onClick={() => setView("bucket")}>
          By bucket
        </button>
      </div>

      {view === "category" ? (
        <>
          <select
            className="history-picker"
            value={selected ?? ""}
            onChange={(e) => setCategoryId(Number(e.target.value))}
          >
            {categoryOptions.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={categoryRows}>
              <CartesianGrid vertical={false} stroke="var(--border-hairline)" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v) => currency(v)} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value) => currency(Number(value))} />
              <Bar
                dataKey="spent"
                fill="var(--brand)"
                radius={4}
                style={{ cursor: "pointer" }}
                onClick={() => selected && navigate(`/transactions?category_id=${selected}`)}
              />
            </BarChart>
          </ResponsiveContainer>
        </>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={bucketHistory}>
            <CartesianGrid vertical={false} stroke="var(--border-hairline)" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => currency(v)} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value) => currency(Number(value))} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="Needs" fill="var(--brand)" radius={4} />
            <Bar dataKey="Wants" fill="var(--series-orange)" radius={4} />
            <Bar dataKey="Savings" fill="var(--series-aqua)" radius={4} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </>
  );
}

type DashboardTab = "overview" | "spending";

export function Dashboard() {
  const today = new Date();
  const [months, setMonths] = useState<AvailableMonth[] | null>(null);
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [budgetSummary, setBudgetSummary] = useState<BudgetSummaryItem[] | null>(null);
  const [savingsProgress, setSavingsProgress] = useState<SavingsProgress[] | null>(null);
  const [income, setIncome] = useState<number | null>(null);
  const [tab, setTab] = useState<DashboardTab>("overview");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.reports
      .availableMonths()
      .then((rows) => {
        const current = { year: today.getFullYear(), month: today.getMonth() + 1 };
        const hasCurrent = rows.some((r) => r.year === current.year && r.month === current.month);
        setMonths(hasCurrent ? rows : [current, ...rows]);
      })
      .catch((err) => setError(String(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    Promise.all([
      api.reports.budgetSummary(year, month),
      api.savings.progress(year, month),
      api.reports.incomeSummary(year, month),
    ])
      .then(([budget, savings, incomeSummary]) => {
        setBudgetSummary(budget);
        setSavingsProgress(savings);
        setIncome(Number(incomeSummary.income));
      })
      .catch((err) => setError(String(err)));
  }, [year, month]);

  if (error) return <Card>Couldn't load the dashboard: {error}</Card>;
  if (!budgetSummary || !savingsProgress || income === null || !months) return <Card>Loading…</Card>;

  const needs = budgetSummary.filter((item) => item.group === "needs");
  const wants = budgetSummary.filter((item) => item.group === "wants");
  const bucketRows = aggregateByBucket(budgetSummary, savingsProgress);
  const bucketByName = (name: string) => bucketRows.find((r) => r.name === name);
  const totalSpent = (bucketByName("Needs")?.spent ?? 0) + (bucketByName("Wants")?.spent ?? 0);

  return (
    <>
      <div className="dashboard-toolbar">
        <div className="segmented-control">
          <button className={tab === "overview" ? "segmented-active" : ""} onClick={() => setTab("overview")}>
            Overview
          </button>
          <button className={tab === "spending" ? "segmented-active" : ""} onClick={() => setTab("spending")}>
            Spending
          </button>
        </div>
        <MonthPicker
          months={months}
          year={year}
          month={month}
          onChange={(y, m) => {
            setYear(y);
            setMonth(m);
          }}
        />
      </div>

      {tab === "overview" ? (
        <>
          <Card>
            <div className="stat-tile">
              <span className="stat-label">Spending vs. income</span>
              <span className="stat-value">{currency(income - totalSpent)}</span>
              <span className="stat-sub">
                {currency(totalSpent)} spent &middot; {currency(income)} income
              </span>
            </div>
          </Card>

          <BudgetGroup title="Needs" items={needs} bucketTotal={bucketByName("Needs")} />
          <BudgetGroup title="Wants" items={wants} bucketTotal={bucketByName("Wants")} />

          <Card title="Savings" headerExtra={bucketTotalLabel(bucketByName("Savings"))}>
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
      ) : (
        <>
          <Card title="Spending by category">
            <SpendChart year={year} month={month} />
          </Card>
          <Card title="Spending history">
            <HistoryChart />
          </Card>
        </>
      )}
    </>
  );
}
