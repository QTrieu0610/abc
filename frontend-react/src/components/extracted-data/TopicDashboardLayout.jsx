import TopicList from "./TopicList";

export default function TopicDashboardLayout({ children }) {
  return (
    <div className="flex h-[calc(100vh-118px)] min-h-0 flex-col overflow-hidden">
      <div className="mb-5 shrink-0">
        <h1 className="text-2xl font-bold text-white">Extracted Data</h1>
        <p className="mt-1 text-sm text-sky-200">
          Browse and analyze extracted data from various sources and topics.
        </p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-5 lg:flex-row">
        <TopicList />
        <section className="min-h-0 min-w-0 flex-1 overflow-hidden rounded-lg border border-line bg-[#071322]/35">
          <div className="h-full overflow-y-auto p-4">
            {children}
          </div>
        </section>
      </div>
    </div>
  );
}
