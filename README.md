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

`n8n` ve `ollama` bu fazda dahil edilmedi; ihtiyaç duyulduğunda (sırasıyla
Faz 7 — gecikmeli hatırlama zamanlaması ve Faz 8 — AI Gateway) eklenecek.

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
