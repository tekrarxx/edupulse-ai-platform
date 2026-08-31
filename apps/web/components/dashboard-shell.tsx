import Link from "next/link";

export function DashboardShell({
  title,
  onLogout,
  children,
}: {
  title: string;
  onLogout: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface">
      <header className="border-b border-border bg-background">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <Link href="/dashboard" className="text-lg font-semibold">
            EduPulse <span className="text-primary">AI</span>
          </Link>
          <button
            onClick={onLogout}
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-surface"
          >
            Çıkış yap
          </button>
        </div>
      </header>

      <main className="mx-auto flex max-w-4xl flex-col gap-6 p-8">
        <h1 className="text-2xl font-semibold">{title}</h1>
        {children}
      </main>
    </div>
  );
}
