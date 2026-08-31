import Link from "next/link";
import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";

const LOOP_STEPS = [
  { title: "Öğrenme etkinliği", desc: "Öğrenci bir soruyu çözer veya bir konuyu çalışır." },
  { title: "Gözlem", desc: "Ne olduğu ham haliyle kaydedilir: doğru, yanlış, ipucu istendi, süre." },
  { title: "Kanıt", desc: "Gözlemler, ilgili beceri için anlamlı sinyallere dönüştürülür." },
  { title: "Bilgi durumu tahmini", desc: "Sistem, öğrencinin o beceriyi ne kadar bildiğini güncel kanıtlarla tahmin eder." },
  { title: "Sıradaki adım", desc: "Tekrar mı, daha zor bir soru mu, transfer görevi mi gerektiğine karar verilir." },
];

const AUDIENCES = [
  {
    title: "Öğrenciler",
    points: [
      "Şu an nerede olduğunu ve sırada ne olduğunu net görür",
      "Unuttuğu konular 14 ve 28 gün sonra otomatik hatırlatılır",
      "Ezberlemek yerine kavramı farklı bağlamlarda uygulamayı öğrenir",
    ],
  },
  {
    title: "Öğretmenler",
    points: [
      "Hangi öğrencinin ilgiye ihtiyacı olduğunu görür, 30 farklı grafiğe bakmaz",
      "Zayıf beceriler ve olası kavram yanılgıları öne çıkar",
      "Her öneri, hangi kanıta dayandığı görülebilecek şekilde açıklanabilir",
    ],
  },
  {
    title: "Okullar ve kurumlar",
    points: [
      "MEB müfredatı ve Türkiye Yüzyılı Maarif Modeli ile uyumlu yapı",
      "Kurum verisi ve öğrenci verisi tamamen izole tutulur",
      "Küçük bir pilotla başlayıp ölçülen sonuçla genişleme",
    ],
  },
];

export default function HomePage() {
  return (
    <>
      <SiteHeader />

      <main>
        <section className="mx-auto max-w-4xl px-6 pb-20 pt-20 text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-primary">
            İlk alan: Fizik · MEB müfredatı
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
            Öğrencinin gerçekte ne bildiğini anlayan,
            <br className="hidden md:block" /> sıradaki adımı söyleyen öğrenme sistemi
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted">
            EduPulse sınırsız soru üreten bir sohbet botu değildir. Kanıta dayalı olarak
            bilgi durumunu tahmin eder, unutulan konuları tespit eder ve her öğrenci için
            en faydalı sıradaki öğrenme eylemini belirler.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              href="/register"
              className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              Ücretsiz başla
            </Link>
            <Link
              href="/login"
              className="rounded-md border border-border px-6 py-3 text-sm font-medium hover:bg-surface"
            >
              Giriş yap
            </Link>
          </div>
        </section>

        <section id="nasil-calisir" className="border-t border-border bg-surface">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <h2 className="text-2xl font-semibold">Nasıl çalışır</h2>
            <p className="mt-2 max-w-2xl text-muted">
              Her öneri, izlenebilir bir kanıt zincirine dayanır — kara kutu bir yapay
              zeka tahmini değil.
            </p>
            <div className="mt-10 grid gap-6 md:grid-cols-5">
              {LOOP_STEPS.map((step, i) => (
                <div key={step.title} className="rounded-lg border border-border bg-background p-4">
                  <span className="text-xs font-medium text-primary">{String(i + 1).padStart(2, "0")}</span>
                  <h3 className="mt-2 text-sm font-semibold">{step.title}</h3>
                  <p className="mt-1 text-xs text-muted">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="kimler-icin" className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-2xl font-semibold">Kimler için</h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {AUDIENCES.map((audience) => (
              <div key={audience.title} className="rounded-lg border border-border p-6">
                <h3 className="text-lg font-semibold">{audience.title}</h3>
                <ul className="mt-4 flex flex-col gap-2 text-sm text-muted">
                  {audience.points.map((point) => (
                    <li key={point} className="flex gap-2">
                      <span className="text-primary">•</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section id="fiyatlandirma" className="border-t border-border bg-surface">
          <div className="mx-auto max-w-3xl px-6 py-16 text-center">
            <h2 className="text-2xl font-semibold">Fiyatlandırma</h2>
            <p className="mt-4 text-muted">
              EduPulse şu anda pilot okul ve öğretmenlerle birlikte geliştiriliyor.
              Fiyatlandırma planları bu pilot sürecin sonunda netleşecek. Bireysel
              öğrenciler için ücretsiz kayıt her zaman açık.
            </p>
            <div className="mt-8 flex items-center justify-center gap-4">
              <Link
                href="/register"
                className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
              >
                Ücretsiz kayıt ol
              </Link>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </>
  );
}
