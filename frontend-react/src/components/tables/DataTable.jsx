export default function DataTable({ columns, rows, emptyMessage = "No records available.", maxHeight }) {
  if (!rows?.length) {
    return (
      <div className="rounded-lg border border-line bg-panel p-6 text-center text-sm text-muted">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-panel">
      <div className="overflow-auto" style={maxHeight ? { maxHeight } : undefined}>
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 bg-[#08182a] text-[11px] uppercase tracking-wide text-sky-300">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={`px-4 py-3 font-semibold ${column.align === "right" ? "text-right" : ""}`}>
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((row, index) => (
              <tr key={row.id || index} className="text-slate-200 transition hover:bg-cyan-400/5">
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-3 ${column.align === "right" ? "text-right" : ""}`}>
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
