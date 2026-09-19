import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Category, Transaction } from "../api/types";
import { Card } from "../components/Card";
import "./Transactions.css";

const currency = (value: string) =>
  Number(value).toLocaleString("en-US", { style: "currency", currency: "USD" });

function TransactionRow({
  transaction,
  categories,
  onChange,
}: {
  transaction: Transaction;
  categories: Category[];
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

  return (
    <>
      <tr>
        <td>{transaction.date}</td>
        <td className="description-cell">{transaction.description}</td>
        <td className="amount-cell">{currency(transaction.amount)}</td>
        <td>
          <select
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
          <button className="link-button" onClick={() => setShowRuleInput((v) => !v)}>
            always categorize like this?
          </button>
        </td>
      </tr>
      {showRuleInput && (
        <tr>
          <td colSpan={5} className="rule-row">
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
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.categories.list().then(setCategories).catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    api.transactions
      .list({ uncategorized_only: uncategorizedOnly })
      .then(setTransactions)
      .catch((err) => setError(String(err)));
  }, [uncategorizedOnly]);

  if (error) return <Card>Couldn't load transactions: {error}</Card>;
  if (!transactions || !categories) return <Card>Loading…</Card>;

  return (
    <Card title="Transactions">
      <label className="filter-toggle">
        <input
          type="checkbox"
          checked={uncategorizedOnly}
          onChange={(e) => setUncategorizedOnly(e.target.checked)}
        />
        Uncategorized only
      </label>
      <table className="transactions-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Amount</th>
            <th>Category</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <TransactionRow
              key={t.id}
              transaction={t}
              categories={categories}
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
