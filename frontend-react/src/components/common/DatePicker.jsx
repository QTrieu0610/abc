import { Calendar } from "lucide-react";

export default function DatePicker({ value, onChange, max, disabled }) {
  return (
    <label className="relative inline-flex items-center">
      <Calendar className="pointer-events-none absolute left-3 h-4 w-4 text-muted" aria-hidden="true" />
      <input
        type="date"
        value={value}
        max={max}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-md border border-line bg-panelSoft py-2 pl-10 pr-3 text-sm font-semibold text-sky-100 outline-none transition hover:border-cyan/40 focus:border-cyan disabled:opacity-60"
      />
    </label>
  );
}
