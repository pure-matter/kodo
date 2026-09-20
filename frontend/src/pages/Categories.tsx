import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { Category, CategoryGroup, CategoryRule, MonthlyHistoryItem } from "../api/types";
import { Card } from "../components/Card";
import { STATUS_COLORS, getBudgetStatus } from "../lib/budgetStatus";
import "./Categories.css";

const GROUPS: CategoryGroup[] = ["needs", "wants", "income", "transfer"];
const GROUP_LABELS: Record<CategoryGroup, string> = {
  needs: "Needs",
  wants: "Wants",
  income: "Income",
  transfer: "Transfer",
};

const currency = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

const monthName = (month: number) =>
  new Date(2000, month - 1, 1).toLocaleString("en-US", { month: "short" });

function CategoryRow({
  category,
  onSaved,
  onDeleted,
}: {
  category: Category;
  onSaved: (updated: Category) => void;
  onDeleted: (id: number) => void;
}) {
  const [name, setName] = useState(category.name);
  const [budget, setBudget] = useState(category.monthly_budget ?? "");
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setError(null);
    try {
      const updated = await api.categories.update(category.id, {
        name,
        monthly_budget: budget === "" ? null : budget,
      });
      onSaved(updated);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${category.name}"? This cannot be undone.`)) return;
    setError(null);
    try {
      await api.categories.remove(category.id);
      onDeleted(category.id);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <tr>
      <td>
        <input className="cell-input" value={name} onChange={(e) => setName(e.target.value)} />
      </td>
      <td>
        <input
          className="cell-input cell-input-narrow"
          type="number"
          step="0.01"
          placeholder="none"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
        />
      </td>
      <td>
        <button className="link-button" onClick={handleSave}>
          save
        </button>
        <button className="link-button link-button-danger" onClick={handleDelete}>
          delete
        </button>
        {error && <div className="row-error">{error}</div>}
      </td>
    </tr>
  );
}

function AddCategoryForm({ onCreated }: { onCreated: (created: Category) => void }) {
  const [name, setName] = useState("");
  const [group, setGroup] = useState<CategoryGroup>("wants");
  const [budget, setBudget] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await api.categories.create({
        name,
        group,
        monthly_budget: budget || null,
      });
      onCreated(created);
      setName("");
      setBudget("");
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <input placeholder="Category name" value={name} onChange={(e) => setName(e.target.value)} required />
      <select value={group} onChange={(e) => setGroup(e.target.value as CategoryGroup)}>
        {GROUPS.map((g) => (
          <option key={g} value={g}>
            {GROUP_LABELS[g]}
          </option>
        ))}
      </select>
      <input
        placeholder="Monthly budget (optional)"
        type="number"
        step="0.01"
        value={budget}
        onChange={(e) => setBudget(e.target.value)}
      />
      <button type="submit">Add category</button>
      {error && <div className="row-error">{error}</div>}
    </form>
  );
}

function RuleRow({
  rule,
  categories,
  onSaved,
  onDeleted,
}: {
  rule: CategoryRule;
  categories: Category[];
  onSaved: (updated: CategoryRule) => void;
  onDeleted: (id: number) => void;
}) {
  const [pattern, setPattern] = useState(rule.pattern);
  const [categoryId, setCategoryId] = useState(rule.category_id);
  const [priority, setPriority] = useState(rule.priority);

  async function handleSave() {
    const updated = await api.categoryRules.update(rule.id, {
      pattern,
      category_id: categoryId,
      priority,
    });
    onSaved(updated);
  }

  async function handleDelete() {
    if (!window.confirm(`Delete the rule for "${rule.pattern}"?`)) return;
    await api.categoryRules.remove(rule.id);
    onDeleted(rule.id);
  }

  return (
    <tr>
      <td>
        <input className="cell-input" value={pattern} onChange={(e) => setPattern(e.target.value)} />
      </td>
      <td>
        <select value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </td>
      <td>
        <input
          className="cell-input cell-input-narrow"
          type="number"
          value={priority}
          onChange={(e) => setPriority(Number(e.target.value))}
        />
      </td>
      <td>
        <button className="link-button" onClick={handleSave}>
          save
        </button>
        <button className="link-button link-button-danger" onClick={handleDelete}>
          delete
        </button>
      </td>
    </tr>
  );
}

function AddRuleForm({ categories, onCreated }: { categories: Category[]; onCreated: (created: CategoryRule) => void }) {
  const [pattern, setPattern] = useState("");
  const [categoryId, setCategoryId] = useState(categories[0]?.id ?? 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const created = await api.categoryRules.create({ pattern, category_id: categoryId });
    onCreated(created);
    setPattern("");
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <input placeholder="Match text" value={pattern} onChange={(e) => setPattern(e.target.value)} required />
      <select value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <button type="submit">Add rule</button>
    </form>
  );
}

function SpendChart({ categories }: { categories: Category[] }) {
  const [spend, setSpend] = useState<{ name: string; spent: number; budgeted: number | null }[] | null>(null);

  useEffect(() => {
    const now = new Date();
    api.reports.budgetSummary(now.getFullYear(), now.getMonth() + 1).then((rows) => {
      const data = rows
        .map((r) => ({
          name: r.category_name,
          spent: Number(r.spent),
          budgeted: r.budgeted !== null ? Number(r.budgeted) : null,
        }))
        .filter((r) => r.spent > 0)
        .sort((a, b) => b.spent - a.spent);
      setSpend(data);
    });
  }, [categories]);

  if (!spend) return <span>Loading…</span>;
  if (spend.length === 0) return <span className="muted">No spending recorded this month yet.</span>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(spend.length * 36, 120)}>
      <BarChart data={spend} layout="vertical" margin={{ left: 24, right: 24 }}>
        <CartesianGrid horizontal={false} stroke="var(--border-hairline)" />
        <XAxis type="number" tickFormatter={(v) => currency(v)} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value) => currency(Number(value))} />
        <Bar dataKey="spent" radius={4}>
          {spend.map((row) => (
            <Cell key={row.name} fill={STATUS_COLORS[getBudgetStatus(row.spent, row.budgeted)]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function HistoryChart() {
  const [history, setHistory] = useState<MonthlyHistoryItem[] | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);

  useEffect(() => {
    api.reports.monthlyHistory(6).then(setHistory);
  }, []);

  if (!history) return <span>Loading…</span>;

  const categoryOptions = Array.from(
    new Map(history.map((h) => [h.category_id, h.category_name])).entries(),
  );
  const selected = categoryId ?? categoryOptions[0]?.[0];
  const rows = history
    .filter((h) => h.category_id === selected)
    .sort((a, b) => (a.year === b.year ? a.month - b.month : a.year - b.year))
    .map((h) => ({ label: `${monthName(h.month)} ${h.year}`, spent: Number(h.spent) }));

  return (
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
        <BarChart data={rows}>
          <CartesianGrid vertical={false} stroke="var(--border-hairline)" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={(v) => currency(v)} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => currency(Number(value))} />
          <Bar dataKey="spent" fill="var(--brand)" radius={4} />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

function ArchiveMonth() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [status, setStatus] = useState<string | null>(null);

  async function handleArchive() {
    const confirmed = window.confirm(
      `Archive ${monthName(month)} ${year}? This saves each category's total for the month, then ` +
        "permanently deletes the underlying transactions for that month across all accounts. " +
        "Re-importing a statement for this month afterward may create duplicates, since the " +
        "records used to detect them will be gone. This cannot be undone.",
    );
    if (!confirmed) return;

    setStatus("Archiving…");
    try {
      await api.reports.archiveMonth(year, month);
      setStatus(`Archived ${monthName(month)} ${year}. Transactions for that month have been cleared.`);
    } catch (err) {
      setStatus(`Failed: ${err}`);
    }
  }

  return (
    <div className="inline-form">
      <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
          <option key={m} value={m}>
            {monthName(m)}
          </option>
        ))}
      </select>
      <input
        type="number"
        value={year}
        onChange={(e) => setYear(Number(e.target.value))}
        className="cell-input-narrow"
      />
      <button onClick={handleArchive}>Archive &amp; clear month</button>
      {status && <span className="row-status">{status}</span>}
    </div>
  );
}

export function Categories() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [rules, setRules] = useState<CategoryRule[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.categories.list().then(setCategories).catch((err) => setError(String(err)));
    api.categoryRules.list().then(setRules).catch((err) => setError(String(err)));
  }, []);

  if (error) return <Card>Couldn't load categories: {error}</Card>;
  if (!categories || !rules) return <Card>Loading…</Card>;

  return (
    <>
      <Card title="Spending by category (this month)">
        <SpendChart categories={categories} />
      </Card>

      <Card title="Categories">
        <AddCategoryForm onCreated={(c) => setCategories((prev) => [...prev!, c])} />
        {GROUPS.map((group) => {
          const inGroup = categories.filter((c) => c.group === group);
          if (inGroup.length === 0) return null;
          return (
            <div key={group} className="category-group">
              <h3 className="category-group-title">{GROUP_LABELS[group]}</h3>
              <table className="categories-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Monthly budget</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {inGroup.map((c) => (
                    <CategoryRow
                      key={c.id}
                      category={c}
                      onSaved={(updated) =>
                        setCategories((prev) => prev!.map((row) => (row.id === updated.id ? updated : row)))
                      }
                      onDeleted={(id) => setCategories((prev) => prev!.filter((row) => row.id !== id))}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </Card>

      <Card title="Rules">
        <AddRuleForm categories={categories} onCreated={(r) => setRules((prev) => [...prev!, r])} />
        <table className="categories-table">
          <thead>
            <tr>
              <th>Match text</th>
              <th>Category</th>
              <th>Priority</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rules
              .slice()
              .sort((a, b) => a.priority - b.priority)
              .map((r) => (
                <RuleRow
                  key={r.id}
                  rule={r}
                  categories={categories}
                  onSaved={(updated) =>
                    setRules((prev) => prev!.map((row) => (row.id === updated.id ? updated : row)))
                  }
                  onDeleted={(id) => setRules((prev) => prev!.filter((row) => row.id !== id))}
                />
              ))}
          </tbody>
        </table>
      </Card>

      <Card title="Spending history">
        <HistoryChart />
      </Card>

      <Card title="Archive a month">
        <p className="archive-hint">
          Saves each category's total for the month, then deletes that month's raw transactions so the
          database doesn't grow forever. You control when this happens - nothing is cleared automatically.
        </p>
        <ArchiveMonth />
      </Card>
    </>
  );
}
