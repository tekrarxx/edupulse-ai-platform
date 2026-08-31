import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-8 text-sm text-muted md:flex-row md:items-center md:justify-between">
        <p>© {new Date().getFullYear()} EduPulse AI. Pilot aşamasında bir üründür.</p>
        <div className="flex gap-5">
          <Link href="/login" className="hover:text-foreground">
            Giriş yap
          </Link>
          <Link href="/register" className="hover:text-foreground">
            Kayıt ol
          </Link>
          <Link href="/status" className="hover:text-foreground">
            Sistem durumu
          </Link>
        </div>
      </div>
    </footer>
  );
}
