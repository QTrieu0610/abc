export default function LoadingState({ title = "Loading data..." }) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-line bg-panel/70 p-8 text-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
      <p className="mt-3 text-sm font-medium text-slate-300">{title}</p>
    </div>
  );
}
