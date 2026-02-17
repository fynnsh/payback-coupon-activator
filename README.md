# Payback Coupon Activator

Automatisiert die Aktivierung aller verfügbaren Payback-Coupons per Browser-Automation — mit Web-Dashboard zum Steuern und Überwachen.

![Dashboard](docs/dashboard.png)

> **Disclaimer:** Dieses Tool dient ausschließlich der persönlichen Nutzung. Die Verwendung erfolgt auf eigene Verantwortung. Bitte die Nutzungsbedingungen von Payback beachten.

## Features

- Automatische Aktivierung aller verfügbaren Coupons
- Web-Dashboard mit Live-Status, Cookie-Upload und manueller Aktivierung
- Geplante Ausführung (Standard: alle 24 Stunden)
- Rate-Limit-Schutz mit konfigurierbarer Pause
- Docker-Support für VPS-Deployment

## Quickstart (Docker)

```bash
git clone https://github.com/<user>/payback-activator.git
cd payback-activator
cp .env.example .env
docker compose up -d
```

Danach das Dashboard unter `http://localhost:8080` öffnen und die `cookies.json` per Drag & Drop hochladen.

![Upload](docs/upload.png)

## Cookie-Export

1. Im Browser bei [payback.de](https://www.payback.de) einloggen
2. Browser-Extension **Cookie-Editor** installieren ([Chrome](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) · [Firefox](https://addons.mozilla.org/de/firefox/addon/cookie-editor/))
3. Auf payback.de die Extension öffnen → **Export → JSON**
4. Datei über das Web-Dashboard hochladen oder als `cookies.json` im Projektverzeichnis speichern

Die Cookies müssen erneuert werden, wenn die Session abläuft.

## Konfiguration

Alle Einstellungen über `.env` oder Environment-Variablen:

| Variable | Beschreibung | Standard |
|---|---|---|
| `SCHEDULE_INTERVAL_HOURS` | Intervall zwischen Aktivierungen (Stunden) | `24` |
| `COOLDOWN_SECONDS` | Pause zwischen Coupon-Klicks (Sekunden) | `1` |
| `HEADLESS` | Browser ohne GUI (`true` für VPS/Docker) | `true` |
| `RATE_LIMIT_BATCH_SIZE` | Coupons vor Rate-Limit-Pause | `100` |
| `RATE_LIMIT_PAUSE_HOURS` | Pause-Dauer in Stunden | `1` |
| `WEB_PORT` | Port für das Web-Dashboard | `8080` |
| `TZ` | Zeitzone | `Europe/Berlin` |

## Lokale Entwicklung

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m src.main
```

## VPS-Deployment

```bash
git clone https://github.com/<user>/payback-activator.git
cd payback-activator
cp .env.example .env
docker compose up -d
```

Cookies per Web-Dashboard hochladen oder per `scp` als `cookies.json` ins Projektverzeichnis kopieren.

```bash
# Logs prüfen
docker compose logs -f
```

## Projektstruktur

```
payback-activator/
├── src/
│   ├── main.py              # Einstiegspunkt, Scheduler
│   ├── config.py            # Konfiguration
│   ├── browser.py           # Playwright Browser-Setup
│   ├── coupon_activator.py  # Coupon-Aktivierungslogik
│   └── web/
│       ├── app.py           # Web-Dashboard (FastAPI/Starlette)
│       └── state.py         # Shared State
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Lizenz

[MIT](LICENSE)
