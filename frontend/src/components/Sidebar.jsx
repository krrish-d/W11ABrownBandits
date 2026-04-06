import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FilePlus,
  FileText,
  ArrowLeftRight,
  ShieldCheck,
  Send,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/create", label: "Create Invoice", icon: FilePlus },
  { to: "/invoices", label: "Invoice Library", icon: FileText },
  { to: "/transform", label: "Transform", icon: ArrowLeftRight },
  { to: "/validate", label: "Validate", icon: ShieldCheck },
  { to: "/send", label: "Send Invoice", icon: Send },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="logo">InvoiceFlow</div>
      <nav>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
