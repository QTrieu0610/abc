import {
  Banknote,
  Bitcoin,
  ChartLine,
  CircleDollarSign,
  Coins,
  Home,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const topics = [
  { label: "Gold Price", to: "/extracted-data/gold-price", icon: Coins },
  { label: "House Price", to: "/extracted-data/house-price", icon: Home },
  { label: "Stock Price", to: "/extracted-data/stock-price", icon: ChartLine },
  { label: "Crypto Price", to: "/extracted-data/crypto-price", icon: Bitcoin },
  { label: "Forex Rate", to: "/extracted-data/forex-rate", icon: CircleDollarSign },
  { label: "Commodity Price", to: "/extracted-data/commodity-price", icon: Banknote },
];

export default function TopicList() {
  return (
    <aside className="w-full lg:w-[250px]">
      <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-sky-300">
        Topics
      </div>
      <div className="space-y-1">
        {topics.map((topic) => (
          <NavLink
            key={topic.to}
            to={topic.to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-3 text-sm font-semibold transition ${
                isActive
                  ? "bg-sky-500/20 text-cyan"
                  : "text-sky-100 hover:bg-sky-500/10 hover:text-white"
              }`
            }
          >
            <topic.icon className="h-4 w-4" aria-hidden="true" />
            {topic.label}
          </NavLink>
        ))}
      </div>
    </aside>
  );
}
