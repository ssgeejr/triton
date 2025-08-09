# Triton – DIY Smart Irrigation (System Architecture & README)

> **Goal:** A DIY controller that turns a single garden solenoid on/off based on schedules and weather, with a simple cloud back end and a Raspberry Pi on‑prem controller.

---

## 1) High‑Level Architecture

```
           Mobile Browser
                 │
                 ▼
        ┌───────────────────┐        hourly pull             ┌───────────────┐
        │  Tomcat (Java)    │  ───────────────────────────▶ │  Raspberry Pi │
        │  JSP UI + REST    │   JSON schedules & settings    │  (Python)     │
        └────────┬──────────┘                                 └─────┬────────┘
                 │                                                GPIO │
                 │  JDBC                                             ▼
                 ▼                                             ┌────────────┐
          ┌───────────────┐                                    │  Solenoid  │
          │   HSQLDB       │                                    └────────────┘
          └───────────────┘
```

- **Cloud**: Dockerized Apache Tomcat (JSP front end, Java backend) + HSQLDB for persistence, orchestrated by a single `docker compose` file.
- **Edge**: Raspberry Pi (Python) controls **one** solenoid via a relay or MOSFET driver. Polls the cloud hourly (configurable) for schedules/overrides and weather‑based hold.
- **UX**: Phone used as the client (mobile browser) to manage schedules and manual runs.

---

## 2) Repository Layout (proposed)

```
triton/
├─ cloud/
│  ├─ compose.yml
│  ├─ tomcat/                 # Java webapp source (JSP + REST)
│  │  ├─ src/main/java/
│  │  ├─ src/main/webapp/
│  │  └─ pom.xml
│  └─ hsqldb/                 # DB files & init scripts
│     ├─ data/
│     └─ init.sql
├─ edge/
│  └─ pi/
│     ├─ triton.py            # main Python controller
│     ├─ config.yaml          # device_id, poll_interval, api_url, gpio pins
│     └─ requirements.txt
└─ docs/
   └─ README.md (this file)
```

---

## 3) Data Model (HSQLDB)

**Tables (first pass):**

```sql
-- Control metadata & configuration
CREATE TABLE IF NOT EXISTS controller_config (
  key        VARCHAR(64) PRIMARY KEY,
  value      VARCHAR(256) NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example keys: poll_interval_minutes, weather_provider, weather_api_key,
-- device_auth_mode, device_token, rain_hold_hours, timezone

CREATE TABLE IF NOT EXISTS devices (
  device_id    VARCHAR(64) PRIMARY KEY,
  name         VARCHAR(64),
  last_checkin TIMESTAMP,
  status       VARCHAR(16) DEFAULT 'OK'
);

-- Watering schedules (simple window model)
CREATE TABLE IF NOT EXISTS schedules (
  id           INTEGER IDENTITY PRIMARY KEY,
  device_id    VARCHAR(64) NOT NULL,
  start_time   TIME NOT NULL,        -- local time of day
  duration_min INT  NOT NULL,
  days_mask    VARCHAR(7) NOT NULL,  -- e.g., 1111100 (Mon..Sun)
  enabled      BOOLEAN DEFAULT TRUE,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- One‑off overrides (manual runs / holds)
CREATE TABLE IF NOT EXISTS overrides (
  id           INTEGER IDENTITY PRIMARY KEY,
  device_id    VARCHAR(64) NOT NULL,
  type         VARCHAR(16) NOT NULL,    -- 'RUN_NOW' | 'HOLD_UNTIL'
  param        VARCHAR(64) NOT NULL,    -- e.g., minutes or ISO timestamp
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at   TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- Audit log
CREATE TABLE IF NOT EXISTS events (
  id           INTEGER IDENTITY PRIMARY KEY,
  device_id    VARCHAR(64),
  event_type   VARCHAR(32),   -- CHECKIN, WATER_ON, WATER_OFF, HOLD, ERROR
  message      VARCHAR(512),
  at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Notes:**

- `days_mask` provides a compact weekly schedule; alternate is an RFC 5545‑style RRULE if needed later.
- `overrides` allows a quick **RUN NOW for N minutes** or a **RAIN HOLD** until timestamp.

---

## 4) Device ↔ Cloud API (first pass)

All endpoints are under `/api/v1`. Auth via **device token** (simple shared secret for MVP) sent as `Authorization: Bearer <token>`.

**Device → Cloud**

- `POST /api/v1/devices/{deviceId}/checkin`
  - Body: `{ "fw":"1.0.0", "capabilities":["relay1"], "sensors":{...} }`
  - Response: consolidated directive:
    ```json
    {
      "poll_interval_minutes": 60,
      "hold_until": "2025-08-09T18:00:00Z",
      "schedules": [
        {"start_time":"06:00","duration_min":15,"days_mask":"1111100","enabled":true}
      ],
      "manual_run": null
    }
    ```

**Cloud → Device (admin via UI)**

- `GET /api/v1/devices/{deviceId}/status`
- `POST /api/v1/devices/{deviceId}/overrides`  (e.g., `{ "type":"RUN_NOW", "param":"10" }`)
- `POST /api/v1/schedules` / `DELETE /api/v1/schedules/{id}`

**Server behaviors**

- On `checkin`, compute effective state: apply active overrides, evaluate weather hold, and return the *next actions* plus poll interval.

---

## 5) Weather Integration (MVP)

- Add `controller_config.weather_provider` and `weather_api_key`.
- Server checks forecast (e.g., upcoming 12–24h) for **rain probability/amount**; if ≥ threshold or it’s currently raining, set a **hold** window and persist it to `overrides` or a computed `hold_until`.
- Thresholds configurable: `rain_probability_threshold` (e.g., 50%), `rain_amount_mm_threshold` (e.g., 2mm).

*(We can swap providers later; the Pi never talks to weather APIs directly.)*

---

## 6) Docker Compose (cloud)

```yaml
version: "3.9"
services:
  triton-tomcat:
    image: tomcat:10-jdk17-temurin
    container_name: triton-tomcat
    environment:
      - JAVA_OPTS=-Xms256m -Xmx512m
    volumes:
      - ./tomcat/target/triton.war:/usr/local/tomcat/webapps/triton.war:ro
    ports:
      - "8080:8080"   # reverse proxy later if desired
    depends_on:
      - triton-hsqldb
    restart: unless-stopped

  triton-hsqldb:
    image: alpine:3.20
    container_name: triton-hsqldb
    command: ["sh", "-c", "apk add --no-cache openjdk17-jre-headless && java -cp /hsqldb/hsqldb.jar org.hsqldb.Server -database.0 file:/data/triton -dbname.0 triton"]
    volumes:
      - ./hsqldb/data:/data
      - ./hsqldb/hsqldb.jar:/hsqldb/hsqldb.jar:ro
      - ./hsqldb/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    expose:
      - "9001"
    restart: unless-stopped
```

> **Note:** For simplicity we run HSQLDB in Server mode on 9001. The webapp connects via JDBC: `jdbc:hsqldb:hsql://triton-hsqldb:9001/triton`.

---

## 7) Raspberry Pi Controller (Python outline)

**Hardware**

- Pi GPIO to a relay module or MOSFET driver controlling the solenoid’s valve power.
- External power supply sized for the valve; Pi **does not** power the valve directly.
- Flyback protection for inductive loads.

**Software (first pass)**

- `triton.py` loop:
  1. Load `config.yaml` (device_id, token, api_url, poll_interval, gpio pin, timezone).
  2. POST `checkin` hourly (or configured interval).
  3. Apply directive: if `manual_run` present → run for N minutes; else evaluate local clock vs `schedules` and `hold_until`.
  4. Toggle GPIO accordingly; log events.
  5. Sleep until next poll or next schedule boundary (whichever comes first).

**Example `config.yaml`**

```yaml
device_id: pi-garden-01
device_token: "REDACTED"
api_url: "http://<server>:8080/triton/api/v1"
poll_interval_minutes: 60
gpio_pin: 18
relay_active_high: false
timezone: "America/Chicago"
```

---

## 8) Security (MVP → v1)

- **Transport**: Terminate TLS (HTTPS) at the server; Pi trusts server CA (pin if desired).
- **Auth**: Per‑device bearer token. Rotate via UI; store salted hash server‑side.
- **RBAC**: Single admin user for MVP; add roles later.
- **Audit**: All actions → `events` table; include IP/device and user id for overrides.
- **Safety**: Server returns **max_run_minutes** to cap any manual run; Pi enforces a **watchdog cutoff**.

---

## 9) Operational Considerations

- **Timezone & DST**: Store times in UTC; convert to local for display/execution using configured TZ.
- **Idempotency**: On reconnect, Pi queries current directive before toggling.
- **Offline behavior**: If server unreachable, Pi follows last known schedule (with a max staleness window, e.g., 24h) and disables watering if weather hold was active and stale.
- **Health**: Heartbeat on check‑in; UI shows last seen.
- **Backups**: Snapshot HSQLDB files nightly; retain 7–14 days.

---

## 10) Build & Run (MVP skeleton)

**Cloud**

1. Build Java webapp → `triton.war` (Maven) and place per compose mapping.
2. Download `hsqldb.jar` into `cloud/hsqldb/`.
3. `docker compose up -d` inside `cloud/`.
4. Access UI at `http://<host>:8080/triton/`.

**Edge**

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python triton.py`

---

## 11) Future Enhancements

- Multi‑zone support (N relays) and per‑zone schedules.
- Soil moisture sensor feedback; adaptive watering.
- Push (WebSocket/MQTT) to reduce poll latency.
- Mobile PWA for offline control.
- OAuth2 user auth, device provisioning workflow, and per‑device ACLs.
- Calendar‑style schedule editor or RRULE support.

---

## 12) Open Questions / Assumptions

- Weather provider preference & thresholds?
- Manual override UX: slider vs presets?
- Do we need sunrise/sunset scheduling (astronomical times) in v1?
- Any power constraints at the valve location (long runs, voltage drop)?

---

## 13) Minimal Acceptance Criteria (MVP)

- Create/edit a daily schedule in the web UI.
- Pi checks in and receives schedule; runs the solenoid accordingly.
- Server applies a rain hold (simulated or real weather) that prevents watering.
- Manual RUN NOW for N minutes works, with safety max and audit entry.

---

**This document is the working spec + README.** As we implement, we’ll keep schema, endpoints, and compose in lock‑step.
