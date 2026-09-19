import { Fragment, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Account, AccountType, Category } from "../api/types";
import { Card } from "../components/Card";
import "./Accounts.css";

const PARSER_OPTIONS = [
  { value: "", label: "None (manual entry)" },
  { value: "boa_checking", label: "BoA checking/savings CSV" },
  { value: "boa_credit_card", label: "BoA credit card CSV" },
  { value: "amex", label: "Amex XLSX" },
];

const ACCOUNT_TYPES: AccountType[] = ["checking", "savings", "credit", "loan", "investment"];

const today = () => new Date().toISOString().slice(0, 10);

function ImportButton({ account, onImported }: { account: Account; onImported: () => void }) {
  const [status, setStatus] = useState<string | null>(null);

  async function handleFile(file: File) {
    setStatus("Importing…");
    try {
      const summary = await api.imports.upload(account.id, file);
      setStatus(
        `Imported ${summary.imported}, skipped ${summary.skipped_duplicates} duplicate(s) of ${summary.total_in_file} in file`,
      );
      onImported();
    } catch (err) {
      setStatus(`Import failed: ${err}`);
    }
  }

  if (!account.parser_type) return <span className="muted">manual entry only</span>;

  return (
    <div className="import-cell">
      <input
        type="file"
        accept=".csv,.xlsx"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      {status && <span className="import-status">{status}</span>}
    </div>
  );
}

function ManualTransactionForm({ account, categories }: { account: Account; categories: Category[] }) {
  const [date, setDate] = useState(today());
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await api.transactions.create({
      account_id: account.id,
      date,
      description,
      amount,
      category_id: categoryId ? Number(categoryId) : null,
    });
    setDescription("");
    setAmount("");
    setCategoryId("");
    setStatus("Added.");
  }

  return (
    <form className="manage-form" onSubmit={handleSubmit}>
      <span className="manage-form-title">Add a transaction</span>
      <div className="manage-form-row">
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
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Uncategorized</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button type="submit">Add</button>
      </div>
      {status && <span className="manage-form-status">{status}</span>}
    </form>
  );
}

function BalanceSnapshotForm({ account }: { account: Account }) {
  const [date, setDate] = useState(today());
  const [balance, setBalance] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await api.netWorth.addBalanceSnapshot(account.id, { date, balance });
    setStatus(`Logged $${balance} as of ${date}.`);
    setBalance("");
  }

  const hint =
    account.type === "credit" || account.type === "loan"
      ? "amount owed, as a positive number"
      : "current balance";

  return (
    <form className="manage-form" onSubmit={handleSubmit}>
      <span className="manage-form-title">Log a balance ({hint}) - feeds Net Worth on the dashboard</span>
      <div className="manage-form-row">
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        <input
          placeholder="Balance"
          type="number"
          step="0.01"
          min="0"
          value={balance}
          onChange={(e) => setBalance(e.target.value)}
          required
        />
        <button type="submit">Log balance</button>
      </div>
      {status && <span className="manage-form-status">{status}</span>}
    </form>
  );
}

export function Accounts() {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [institution, setInstitution] = useState("");
  const [type, setType] = useState<AccountType>("checking");
  const [parserType, setParserType] = useState("");
  const [managingId, setManagingId] = useState<number | null>(null);

  function refresh() {
    api.accounts.list().then(setAccounts).catch((err) => setError(String(err)));
  }

  useEffect(() => {
    refresh();
    api.categories.list().then(setCategories).catch((err) => setError(String(err)));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    await api.accounts.create({
      name,
      institution,
      type,
      parser_type: parserType || null,
    });
    setName("");
    setInstitution("");
    setParserType("");
    refresh();
  }

  if (error) return <Card>Couldn't load accounts: {error}</Card>;

  return (
    <>
      <Card title="Add an account">
        <form className="account-form" onSubmit={handleCreate}>
          <input placeholder="Name (e.g. Checking)" value={name} onChange={(e) => setName(e.target.value)} required />
          <input
            placeholder="Institution (e.g. Bank of America)"
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
            required
          />
          <select value={type} onChange={(e) => setType(e.target.value as AccountType)}>
            {ACCOUNT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select value={parserType} onChange={(e) => setParserType(e.target.value)}>
            {PARSER_OPTIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <button type="submit">Add account</button>
        </form>
      </Card>

      <Card title="Accounts">
        {!accounts ? (
          "Loading…"
        ) : (
          <table className="accounts-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Institution</th>
                <th>Type</th>
                <th>Import statement</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <Fragment key={a.id}>
                  <tr>
                    <td>{a.name}</td>
                    <td>{a.institution}</td>
                    <td>{a.type}</td>
                    <td>
                      <ImportButton account={a} onImported={refresh} />
                    </td>
                    <td>
                      <button
                        className="link-button"
                        onClick={() => setManagingId(managingId === a.id ? null : a.id)}
                      >
                        {managingId === a.id ? "close" : "manage"}
                      </button>
                    </td>
                  </tr>
                  {managingId === a.id && (
                    <tr>
                      <td colSpan={5} className="manage-row">
                        {!a.parser_type && <ManualTransactionForm account={a} categories={categories} />}
                        <BalanceSnapshotForm account={a} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
