import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Account, Category, Transaction } from "../api/types";
import { Card } from "../components/Card";
import "./Transactions.css";

const currency = (value: string) =>
  Number(value).toLocaleString("en-US", { style: "currency", currency: "USD" });

const today = () => new Date().toISOString().slice(0, 10);

function NewTransactionForm({
  accounts,
  categories,
  onCreated,
}: {
  accounts: Account[];
  categories: Category[];
  onCreated: (created: Transaction) => void;
}) {
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? 0);
  const [date, setDate] = useState(today());
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const created = await api.transactions.create({
      account_id: accountId,
      date,
      description,
      amount,
      category_id: categoryId ? Number(categoryId) : null,
    });
    onCreated(created);
    setDescription("");
    setAmount("");
    setCategoryId("");
  }

  return (
    <form className="new-transaction-form" onSubmit={handleSubmit}>
      <select
        aria-label="Account"
        value={accountId}
        onChange={(e) => setAccountId(Number(e.target.value))}
      >
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
      <input
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        required
      />
      <input
        placeholder="Amount (negative = spend)"
        type="number"
        step="0.01"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
      />
      <select
        aria-label="New transaction category"
        value={categoryId}
        onChange={(e) => setCategoryId(e.target.value)}
      >
        <option value="">Uncategorized</option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <button type="submit">Add transaction</button>
    </form>
  );
}

function TransactionRow({
  transaction,
  categories,
  selected,
  onToggleSelect,
  onChange,
}: {
  transaction: Transaction;
  categories: Category[];
  selected: boolean;
  onToggleSelect: () => void;
  onChange: (updated: Transaction) => void;
}) {
  const [showRuleInput, setShowRuleInput] = useState(false);
  const [pattern, setPattern] = useState(transaction.description);

  async function setCategory(categoryId: number, createRule: boolean) {
    const updated = await api.transactions.recategorize(transaction.id, {
      category_id: categoryId,
      create_rule: createRule,
      pattern: createRule ? pattern : undefined,
    });
    onChange(updated);
    setShowRuleInput(false);
  }

  async function toggleReviewed() {
    const [updated] = await api.transactions.bulkReview([transaction.id], !transaction.is_reviewed);
    onChange(updated);
  }

  return (
    <>
      <tr>
        <td>
          <input
            type="checkbox"
            aria-label={`Select ${transaction.description}`}
            checked={selected}
            onChange={onToggleSelect}
          />
        </td>
        <td>{transaction.date}</td>
        <td className="description-cell">{transaction.description}</td>
        <td className="amount-cell">{currency(transaction.amount)}</td>
        <td>
          <select
            aria-label="Category"
            value={transaction.category_id ?? ""}
            onChange={(e) => setCategory(Number(e.target.value), false)}
          >
            <option value="" disabled>
              Uncategorized
            </option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </td>
        <td>
          <button className="link-button" onClick={toggleReviewed}>
            {transaction.is_reviewed ? (
              <span className="reviewed-badge">✓ reviewed</span>
            ) : (
              "mark reviewed"
            )}
          </button>
        </td>
        <td>
          <button className="link-button" onClick={() => setShowRuleInput((v) => !v)}>
            always categorize like this?
          </button>
        </td>
      </tr>
      {showRuleInput && (
        <tr>
          <td colSpan={6} className="rule-row">
            <span>Match text (edit if needed - raw bank text can be truncated oddly):</span>
            <input value={pattern} onChange={(e) => setPattern(e.target.value)} />
            <select
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) setCategory(Number(e.target.value), true);
              }}
            >
              <option value="" disabled>
                Save rule as category…
              </option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </td>
        </tr>
      )}
    </>
  );
}

export function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [unreviewedOnly, setUnreviewedOnly] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.categories.list().then(setCategories).catch((err) => setError(String(err)));
    api.accounts.list().then(setAccounts).catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    api.transactions
      .list({ uncategorized_only: uncategorizedOnly, reviewed: unreviewedOnly ? false : undefined })
      .then((rows) => {
        setTransactions(rows);
        setSelectedIds(new Set());
      })
      .catch((err) => setError(String(err)));
  }, [uncategorizedOnly, unreviewedOnly]);

  if (error) return <Card>Couldn't load transactions: {error}</Card>;
  if (!transactions || !categories || !accounts) return <Card>Loading…</Card>;

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) =>
      prev.size === transactions!.length ? new Set() : new Set(transactions!.map((t) => t.id)),
    );
  }

  async function markSelectedReviewed() {
    const updated = await api.transactions.bulkReview(Array.from(selectedIds), true);
    const updatedById = new Map(updated.map((t) => [t.id, t]));
    setTransactions((prev) => prev!.map((row) => updatedById.get(row.id) ?? row));
    setSelectedIds(new Set());
  }

  return (
    <Card title="Transactions">
      {accounts.length > 0 && (
        <NewTransactionForm
          accounts={accounts}
          categories={categories}
          onCreated={(created) => setTransactions((prev) => [created, ...prev!])}
        />
      )}
      <div className="filters-row">
        <label className="filter-toggle">
          <input
            type="checkbox"
            checked={uncategorizedOnly}
            onChange={(e) => setUncategorizedOnly(e.target.checked)}
          />
          Uncategorized only
        </label>
        <label className="filter-toggle">
          <input
            type="checkbox"
            checked={unreviewedOnly}
            onChange={(e) => setUnreviewedOnly(e.target.checked)}
          />
          Unreviewed only
        </label>
        {selectedIds.size > 0 && (
          <button className="bulk-action-button" onClick={markSelectedReviewed}>
            Mark {selectedIds.size} as reviewed
          </button>
        )}
      </div>
      <table className="transactions-table">
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                aria-label="Select all"
                checked={transactions.length > 0 && selectedIds.size === transactions.length}
                onChange={toggleSelectAll}
              />
            </th>
            <th>Date</th>
            <th>Description</th>
            <th>Amount</th>
            <th>Category</th>
            <th>Reviewed</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <TransactionRow
              key={t.id}
              transaction={t}
              categories={categories}
              selected={selectedIds.has(t.id)}
              onToggleSelect={() => toggleSelect(t.id)}
              onChange={(updated) =>
                setTransactions((prev) => prev!.map((row) => (row.id === updated.id ? updated : row)))
              }
            />
          ))}
        </tbody>
      </table>
    </Card>
  );
}
