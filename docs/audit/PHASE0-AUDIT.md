# EduPulse AI — Faz 0 Depo Denetim Raporu

Tarih: 2026-08-28
Kapsam: Salt okunur mimari denetim (PHASE0-AUDIT-PROMPT.md talimatına göre)
Kanıt komutları: `ls -la`, `find . -maxdepth 5`, `git status`, `git log --oneline -20`

## Terminoloji Uyarısı

Bu raporda **PDE** = Prometheus Decision Engine (CLAUDE.md §6, §32–39, §98–100,
ürünün kendisi) ve **Prometheus/Grafana** = gözlemlenebilirlik/metrik yığını
(CLAUDE.md §83) her zaman ayrı belirtilmiştir. Depoda ikisine ait hiçbir kod
bulunmadığından bu ayrım şu an sadece kavramsaldır.

---

## 1. CURRENT STATE

Depo kökü (`C:\Users\onuracar.OGM\Desktop\EduPulse_AI`) tamamen boş bir
proje iskeleti — sadece üç metin dosyası içeriyor:

```
.
├── Claude.md                        (= CLAUDE.md, Windows dosya sistemi büyük/küçük harf duyarsız)
├── EDUPULSE-CLAUDE-CODE-PHASES.md
└── PHASE0-AUDIT-PROMPT.md
```

Kanıt: `find . -maxdepth 5` çıktısı yalnızca bu üç dosyayı listeledi;
`ls -la` ile teyit edildi. `node_modules`, `.venv`, `.next`, `__pycache__`,
`.git` gibi hariç tutulması istenen dizinler zaten mevcut değil çünkü hiçbir
proje dizini yok.

Aşağıdaki 18 denetim maddesinin tamamı **NOT PRESENT**:

| # | Madde | Durum | Kanıt |
|---|---|---|---|
| 1 | Depo yapısı | NOT PRESENT | `find . -maxdepth 5` → 3 dosya, dizin yok |
| 2 | Uygulamalar (`apps/web`, `apps/api`, `apps/admin`) | NOT PRESENT | `find` çıktısında `apps/` yok |
| 3 | Backend mimarisi (katmanlama, ince route'lar, modüler monolit sınırı) | NOT PRESENT | Backend kodu yok |
| 4 | Frontend mimarisi (Next.js, routing, state, UI) | NOT PRESENT | Frontend kodu yok |
| 5 | Veritabanı modelleri (SQLAlchemy, tenant kolonu, FK, timestamp) | NOT PRESENT | `models/`, `*.py` yok |
| 6 | Migration'lar (Alembic zinciri) | NOT PRESENT | `alembic/`, `versions/` yok |
| 7 | Docker yapılandırması | NOT PRESENT | `docker-compose.yml` yok |
| 8 | API endpoint envanteri | NOT PRESENT | Route tanımı yok |
| 9 | PDE uygulama durumu (bilgi durumu, Bayesian, aday eylemler, politika, açıklanabilirlik, shadow mode, yanlışlanabilirlik) | NOT PRESENT | PDE'ye ait hiçbir dosya yok |
| 10 | Prometheus/Grafana gözlemlenebilirlik durumu | NOT PRESENT | Metrik/exporter/dashboard dosyası yok |
| 11 | Testler (unit/integration/api/e2e, property-based, cross-tenant) | NOT PRESENT | `tests/` dizini yok |
| 12 | Kimlik doğrulama / yetkilendirme | NOT PRESENT | Auth kodu yok |
| 13 | Kiracı (tenant) mimarisi | NOT PRESENT | Tenant modeli yok |
| 14 | AI/LLM entegrasyonu | NOT PRESENT | Gateway/provider kodu yok |
| 15 | n8n entegrasyonu | NOT PRESENT | n8n workflow dosyası yok |
| 16 | Event sourcing, provenance, immutable telemetry | NOT PRESENT | Event şeması yok |
| 17 | Dokümantasyon (`docs/`, ADR, README) | NOT PRESENT (bu rapor öncesi) | `docs/` bu denetimden önce yoktu; `README.md` yok |
| 18 | Git durumu | NOT PRESENT (git deposu yok) | `git status` → `fatal: not a git repository (or any of the parent directories): .git` |

**Kod kalitesi notu:** Değerlendirilecek kod yok — bu nedenle "korumaya değer
mi" (§124) sorusu şu an anlamsız; hiçbir şey silinme/üzerine yazılma riski
taşımıyor.

---

## 2. TARGET ARCHITECTURE

CLAUDE.md'nin öngördüğü hedef mimari (bölüm numaralarıyla):

**MVP-gerekli (§115):**
- §13 Modüler monolit: Next.js web → FastAPI api → Identity/Education/Assessment
  domain modülleri → Learning State → PDE → Decision Layer → Authorization.
- §15–16 API-first, ince route'lar; iş mantığı route handler'da değil.
- §19–20 Eğitim domain hiyerarşisi (Curriculum→Subject→Topic→Concept→Skill→
  Prerequisite→Assessment), müfredat versiyonlanmış.
- §21–23 Assessment/Observation/Evidence üçlüsü, Observation ve Evidence
  kesinlikle ayrı.
- §24–27 Bilgi durumu (Knowledge State) olasılıksal tahmin, Beta-Binomial
  Bayesian model (§25).
- §28–30 Recognition/Recall/Application/Transfer/Retention ayrımı,
  14/28 günlük gecikmeli hatırlama.
- §32–39 PDE: yapılandırılmış karar çıktısı, aday eylemler, politika/durum
  ayrımı, yetkilendirme katmanı, açıklanabilirlik, shadow mode, yanlışlanabilirlik.
- §50–53 Multi-tenant, sunucu taraflı tenant izolasyonu, RBAC (6 rol).
- §55–56 PostgreSQL + SQLAlchemy 2.x + Alembic, soft delete tercih edilir.
- §86–89 Test katmanları + property-based + cross-tenant testler.
- §91 Docker Compose (postgres, redis, api, web, opsiyonel n8n/ollama).
- §98–100 PDE bilimsel bütünlüğü: reproducibility, provenance, ADR zorunluluğu.

**Sonraki-faz (§114/§116, MVP'de gerekmez):**
- Kubernetes, karmaşık mikroservisler, tam kurumsal faturalama, enterprise SSO,
  gelişmiş öneri algoritmaları, onlarca ders, sosyal ağ/gamification, mobil
  native uygulama, gereksiz AI ajanları, büyük ölçekli vektör altyapısı,
  büyük ölçekli bulut altyapısı (§9–10 yerel-öncelik ilkesi gereği zaten
  bulut bu aşamada yok).
- P7–P10: AI Gateway (§45), Dashboard'lar (§74–77), SaaS/Entitlement/Billing
  (§59–66), Hardening/Observability/Performance/Deployment (§78–83, §109,
  §119–120, §137–139).

---

## 3. GAP ANALYSIS

Severity, §134 çakışma öncelik sırasına göre (Security > Privacy > Data
Integrity > Correctness > PDE Scientific Integrity > Educational Safety >
Maintainability > Testability > Observability > Performance >
Developer Convenience > UI Polish) atanmıştır. Effort: S/M/L.

| Area | Current | Target | CLAUDE.md § | Severity | Effort |
|---|---|---|---|---|---|
| Git deposu | Yok | Versiyon kontrolü altında proje | §103 | Yüksek (Correctness/Maintainability temeli) | S |
| Docker Compose iskeleti | Yok | postgres/redis/api/web/n8n, health check | §91 | Orta | M |
| Backend (FastAPI) iskeleti | Yok | Modüler monolit, ince route'lar | §13,§15–16 | Yüksek | M |
| Frontend (Next.js) iskeleti | Yok | App shell, TS, Tailwind, shadcn/ui | §17 | Orta | M |
| Kimlik/Tenant/RBAC | Yok | Sunucu taraflı tenant izolasyonu, 6 rol | §50–53 | **Kritik** (Security/Privacy) | L |
| Cross-tenant negatif testler | Yok | Her tenant-scoped kaynak için A↔B testi | §52,§88 | **Kritik** (Security) | M |
| Eğitim domain modeli (Curriculum→Skill) | Yok | Versiyonlu müfredat, prerequisite graf | §19–20 | Yüksek (Correctness) | M |
| Assessment/Observation/Evidence ayrımı | Yok | Observation'da yorum yok, Evidence FK ile ayrı | §21–23 | Yüksek (PDE bilimsel bütünlük öncülü) | M |
| Event sourcing / append-only log | Yok | Immutable event tablosu, DB seviyesinde zorunlu | §40 | Yüksek (Data Integrity) | M |
| Bilgi Durumu + Bayesian güncelleme | Yok | ADR önce (§25), sonra Beta-Binomial servis | §24–27,§98 | **Kritik** (PDE Scientific Integrity) | L |
| PDE karar motoru | Yok | Yapılandırılmış karar, yetkilendirme ayrımı, shadow mode | §32–39 | **Kritik** (PDE Scientific Integrity) | L |
| Transfer/Retention/Falsification | Yok | 14/28 gün checkpoint, hipotez kayıtları | §29–31,§39 | Yüksek | M |
| AI Gateway | Yok | Provider-agnostic, cost tracking, Ollama local-first | §43–49 | Orta (MVP sonrası) | M |
| Dashboard'lar | Yok | Student/Teacher/Admin, tenant-scoped agregasyon | §74–77 | Orta (MVP sonrası) | M |
| SaaS/Entitlement/Billing | Yok | Plan→Entitlement→Feature Access, ayrı modül | §59–66,§95 | Orta (MVP sonrası) | L |
| Observability (Prometheus/Grafana) | Yok | Metrik, decision log, dashboard | §83–85 | Orta (MVP sonrası) | M |
| Dokümantasyon/ADR | Sadece bu rapor | `docs/adr/` içinde 10 ADR | §101–102 | Düşük-Orta | S (her ADR ayrı) |

Not: "Effort" her satır için toplam faz büyüklüğünü gösterir; gerçek
uygulamada her biri §125–126 gereği çok daha küçük dikey dilimlere
bölünecektir (bkz. Bölüm 5).

---

## 4. RISKS

**(a) Mevcut kodda risk:** Yok — değerlendirilecek kod, migration veya
konfigürasyon mevcut değil. Tek gözlem: depo git ile izlenmiyor, bu da
şu anki üç dosyanın (CLAUDE.md dahil) kazara kaybolmasına karşı hiçbir
koruma olmadığı anlamına geliyor (versiyon geçmişi yok).

**(b) İleride yapılacak değişikliklerin yaratacağı riskler:**
- **Tenant izolasyonu:** Faz 1'de (P0 Foundation) tenant_id kolonu olmadan
  tablo/model tasarlanırsa, Faz 2'de (P1) sonradan eklemek §147'nin
  yasakladığı bir "retrofit" haline gelir ve kritik bir güvenlik açığı
  riski doğurur. **Öneri:** Faz 1'de boş bile olsa domain modülü sınırları
  ve ileride tenant_id taşıyacak tablo iskeletleri bu ayrımı gözeterek
  tasarlanmalı.
- **PDE matematik bütünlüğü:** Bilgi durumu / Bayesian güncelleme (Faz 5)
  ADR onayı olmadan koda geçerse §98 ve §147 ihlal edilir; bu rapor hiçbir
  matematiksel formülasyon önermez, önerilmemelidir de (Faz 5 STEP 5A'nın
  konusu).
- **Event sourcing gecikmesi:** Assessment/Observation/Evidence (Faz 4)
  append-only olarak DB seviyesinde kısıtlanmadan yazılırsa, sonradan bunu
  eklemek geçmiş veriyi bozma riski taşır — bu yüzden Faz 4'te bu kısıt
  en baştan (ilk migration'da) konmalı.
- **Boş depo + git yokluğu:** Faz 1 sırasında ilk commit atılmadan çok
  dosya üretilirse, "hangi değişiklik hangi amaçla yapıldı" izlenebilirliği
  kaybolur (§103 küçük anlamlı commit ilkesiyle çelişir).

Güvenlik, gizlilik, veri bütünlüğü, tenant izolasyonu veya PDE bilimsel
bütünlüğüne dokunan somut bir mevcut ihlal **yoktur** — çünkü henüz hiçbir
şey inşa edilmemiştir. Riskler tamamen ileriye dönüktür.

---

## 5. RECOMMENDED IMPLEMENTATION ORDER

§113 P0–P10 merdiveni ile EDUPULSE-CLAUDE-CODE-PHASES.md Faz 1–11 birebir
örtüşüyor; sıralama aynen izlenmelidir çünkü her faz bir öncekinin üzerine
kurulur (özellikle tenant/RBAC temelinin en erken atılması, PDE'nin
Observation/Evidence ayrımına bağımlı olması kritik):

1. **Faz 1 — P0 Foundation** (bağımlılık yok, ilk adım): git init, Docker
   Compose, FastAPI+Next.js iskeleti, Alembic baseline, test harness.
2. **Faz 2 — P1 Identity/Tenant/RBAC** (Faz 1'e bağımlı): tenant modeli,
   auth, RBAC, cross-tenant negatif testler. Bu olmadan hiçbir sonraki
   domain verisi güvenle tenant-scoped olamaz.
3. **Faz 3 — P2 Eğitim Domain** (Faz 1+2'ye bağımlı): Curriculum→Skill
   hiyerarşisi, tenant-scoped CRUD.
4. **Faz 4 — P3 Assessment/Observation/Evidence** (Faz 2+3'e bağımlı):
   event sourcing en baştan append-only.
5. **Faz 5 — P4 Bilgi Durumu** (Faz 4'e bağımlı, Evidence gerekli):
   ÖNCE ADR (5A), SONRA implementasyon (5B) — asla birleştirilmez.
6. **Faz 6 — P5 PDE** (Faz 5'e bağımlı, Knowledge State gerekli): karar
   motoru, yetkilendirme, shadow mode.
7. **Faz 7 — P6 Transfer/Retention/Falsification** (Faz 6'ya bağımlı).
8. **MVP GATE** — Faz 1–7 sonrası, uygulamaya geçmeden doğrulama.
9. **Faz 8–11 — P7–P10** (MVP onaylandıktan sonra): AI Gateway, Dashboard,
   SaaS/Billing, Hardening — MVP gate PASS olmadan başlatılmamalı (§115,
   dokümanın kendi kuralı).

Her faz kendi içinde §126 dikey dilim ilkesiyle (Domain→DB→Service→API→
Frontend→Test) daha da küçük parçalara bölünmelidir; bu rapor faz sırasını
onaylıyor, alt-dilimlerin detayını değil (o, her fazın kendi §122
Pre-Implementation Report'unda ele alınacak).

---

## 6. FILES THAT SHOULD BE MODIFIED

Şu an depoda değiştirilecek hiçbir dosya yok. Faz 1 onaylandığında ilk
oluşturulacak/değiştirilecek dosyalar (bu denetimin kapsamı dışında, sadece
bilgi amaçlı):
- `docker-compose.yml`, `.env.example`, `Makefile`, `README.md` — yeni.
- `apps/api/`, `apps/web/` altında iskelet dosyalar — yeni.

---

## 7. FILES THAT SHOULD NOT BE MODIFIED

- `Claude.md` (= CLAUDE.md) — anayasa; yalnızca kullanıcının açık onayıyla
  değiştirilir (§0).
- Mevcut migration: **NOT PRESENT**, dolayısıyla "dokunulmayacak migration"
  listesi şu an boş.

---

## 8. DATABASE CHANGES

Şu an veritabanı yok. Faz 1'de önerilecek ilk değişiklik: tek bir Alembic
baseline migration'ı (boş/iskelet şema). Bu **additive** bir başlangıçtır,
yıkıcı değildir. Backfill ihtiyacı yok (veri yok). İndeks etkisi yok.
Bu denetim aşamasında somut bir şema deltası önerilmemektedir — şema
tasarımı Faz 1 §122 raporunda ayrıca sunulacaktır.

---

## 9. API CHANGES

Şu an API yok. Yeni/değişen/kaldırılan endpoint yok. Geriye dönük uyumluluk
endişesi bu aşamada söz konusu değil (§107, §128) — ilk API yüzeyi Faz 1'de
tanımlanacak.

---

## 10. PDE (DECISION ENGINE) CHANGES

Şu an PDE yok. Bu rapor **hiçbir matematiksel formülasyon önermemektedir**
ve önermemelidir — §98/§147 gereği bu, Faz 5 STEP 5A'da ayrı bir ADR ile,
kullanıcı onayı alınarak yapılacaktır. Reproducibility ve explainability
gereksinimleri Faz 6 (P5) kapsamında en baştan tasarıma dahil edilecek,
sonradan eklenmeyecek.

---

## 11. OBSERVABILITY / PROMETHEUS-GRAFANA CHANGES

Şu an gözlemlenebilirlik yığını yok. Metrik, decision log veya dashboard
önerisi bu aşamada yok — bu Faz 11 (P10) kapsamına girer; ancak decision
logging'in temel alanları (§85) Faz 6'da PDE ile birlikte en baştan
tasarlanmalıdır (sonradan eklemek yerine).

---

## 12. TEST STRATEGY

Şu an test yok. Faz 1'in somut test beklentisi (§86, DoD'den):
- pytest: `tests/unit/`, `tests/integration/`, `tests/api/` dizinleri,
  test veritabanı fixture'ı, her katmandan en az bir gerçek geçen test
  (placeholder değil).
- Frontend: bir test runner kurulumu ve en az bir gerçek geçen test.
- `make test` tek komutla hepsini çalıştırmalı.

Property-based testler (§87) Faz 5'te (Bayesian model) ve cross-tenant
testler (§88) Faz 2'de (tenant/RBAC) zorunlu hale gelecek — Faz 1'de
henüz uygulanacak domain mantığı olmadığından kapsam dışı.

---

## 13. OPEN QUESTIONS

Bunlar kullanıcı tarafından karar verilmeli, ben varsayılan seçmedim:

1. Depo gerçekten sıfırdan mı başlıyor, yoksa mevcut kod başka bir dizinde/
   repoda mı bulunuyor ve yanlışlıkla bu boş dizinde mi çalışıyoruz?
2. Git deposunun başlatılması (`git init`) Faz 1'in bir parçası olarak mı
   ele alınsın, yoksa şimdi ayrı bir adım olarak mı yapılsın?
3. n8n ve Ollama bu erken aşamada Docker Compose'a dahil edilsin mi, yoksa
   ilk gerçekten ihtiyaç duyulduğunda mı (n8n için Faz 7/P6 retention
   scheduling, Ollama için Faz 8/P7 AI Gateway) eklensin?
4. §57'deki hedef klasör yapısı Faz 1'de tam iskelet olarak mı kurulsun
   (tüm boş dizinlerle), yoksa yalnızca P0 kapsamındaki modüller mi
   oluşturulsun?
5. Bu Faz 0 raporu onaylandıktan sonra bir sonraki adım olarak doğrudan
   Faz 1'in §122 Pre-Implementation Report'una mı geçilsin?

---

## 14. COVERAGE CHECKLIST

| # | Madde | Durum |
|---|---|---|
| 1 | Depo yapısı | INSPECTED |
| 2 | Uygulamalar | INSPECTED — mevcut değil |
| 3 | Backend mimarisi | INSPECTED — mevcut değil |
| 4 | Frontend mimarisi | INSPECTED — mevcut değil |
| 5 | Veritabanı modelleri | INSPECTED — mevcut değil |
| 6 | Migration'lar | INSPECTED — mevcut değil |
| 7 | Docker yapılandırması | INSPECTED — mevcut değil |
| 8 | API endpoint envanteri | INSPECTED — mevcut değil |
| 9 | PDE uygulama durumu | INSPECTED — mevcut değil |
| 10 | Prometheus/Grafana durumu | INSPECTED — mevcut değil |
| 11 | Testler | INSPECTED — mevcut değil |
| 12 | Auth/RBAC | INSPECTED — mevcut değil |
| 13 | Tenant mimarisi | INSPECTED — mevcut değil |
| 14 | AI/LLM entegrasyonu | INSPECTED — mevcut değil |
| 15 | n8n entegrasyonu | INSPECTED — mevcut değil |
| 16 | Event sourcing/provenance | INSPECTED — mevcut değil |
| 17 | Dokümantasyon | INSPECTED — bu rapor öncesi mevcut değildi |
| 18 | Git durumu | INSPECTED — git deposu başlatılmamış |

---

## SONUÇ VE DUR NOKTASI

Depo şu an tamamen boş bir başlangıç noktası — CLAUDE.md'de tarif edilen
hiçbir katman (Identity, Education, Assessment, Knowledge State, PDE,
Authorization) mevcut değil. Bu, kötü bir haber değil: sıfırdan, CLAUDE.md'nin
anayasasına tam uyumlu şekilde inşa etme fırsatı demek.

PHASE0-AUDIT-PROMPT.md'nin STEP 6 talimatı gereği burada duruyorum. Kod
yazmadım, migration oluşturmadım, yeniden yapılandırma yapmadım, Faz 1'e
başlamadım. Bölüm 13'teki açık soruların yanıtlarını ve hangi adlandırılmış
dilimi (muhtemelen Faz 1 — P0 Foundation) onayladığınızı bekliyorum.
