# AnimeinAPI v2

Tentang AnimeinAPI V2. Mengambil metadata, daftar episode, dan **stream multi-resolusi (360p/480p/720p/1080p)** dari website streaming `animeinweb.com`.

## Statistik

- **4.779** judul anime
- **75.000+** episode
- **33** genre (Genre, Theme, Demographic)

## Endpoint

| Method | Path | Deskripsi | Status |
|---|---|---|---|
| GET | `/api/search?q=&page=&sort=&genre=` | Cari anime (pageSize 18) | ✓ |
| GET | `/api/genres` | Daftar genre (33, grup Genre/Theme) | ✓ |
| GET | `/api/home?day=&limit=` | Data homepage: slider, hot, new, today, popular, waiting, random, trailer | ✓ |
| GET | `/api/schedule?day=` | Jadwal rilis per hari (SENIN..MINGGU/RANDOM) | ✓ |
| GET | `/api/anime/{id}` | Metadata lengkap anime | ✓ |
| GET | `/api/anime/{id}/episodes` | Daftar episode (urut naik) | ✓ |
| GET | `/api/anime/{id}/trailers` | Trailer YouTube | ✓ |
| GET | `/api/episode/{id}/streams` | Server stream per resolusi + `episode_next` | ✓ |
| GET | `/api/chat?highest_id=&lowest_id=` | Chat global komunitas (polling, window 100 pesan) | ✓ |
| GET | `/api/episode/{id}/comments?sort=&page=` | Komentar per episode (30/halaman) + cover/poster | ✓ |
| GET | `/api/ads?tag=` | Iklan terstruktur (video/image/redirect) | ✓ |
| GET | `/metrics` | Latency per path (avg/p50/p95) | ✓ |
| GET | `/healthz` | Health check | ✓ |
| GET | `/docs` | Swagger UI (FastAPI bawaan) | ✓ |

## Referensi API

### Search / Catalog
```
GET /api/search?q=naruto&page=0&sort=views&genre=14,43
```
- `q` — kata kunci judul
- `page` — 0-based (pageSize 18)
- `sort` — `views` (default) | `newest` | `year` | `rating`
- `genre` — id genre dipisah koma (ambil dari `/api/genres`)

### Home
```
GET /api/home?day=MINGGU&limit=16
```
Mengembalikan 8 section: `slider` (banner), `hot`, `new`, `today`, `popular`, `waiting` (belum tayang), `random`, `trailer` — plus `setup_fyp_flag`/`setup_fyp_name`.

### Schedule
```
GET /api/schedule?day=SENIN
```
Jadwal rilis. `day` = MINGGU/SENIN/SELASA/RABU/KAMIS/JUMAT/SABTU/RANDOM.

### Stream multi-reso
```
GET /api/episode/35969/streams
```
```json
{
  "episode": {"id": "35969", "index": "25", "title": "Episode 25"},
  "episode_next": {"id": "...", "index": "26"},
  "streams": {
    "360p": [{"id": "599380", "link": "https://storages.animein.net/...25-360p-....mp4", "type": "direct", "name": "RAPSODI", "key_file_size": "25.78"}],
    "480p": [...],
    "720p": [...]
  }
}
```
- `streams` dikelompokkan per kualitas; `type: direct` = MP4 dari `storages.animein.net`, `type: semi` = embed pihak ketiga
- `episode_next` untuk auto-continue

### Chat
```
GET /api/chat
```
Pesan global komunitas (nama user, avatar pokemon, rank, pro, balasan). `refresh` = interval polling (3000ms).

### Komentar
```
GET /api/episode/5017/comments?sort=new&page=0
```
Komentar per episode + `cover`/`poster`.

## Instalasi & menjalankan

```bash
pip install -e ".[dev]"
python -m uvicorn animeinapi.main:app --port 8000
# atau
animein
```

Tanpa `.env` pun bisa jalan. Cukup salin `.env.example` ke `.env` jika ingin mengubah base URL, timeout, atau retries.

## Konfigurasi (env)

| Var | Default | Keterangan |
|---|---|---|
| `ANIMEIN_BASE_URL` | `https://animeinweb.com` | Situs sumber |
| `ANIMEIN_PROXY_SECRET` | value publik frontend | Header `x-proxy-secret` |
| `ANIMEIN_TIMEOUT` | `15` | Timeout request (detik) |
| `ANIMEIN_RETRIES` | `2` | Retry untuk 429/5xx/network error |
| `ANIMEIN_LOG_LEVEL` | `INFO` | Log level |

## Struktur

```
animeinapi/
├── main.py            # FastAPI app + lifespan + warmup + metrics
├── config.py          # Settings via pydantic-settings
├── models.py          # Pydantic models (Anime, Episode, Stream, Genre, Home, Trailer, Chat, Comment, Ad)
├── core/
│   ├── cache.py       # Cache TTL in-memory (single-flight + SWR + negative cache)
│   ├── client.py      # Async httpx client + retry/backoff
│   ├── constants.py   # TTL & konstanta lain
│   └── service.py     # Orkestrasi semua operasi domain
└── api/routes.py      # Endpoint HTTP
tests/                 # pytest + respx (mocked transport, 13 tes)
```

## Tes

```bash
python -m pytest
```
