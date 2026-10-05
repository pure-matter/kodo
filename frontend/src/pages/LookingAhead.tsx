import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type {
  Account,
  GoalContribution,
  Holding,
  InvestmentType,
  LookingAheadSummary,
  NetWorth,
  PortfolioSlice,
  RecurringFrequency,
  RecurringInvestment,
  SavingsGoal,
} from "../api/types";
import { Card } from "../components/Card";
import { ProgressBar } from "../components/ProgressBar";
import { STATUS_COLORS, getSavingsStatus } from "../lib/budgetStatus";
import "./LookingAhead.css";

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

const monthDay = (iso: string) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

const today = () => new Date().toISOString().slice(0, 10);

const INVESTMENT_TYPES: InvestmentType[] = ["stock", "etf", "retirement_401k", "roth_ira", "real_estate", "other"];
const INVESTMENT_TYPE_LABELS: Record<InvestmentType, string> = {
  stock: "Stock",
  etf: "ETF",
  retirement_401k: "401(k)",
  roth_ira: "Roth IRA",
  real_estate: "Real Estate",
  other: "Other",
};

const FREQUENCIES: RecurringFrequency[] = ["weekly", "biweekly", "monthly"];

const SLICE_COLORS = [
  "var(--brand)",
  "var(--series-orange)",
  "var(--series-aqua)",
  "var(--series-yellow)",
  "var(--series-magenta)",
  "var(--series-violet)",
  "var(--series-green)",
  "var(--series-red)",
];

// --- Goals -----------------------------------------------------------------

function AddGoalForm({ accounts, onCreated }: { accounts: Account[]; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [linkedAccountId, setLinkedAccountId] = useState("");
  const [apy, setApy] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.savingsGoals.create({
        name,
        target_amount: targetAmount,
        target_date: targetDate || null,
        linked_account_id: linkedAccountId ? Number(linkedAccountId) : null,
        manual_apy: apy || null,
      });
      setName("");
      setTargetAmount("");
      setTargetDate("");
      setLinkedAccountId("");
      setApy("");
      onCreated();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <input placeholder="Goal name" value={name} onChange={(e) => setName(e.target.value)} required />
      <input
        placeholder="Target amount"
        type="number"
        step="0.01"
        value={targetAmount}
        onChange={(e) => setTargetAmount(e.target.value)}
        required
      />
      <input
        type="date"
        title="Target date (optional)"
        value={targetDate}
        onChange={(e) => setTargetDate(e.target.value)}
      />
      <select value={linkedAccountId} onChange={(e) => setLinkedAccountId(e.target.value)}>
        <option value="">No linked account</option>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <input
        placeholder="APY % (optional)"
        type="number"
        step="0.01"
        value={apy}
        onChange={(e) => setApy(e.target.value)}
      />
      <button type="submit">Add goal</button>
      {error && <div className="row-error">{error}</div>}
    </form>
  );
}

function ContributionForm({ goal, onLogged }: { goal: SavingsGoal; onLogged: () => void }) {
  const [date, setDate] = useState(today());
  const [amount, setAmount] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.savingsGoals.addContribution(goal.id, { date, amount });
      setStatus(`Logged ${currency(Number(amount))} on ${date}.`);
      setAmount("");
      onLogged();
    } catch (err) {
      setStatus(`Failed: ${err}`);
    }
  }

  return (
    <form className="manage-form-row" onSubmit={handleSubmit}>
      <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      <input
        placeholder="Amount"
        type="number"
        step="0.01"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
      />
      <button type="submit">Log contribution</button>
      {status && <span className="row-status">{status}</span>}
    </form>
  );
}

function ContributionHistory({ goalId }: { goalId: number }) {
  const [contributions, setContributions] = useState<GoalContribution[] | null>(null);

  useEffect(() => {
    api.savingsGoals.listContributions(goalId).then(setContributions);
  }, [goalId]);

  if (!contributions) return <span className="muted">Loading…</span>;
  if (contributions.length === 0) return <span className="muted">No contributions logged yet.</span>;

  let running = 0;
  const data = contributions.map((c) => {
    running += Number(c.amount);
    return { label: monthDay(c.date), cumulative: running };
  });

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data}>
        <CartesianGrid vertical={false} stroke="var(--border-hairline)" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => currency(v)} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value) => currency(Number(value))} />
        <Bar dataKey="cumulative" fill="var(--brand)" radius={4} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function GoalCard({ goal, onChanged }: { goal: SavingsGoal; onChanged: () => void }) {
  const [expanded, setExpanded] = useState<"contribute" | "history" | null>(null);
  const contributed = Number(goal.contributed);
  const target = Number(goal.target_amount);
  const status = getSavingsStatus(contributed, target);

  async function handleDelete() {
    if (!window.confirm(`Delete goal "${goal.name}"? This cannot be undone.`)) return;
    await api.savingsGoals.remove(goal.id);
    onChanged();
  }

  return (
    <div className={`goal-card${goal.achieved_at ? " goal-achieved" : ""}`}>
      <div className="goal-card-header">
        <span className="goal-card-name">
          {goal.name}
          {goal.achieved_at && <span className="goal-met-badge">✓ met</span>}
        </span>
        <button className="link-button link-button-danger" onClick={handleDelete}>
          delete
        </button>
      </div>
      <ProgressBar
        label=""
        value={contributed}
        target={target}
        fillColor={STATUS_COLORS[status]}
        valueLabel={`${currency(contributed)} / ${currency(target)}`}
      />
      {goal.target_date && (
        <div className="goal-meta">
          Target date: {monthDay(goal.target_date)}
          {goal.required_monthly_contribution !== null && !goal.achieved_at && (
            <> &middot; need {currency(Number(goal.required_monthly_contribution))}/month to get there</>
          )}
        </div>
      )}
      {!goal.achieved_at && (
        <div className="goal-actions">
          <button
            className="link-button"
            onClick={() => setExpanded(expanded === "contribute" ? null : "contribute")}
          >
            {expanded === "contribute" ? "close" : "log contribution"}
          </button>
          <button className="link-button" onClick={() => setExpanded(expanded === "history" ? null : "history")}>
            {expanded === "history" ? "close" : "view contributions"}
          </button>
        </div>
      )}
      {expanded === "contribute" && <ContributionForm goal={goal} onLogged={onChanged} />}
      {expanded === "history" && <ContributionHistory goalId={goal.id} />}
    </div>
  );
}

// --- Holdings ----------------------------------------------------------------

function AddHoldingForm({ accounts, onCreated }: { accounts: Account[]; onCreated: () => void }) {
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? 0);
  const [investmentType, setInvestmentType] = useState<InvestmentType>("stock");
  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [shares, setShares] = useState("");
  const [costBasis, setCostBasis] = useState("");
  const [purchaseDate, setPurchaseDate] = useState("");
  const [manualValue, setManualValue] = useState("");
  const [apy, setApy] = useState("");
  const [projectionYears, setProjectionYears] = useState("");
  const [targetProjectedValue, setTargetProjectedValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.holdings.create({
        account_id: accountId,
        investment_type: investmentType,
        name,
        symbol: symbol || null,
        shares: shares || null,
        cost_basis: costBasis,
        purchase_date: purchaseDate || null,
        manual_value: manualValue || null,
        manual_apy: apy || null,
        projection_years: projectionYears ? Number(projectionYears) : null,
        target_projected_value: targetProjectedValue || null,
      });
      setName("");
      setSymbol("");
      setShares("");
      setCostBasis("");
      setPurchaseDate("");
      setManualValue("");
      setApy("");
      setProjectionYears("");
      setTargetProjectedValue("");
      onCreated();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <select value={accountId} onChange={(e) => setAccountId(Number(e.target.value))}>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <select value={investmentType} onChange={(e) => setInvestmentType(e.target.value as InvestmentType)}>
        {INVESTMENT_TYPES.map((t) => (
          <option key={t} value={t}>
            {INVESTMENT_TYPE_LABELS[t]}
          </option>
        ))}
      </select>
      <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
      <input placeholder="Ticker (optional)" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
      <input
        placeholder="Shares (optional)"
        type="number"
        step="0.0001"
        value={shares}
        onChange={(e) => setShares(e.target.value)}
      />
      <input
        placeholder="Cost basis"
        type="number"
        step="0.01"
        value={costBasis}
        onChange={(e) => setCostBasis(e.target.value)}
        required
      />
      <input type="date" title="Purchase date (optional)" value={purchaseDate} onChange={(e) => setPurchaseDate(e.target.value)} />
      <input
        placeholder="Current value (if no ticker)"
        type="number"
        step="0.01"
        value={manualValue}
        onChange={(e) => setManualValue(e.target.value)}
      />
      <input placeholder="APY % (optional)" type="number" step="0.01" value={apy} onChange={(e) => setApy(e.target.value)} />
      <input
        placeholder="Projection years"
        type="number"
        value={projectionYears}
        onChange={(e) => setProjectionYears(e.target.value)}
      />
      <input
        placeholder="Projected value (optional)"
        type="number"
        step="0.01"
        value={targetProjectedValue}
        onChange={(e) => setTargetProjectedValue(e.target.value)}
      />
      <button type="submit">Add holding</button>
      {error && <div className="row-error">{error}</div>}
    </form>
  );
}

function HoldingRow({
  holding,
  accountName,
  onChanged,
}: {
  holding: Holding;
  accountName: string;
  onChanged: () => void;
}) {
  const [status, setStatus] = useState<string | null>(null);

  async function handleRefresh() {
    setStatus("Checking price…");
    try {
      await api.holdings.refreshPrice(holding.id);
      setStatus(null);
      onChanged();
    } catch (err) {
      setStatus(String(err));
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${holding.name}"?`)) return;
    await api.holdings.remove(holding.id);
    onChanged();
  }

  return (
    <tr>
      <td>{holding.name}</td>
      <td>{INVESTMENT_TYPE_LABELS[holding.investment_type]}</td>
      <td>{accountName}</td>
      <td>{currency(Number(holding.current_value))}</td>
      <td>
        {holding.symbol ? (
          <>
            {holding.current_price ? currency(Number(holding.current_price)) : "—"}{" "}
            <button className="link-button" onClick={handleRefresh}>
              check price
            </button>
            {status && <div className="row-error">{status}</div>}
          </>
        ) : (
          <span className="muted">no ticker</span>
        )}
      </td>
      <td>
        {holding.computed_projected_value
          ? `${currency(Number(holding.computed_projected_value))}${
              holding.projection_years ? ` (${holding.projection_years}y)` : ""
            }`
          : "—"}
      </td>
      <td>
        <button className="link-button link-button-danger" onClick={handleDelete}>
          delete
        </button>
      </td>
    </tr>
  );
}

type GroupBy = "type" | "account";

function HoldingsSection({
  holdings,
  accounts,
  onChanged,
}: {
  holdings: Holding[];
  accounts: Account[];
  onChanged: () => void;
}) {
  const [groupBy, setGroupBy] = useState<GroupBy>("type");
  const accountName = (id: number) => accounts.find((a) => a.id === id)?.name ?? "Unknown";

  const groups =
    groupBy === "type"
      ? INVESTMENT_TYPES.map((t) => ({
          label: INVESTMENT_TYPE_LABELS[t],
          rows: holdings.filter((h) => h.investment_type === t),
        })).filter((g) => g.rows.length > 0)
      : accounts
          .map((a) => ({ label: a.name, rows: holdings.filter((h) => h.account_id === a.id) }))
          .filter((g) => g.rows.length > 0);

  return (
    <>
      <div className="segmented-control">
        <button className={groupBy === "type" ? "segmented-active" : ""} onClick={() => setGroupBy("type")}>
          By type
        </button>
        <button className={groupBy === "account" ? "segmented-active" : ""} onClick={() => setGroupBy("account")}>
          By account
        </button>
      </div>
      {holdings.length === 0 ? (
        <span className="muted">No investments added yet.</span>
      ) : (
        groups.map((group) => (
          <div key={group.label} className="category-group">
            <h3 className="category-group-title">{group.label}</h3>
            <table className="categories-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Account</th>
                  <th>Value</th>
                  <th>Price</th>
                  <th>Projected</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {group.rows.map((h) => (
                  <HoldingRow key={h.id} holding={h} accountName={accountName(h.account_id)} onChanged={onChanged} />
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </>
  );
}

function PortfolioBreakdown({ byType, byAccount }: { byType: PortfolioSlice[]; byAccount: PortfolioSlice[] }) {
  const [view, setView] = useState<GroupBy>("type");
  const slices = (view === "type" ? byType : byAccount).map((s) => ({
    ...s,
    label: view === "type" ? INVESTMENT_TYPE_LABELS[s.label as InvestmentType] ?? s.label : s.label,
  }));

  if (byType.length === 0) return <span className="muted">Add investments to see a portfolio breakdown.</span>;

  return (
    <>
      <div className="segmented-control">
        <button className={view === "type" ? "segmented-active" : ""} onClick={() => setView("type")}>
          By type
        </button>
        <button className={view === "account" ? "segmented-active" : ""} onClick={() => setView("account")}>
          By account
        </button>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(slices.length * 36, 120)}>
        <BarChart data={slices} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid horizontal={false} stroke="var(--border-hairline)" />
          <XAxis type="number" tickFormatter={(v) => currency(v)} tick={{ fontSize: 12 }} />
          <YAxis type="category" dataKey="label" width={110} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value, _name, item) => [
              `${currency(Number(value))} (${item.payload.percent_of_total}%)`,
              "value",
            ]}
          />
          <Bar dataKey="value" radius={4}>
            {slices.map((s, i) => (
              <Cell key={s.label} fill={SLICE_COLORS[i % SLICE_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

// --- Uninvested cash ---------------------------------------------------------

function AddUninvestedCashForm({ accounts, onLogged }: { accounts: Account[]; onLogged: () => void }) {
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? 0);
  const [date, setDate] = useState(today());
  const [amount, setAmount] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await api.uninvestedCash.log(accountId, { date, amount });
    setAmount("");
    onLogged();
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <select value={accountId} onChange={(e) => setAccountId(Number(e.target.value))}>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      <input
        placeholder="Uninvested cash"
        type="number"
        step="0.01"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
      />
      <button type="submit">Log</button>
    </form>
  );
}

// --- Recurring investments ----------------------------------------------------

function AddRecurringForm({
  goals,
  holdings,
  onCreated,
}: {
  goals: SavingsGoal[];
  holdings: Holding[];
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState<RecurringFrequency>("monthly");
  const [target, setTarget] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const [kind, id] = target.split(":");
    await api.recurringInvestments.create({
      name,
      amount,
      frequency,
      goal_id: kind === "goal" ? Number(id) : null,
      holding_id: kind === "holding" ? Number(id) : null,
    });
    setName("");
    setAmount("");
    setTarget("");
    onCreated();
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
      <input
        placeholder="Amount"
        type="number"
        step="0.01"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
      />
      <select value={frequency} onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}>
        {FREQUENCIES.map((f) => (
          <option key={f} value={f}>
            {f}
          </option>
        ))}
      </select>
      <select value={target} onChange={(e) => setTarget(e.target.value)}>
        <option value="">Not linked</option>
        <optgroup label="Goals">
          {goals.map((g) => (
            <option key={`goal:${g.id}`} value={`goal:${g.id}`}>
              {g.name}
            </option>
          ))}
        </optgroup>
        <optgroup label="Holdings">
          {holdings.map((h) => (
            <option key={`holding:${h.id}`} value={`holding:${h.id}`}>
              {h.name}
            </option>
          ))}
        </optgroup>
      </select>
      <button type="submit">Add recurring investment</button>
    </form>
  );
}

function RecurringTable({
  recurring,
  goals,
  holdings,
  onChanged,
}: {
  recurring: RecurringInvestment[];
  goals: SavingsGoal[];
  holdings: Holding[];
  onChanged: () => void;
}) {
  function targetLabel(r: RecurringInvestment) {
    if (r.goal_id) return goals.find((g) => g.id === r.goal_id)?.name ?? "—";
    if (r.holding_id) return holdings.find((h) => h.id === r.holding_id)?.name ?? "—";
    return "—";
  }

  async function handleDelete(id: number) {
    await api.recurringInvestments.remove(id);
    onChanged();
  }

  if (recurring.length === 0) return <span className="muted">No recurring investments set up yet.</span>;

  return (
    <table className="categories-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Amount</th>
          <th>Frequency</th>
          <th>Contributes to</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {recurring.map((r) => (
          <tr key={r.id}>
            <td>{r.name}</td>
            <td>{currency(Number(r.amount))}</td>
            <td>{r.frequency}</td>
            <td>{targetLabel(r)}</td>
            <td>
              <button className="link-button link-button-danger" onClick={() => handleDelete(r.id)}>
                delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// --- Page ---------------------------------------------------------------------

type LookingAheadTab = "overview" | "savings" | "investments";

export function LookingAhead() {
  const [summary, setSummary] = useState<LookingAheadSummary | null>(null);
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [netWorth, setNetWorth] = useState<NetWorth | null>(null);
  const [tab, setTab] = useState<LookingAheadTab>("overview");
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.lookingAhead.summary().then(setSummary).catch((err) => setError(String(err)));
  }

  useEffect(() => {
    refresh();
    api.accounts.list().then(setAccounts).catch((err) => setError(String(err)));
    api.netWorth.get().then(setNetWorth).catch((err) => setError(String(err)));
  }, []);

  if (error) return <Card>Couldn't load Looking Ahead: {error}</Card>;
  if (!summary || !accounts || !netWorth) return <Card>Loading…</Card>;

  const investmentAccounts = accounts.filter((a) => a.type === "investment");

  return (
    <>
      <div className="segmented-control">
        <button className={tab === "overview" ? "segmented-active" : ""} onClick={() => setTab("overview")}>
          Overview
        </button>
        <button className={tab === "savings" ? "segmented-active" : ""} onClick={() => setTab("savings")}>
          Savings
        </button>
        <button className={tab === "investments" ? "segmented-active" : ""} onClick={() => setTab("investments")}>
          Investments
        </button>
      </div>

      {tab === "overview" ? (
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

          <Card title="Portfolio breakdown">
            <PortfolioBreakdown byType={summary.by_type} byAccount={summary.by_account} />
            <div className="goal-meta">Total portfolio value: {currency(Number(summary.total_portfolio_value))}</div>
          </Card>
        </>
      ) : tab === "savings" ? (
        <Card title="Savings goals">
          <AddGoalForm accounts={accounts} onCreated={refresh} />
          {summary.goals.length === 0 ? (
            <span className="muted">No active goals yet.</span>
          ) : (
            <div className="goal-grid">
              {summary.goals.map((g) => (
                <GoalCard key={g.id} goal={g} onChanged={refresh} />
              ))}
            </div>
          )}
          {summary.achieved_goals.length > 0 && (
            <>
              <h3 className="category-group-title">Achieved</h3>
              <div className="goal-grid">
                {summary.achieved_goals.map((g) => (
                  <GoalCard key={g.id} goal={g} onChanged={refresh} />
                ))}
              </div>
            </>
          )}
        </Card>
      ) : (
        <>
          <Card title="Investments">
            <AddHoldingForm accounts={accounts} onCreated={refresh} />
            <HoldingsSection holdings={summary.holdings} accounts={accounts} onChanged={refresh} />
          </Card>

          <Card title="Uninvested cash">
            {investmentAccounts.length === 0 ? (
              <span className="muted">Add an investment account to track uninvested cash.</span>
            ) : (
              <>
                <AddUninvestedCashForm accounts={investmentAccounts} onLogged={refresh} />
                {summary.uninvested_cash.length === 0 ? (
                  <span className="muted">Nothing logged yet.</span>
                ) : (
                  <ul className="plain-list">
                    {summary.uninvested_cash.map((entry) => (
                      <li key={entry.id}>
                        {accounts.find((a) => a.id === entry.account_id)?.name ?? "Unknown"}:{" "}
                        {currency(Number(entry.amount))} as of {monthDay(entry.date)}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </Card>

          <Card title="Recurring investments">
            <AddRecurringForm goals={summary.goals} holdings={summary.holdings} onCreated={refresh} />
            <RecurringTable
              recurring={summary.recurring_investments}
              goals={summary.goals}
              holdings={summary.holdings}
              onChanged={refresh}
            />
          </Card>
        </>
      )}
    </>
  );
}
