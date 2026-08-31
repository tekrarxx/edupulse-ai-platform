import Link from "next/link";

const PITCH_POINTS = [
  "Kanıta dayalı bilgi durumu tahmini",
  "Unutulan konular için otomatik hatırlatma",
  "Her önerinin izlenebilir bir açıklaması",
];

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="hidden flex-col justify-between bg-foreground p-10 text-background md:flex">
        <Link href="/" className="text-lg font-semibold">
          EduPulse <span className="text-primary">AI</span>
        </Link>
        <div>
          <p className="text-2xl font-semibold leading-snug">
            Öğrencinin gerçekte ne bildiğini anlayan öğrenme sistemi.
          </p>
          <ul className="mt-6 flex flex-col gap-2 text-sm opacity-80">
            {PITCH_POINTS.map((point) => (
              <li key={point} className="flex gap-2">
                <span className="text-primary">•</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs opacity-60">Fizik ile başlıyoruz · MEB müfredatı uyumlu</p>
      </div>

      <div className="flex flex-col justify-center p-8">
        <Link href="/" className="mb-8 text-lg font-semibold md:hidden">
          EduPulse <span className="text-primary">AI</span>
        </Link>
        <div className="mx-auto w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
