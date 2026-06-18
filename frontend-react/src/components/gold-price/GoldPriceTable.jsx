import DataTable from "../tables/DataTable";
import { formatDateTime, formatVND } from "../../utils/format";

function companyBadge(company) {
  const key = String(company || "Other").toUpperCase();
  const classes = {
    SJC: "bg-red-500/20 text-red-200 border-red-400/30",
    DOJI: "bg-sky-500/20 text-sky-200 border-sky-400/30",
    PNJ: "bg-emerald-500/20 text-emerald-200 border-emerald-400/30",
  };
  return (
    <span className={`rounded border px-2 py-1 text-[11px] font-bold ${classes[key] || "border-slate-400/30 bg-slate-500/20 text-slate-200"}`}>
      {key}
    </span>
  );
}

export default function GoldPriceTable({ records }) {
  const columns = [
    { key: "company", header: "Company", render: (row) => companyBadge(row.company) },
    { key: "region", header: "Region" },
    { key: "goldType", header: "Gold Type" },
    { key: "buy", header: "Buy", align: "right", render: (row) => formatVND(row.buy) },
    { key: "sell", header: "Sell", align: "right", render: (row) => formatVND(row.sell) },
    { key: "spread", header: "Spread", align: "right", render: (row) => formatVND(row.spread) },
    { key: "timestamp", header: "Date / Timestamp", render: (row) => formatDateTime(row.timestamp) },
    { key: "source", header: "Source", render: (row) => row.source || "N/A" },
  ];

  const rows = records.map((record, index) => ({
    id: `${record.company}-${record.region}-${record.goldType}-${index}`,
    ...record,
  }));

  return (
    <DataTable
      columns={columns}
      rows={rows}
      maxHeight="320px"
      emptyMessage="No gold price data available. Run crawler first."
    />
  );
}
