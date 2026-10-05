import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { SettingsLayout } from "./components/SettingsLayout";
import { Accounts } from "./pages/Accounts";
import { Categories } from "./pages/Categories";
import { Dashboard } from "./pages/Dashboard";
import { LookingAhead } from "./pages/LookingAhead";
import { Transactions } from "./pages/Transactions";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="looking-ahead" element={<LookingAhead />} />
        <Route path="settings" element={<SettingsLayout />}>
          <Route index element={<Navigate to="accounts" replace />} />
          <Route path="accounts" element={<Accounts />} />
          <Route path="categories" element={<Categories />} />
        </Route>
      </Route>
    </Routes>
  );
}
