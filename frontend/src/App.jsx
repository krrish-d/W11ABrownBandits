import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import CreateInvoice from "./pages/CreateInvoice";
import InvoiceLibrary from "./pages/InvoiceLibrary";
import InvoiceDetail from "./pages/InvoiceDetail";
import Transform from "./pages/Transform";
import Validate from "./pages/Validate";
import SendInvoice from "./pages/SendInvoice";

function AppLayout() {
  const location = useLocation();

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-content">
        <Header pathname={location.pathname} />
        <div className="page-wrap">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/create" element={<CreateInvoice />} />
        <Route path="/invoices" element={<InvoiceLibrary />} />
        <Route path="/invoices/:id" element={<InvoiceDetail />} />
        <Route path="/transform" element={<Transform />} />
        <Route path="/validate" element={<Validate />} />
        <Route path="/send" element={<SendInvoice />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
