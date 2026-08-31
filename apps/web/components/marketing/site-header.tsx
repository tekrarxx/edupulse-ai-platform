import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          EduPulse <span className="text-primary">AI</span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-muted md:flex">
          <Link href="/#nasil-calisir" className="hover:text-foreground">
            Nasıl çalışır
          </Link>
          <Link href="/#kimler-icin" className="hover:text-foreground">
            Kimler için
          </Link>
          <Link href="/#fiyatlandirma" className="hover:text-foreground">
            Fiyatlandırma
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm font-medium text-muted hover:text-foreground">
            Giriş yap
          </Link>
          <Link
            href="/register"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            Ücretsiz başla
          </Link>
        </div>
      </div>
    </header>
  );
}
