import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Accounts } from "./pages/Accounts";
import { Categories } from "./pages/Categories";
import { Dashboard } from "./pages/Dashboard";
import { Transactions } from "./pages/Transactions";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="categories" element={<Categories />} />
        <Route path="accounts" element={<Accounts />} />
      </Route>
    </Routes>
  );
}
