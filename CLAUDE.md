# CLAUDE.md — Projekt-spezifische Agent-Hinweise

## Projekt-Kontext

- **Was:** Long-running Python-Service, der auf `https://www.payback.de/coupons` per Playwright alle nicht aktivierten Coupons aktiviert und über ein FastAPI-Dashboard gesteuert wird.
- **Stack:** Python 3 (Playwright-Base-Image), Playwright 1.58.0, FastAPI + Uvicorn, APScheduler, loguru.
- **Auth-Modell:** Keine Login-Flows — Authentifizierung ausschliesslich über vom Nutzer exportierte `cookies.json` (Cookie-Editor-Browser-Extension-Format), die in Playwright-Format konvertiert wird (`src/browser.py::load_cookies`).
- **Status persistiert in:** `data/cookies.json` (Volume), zur Laufzeit zusätzlich im `AppState`-Singleton (`src/web/state.py`).
- **Logging:** loguru, Konsole + `logs/payback_YYYY-MM-DD.log`, Rotation 1 Tag, Retention 7 Tage.
- **Repository:** `ssh://git@ssh.github.com:443/fynnsh/payback-coupon-activator.git`.

## Build / Test / Run

### Lokal (venv)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m src.main
```

### Docker (Standard)

```bash
docker compose up -d --build
docker compose logs -f
docker compose restart
docker compose down
```

### Tests

- **Keine vorhanden.** Vor Behauptungen über Verhalten: nicht raten, sondern Code lesen oder im Container reproduzieren.

### Manueller Smoke-Test

1. `docker compose up -d`
2. `curl http://localhost:8080/api/status` → JSON-Response mit `cookie_count`
3. Dashboard im Browser unter `http://localhost:8080`
4. Optional: `curl -X POST http://localhost:8080/api/trigger` (nur wenn Cookies vorhanden)

## Wichtige Konventionen

- **Sprache:** Code-Kommentare/Logs auf Englisch, Dashboard-UI auf Deutsch, README/CLAUDE auf Deutsch.
- **Async überall:** Alle Browser-, Scheduler-, FastAPI-Pfade sind async. Keine sync Blocker einbauen.
- **Konfiguration ausschliesslich über `Config`-Klasse** (`src/config.py`). Keine direkten `os.getenv`-Calls in anderen Modulen.
- **Cookie-Format:** Eingehend Cookie-Editor-Schema (`expirationDate`, `sameSite="no_restriction"`, …), umgewandelt in Playwright-Schema (`expires`, `sameSite="None"`). Konvertierung **nur** in `load_cookies`.
- **`extract_cookie_metadata` liest BEWUSST keine `name`/`value`-Felder** — nur Domain, Expiry, Session-Flag. Bei Erweiterungen dieser Funktion das Datenschutz-Versprechen halten.
- **Atomarer Cookie-Upload:** `tempfile.mkstemp` im selben Verzeichnis + `os.replace`. Niemals direkt in `COOKIES_FILE` schreiben.
- **Selektor für Coupon-Buttons:** `button.coupon__activate-button.not-activated`. Hartkodiert in `coupon_activator.py`. Bei Änderungen am Payback-Frontend ist dies die erste zu prüfende Stelle.
- **Rate-Limit:** Nach `RATE_LIMIT_BATCH_SIZE` (Default 100) Klicks für `RATE_LIMIT_PAUSE_HOURS` (Default 1 h) schlafen und Seite neu laden.
- **Graceful Shutdown:** SIGTERM/SIGINT → `_shutdown` → Scheduler down, Uvicorn `should_exit=True`. Nicht durch direkten `sys.exit` ersetzen.
- **Container läuft als non-root** (`appuser`). `/app/data` und `/app/logs` müssen schreibbar sein.

## Deploy-Pfad

- **Aktuell:** Manuelles `docker compose up -d` auf Zielhost. Kein Coolify-Service angelegt (per `mcp__coolify__list_applications` verifiziert, Stand 2026-05-20), keine CI/CD.
- **Empfehlung für Hosting:** Hinter Reverse-Proxy mit Auth (Traefik + BasicAuth oder Authentik), da `/api/trigger` und `/api/cookies` ungeschützt sind.
- **Volumes (müssen persistieren):**
  - `./data` → enthält `cookies.json` (sensibel!)
  - `./logs` → enthält tägliche Logs
- **Ports:** Default 8080 (über `WEB_PORT` änderbar).
- **Zeitzone:** `TZ=Europe/Berlin` setzt sowohl Container-Zeit als auch loguru-Timestamps.

## Bekannte Stolperfallen

- **Chromium braucht `shm_size: 1gb`** im Compose — sonst Crashes bei vielen Seitenladungen. Bereits gesetzt, nicht entfernen.
- **`docker compose up` löst initialen Run sofort aus**, sofern `data/cookies.json` existiert. Bei frischem Setup ohne Cookies wartet der Service ruhig auf den Upload.
- **`.dockerignore` schliesst `*.md` aus** — Doku landet nicht im Image, READMEs im Container fehlen daher absichtlich.
- **`cookies.json` und `.env` sind gitignored.** Nicht aus Versehen committen. Im Repo-Root liegen historisch `cookies.json` und `.env` als Datei — bei Migration auf `data/cookies.json` darauf achten, dass die alte Datei nicht überschrieben wird.
- **`COOKIES_FILE`-ENV im Dockerfile (`/app/data/cookies.json`)** weicht vom lokalen Default (`<BASE>/cookies.json`) ab. Lokal ohne ENV liegt die Datei im Projektroot — im Container im `data/`-Volume.
- **Manueller Trigger setzt `is_running=True` VOR `asyncio.create_task`** — bewusste Race-Condition-Vermeidung, beim Refactoring nicht umdrehen.
- **`max_instances=1` an APScheduler-Jobs** verhindert parallele Runs. Wenn ein Job länger läuft als das Intervall, werden Folge-Runs übersprungen — gewollt.
- **Cookie-Banner-Dismiss-Selektor** ist deutschsprachig (`"Alle Cookies akzeptieren"`). Bei `locale`-Änderungen anpassen.
- **Keine Authentifizierung** am Dashboard. Service **niemals** öffentlich exposen ohne Reverse-Proxy-Auth.

## Externe Abhängigkeiten

| Dienst | Zweck | Notizen |
|---|---|---|
| `payback.de/coupons` | Aktivierungs-Ziel | Selektor-Änderungen brechen den Service |
| `mcr.microsoft.com/playwright/python:v1.58.0-jammy` | Docker-Base-Image | Version mit `playwright`-Pin synchron halten |
| Browser-Extension `Cookie-Editor` | Cookie-Export beim Nutzer | Kein eigener Login-Flow im Service |

Keine Datenbank, keine Message-Queue, keine externen APIs ausser Payback.

## Verweise

- Globale Regeln: `~/.claude/CLAUDE.md`
- Workspace-Infra: `/Users/wfy/Documents/private/.claude/CLAUDE.md`
- Backup vorherige README: `README.backup.md`
