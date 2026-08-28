# EduPulse AI

Kanıta dayalı, adaptif öğrenme platformu. Bkz. `Claude.md` (CLAUDE.md) —
depodaki mühendislik anayasası. Bu README yalnızca yerel geliştirme
kurulumunu anlatır.

## Durum

Faz 1 — P0 Foundation: çalışan bir iskelet. Kimlik doğrulama, kiracı
yönetimi, eğitim domaini, PDE (karar motoru), AI entegrasyonu ve
dashboard'lar henüz yok — bunlar sonraki fazlarda gelecek
(`EDUPULSE-CLAUDE-CODE-PHASES.md`).

## Gereksinimler

- Docker ve Docker Compose
- (İsteğe bağlı, Docker dışında geliştirme için) Python 3.12+, Node.js 20+

## Kurulum

1. `.env.example` dosyasını `.env` olarak kopyalayın ve gerekirse değerleri
   düzenleyin:

   ```
   cp .env.example .env
   ```

2. Servisleri ayağa kaldırın:

   ```
   make up
   ```

3. Veritabanı migration'ını çalıştırın:

   ```
   make migrate
   ```

4. Servisleri kontrol edin:
   - API sağlık kontrolü: http://localhost:8000/health
   - Web arayüzü: http://localhost:3000

## Testler

```
make test
```

Katman bazlı çalıştırmak için: `make test-api`, `make test-web`.

`pytest`, gerçek geliştirme veritabanınızı hiç kullanmaz — ayrı bir
`edupulse_test` veritabanına yazar (`TEST_DATABASE_URL`,
`docker-compose.yml`). Bu veritabanı, **taze bir `postgres_data` volume'ünde**
`infrastructure/postgres/init/01-create-test-db.sql` tarafından otomatik
oluşturulur (Postgres imajı `docker-entrypoint-initdb.d` script'lerini yalnızca
ilk kurulumda çalıştırır). Zaten var olan bir volume'de çalışıyorsanız (örn.
bu depo Faz 3 öncesinde kurulduysa) bir kerelik elle oluşturmanız gerekir:

```
docker compose exec postgres psql -U edupulse -d edupulse -c "CREATE DATABASE edupulse_test;"
```

## Servisler

| Servis | Açıklama | Port |
|---|---|---|
| `postgres` | PostgreSQL 16 | 5432 |
| `redis` | Redis 7 | 6379 |
| `api` | FastAPI backend | 8000 |
| `web` | Next.js frontend | 3000 |
| `ollama` | Yerel LLM (AI Gateway, §44) | 11434 |

`ollama` compose dosyasında tanımlı ama **varsayılan olarak çalıştırılmaz/
model indirilmez**. Gerçek donanımda test edildi (bkz.
docs/adr/ADR-015-ai-gateway.md, "Addendum — Real Hardware Verification"):
CPU-only / GPU hızlandırmasız mütevazı makinelerde bile 1-3B parametreli
küçük modeller (varsayılan: `llama3.2:1b`) makul hızda (~10 token/sn)
çalışıyor; 8B+ modeller önerilmiyor.

İki kurulum seçeneği:
- **Host'ta native (test edilen, önerilen)**: Ollama'yı Windows/Mac/Linux'a
  doğrudan kurun (https://ollama.com/download), `ollama serve` çalıştırın,
  `ollama pull llama3.2:1b`. `docker-compose.yml` `api` servisini otomatik
  olarak `http://host.docker.internal:11434` üzerinden host'a yönlendirir.
- **Docker container olarak**: `docker compose up -d ollama`, ardından
  `docker compose exec ollama ollama pull llama3.2:1b`.

Her iki durumda da: `POST /ai/explanations` ile gerçek bir açıklama
üretebilirsiniz.

`n8n` bu fazda dahil edilmedi; ihtiyaç duyulduğunda (Faz 7'nin gecikmeli
hatırlama zamanlama tetikleyicisi için) eklenecek.

## Depo yapısı

```
apps/
  api/    FastAPI backend (Python) — bkz. apps/api altındaki katmanlar
  web/    Next.js frontend (TypeScript)
docs/
  audit/  Faz 0 depo denetim raporu
```

Diğer modül sınırları (identity, tenancy, education, assessment,
learning_state, prometheus/PDE, ai, content, analytics, billing, usage,
notifications — CLAUDE.md §54) her biri gerçekten ihtiyaç duyulduğu fazda
kademeli olarak açılacak; önceden boş dizin olarak oluşturulmadı.

## Diğer komutlar

`make down`, `make logs`, `make lint`, `make format`, `make seed`
(`Makefile` içinde tanımlı).
