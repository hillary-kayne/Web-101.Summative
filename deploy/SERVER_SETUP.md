# ReThread — server setup guide

This reflects what was actually deployed and verified working: **http://32.192.238.247/**
(round-robin across web-01 and web-02, both backed by the same Supabase Postgres instance).
Kept here as the reproducible record of every step, in case the servers need to be rebuilt.

## Assumed roles

Three servers, three jobs. Swap the IPs below if this mapping is wrong:

| Role | Public IP | Private IP | Job |
|---|---|---|---|
| **web-01** | `52.207.253.107` | `10.227.50.192` | App server #1 (gunicorn, port 8000) |
| **web-02** | `100.53.143.147` | `10.227.102.34` | App server #2 (gunicorn, port 8000) |
| **lb-01**  | `32.192.238.247` | `10.227.41.131` | Load balancer (HAProxy), round-robin across web-01/web-02 |

Database lives outside all three — a managed Supabase Postgres instance (see step 2).

Set these once so you can copy-paste the rest of this file as-is:

```bash
KEY=~/.ssh/school
WEB01=52.207.253.107
WEB02=100.53.143.147
LB01=32.192.238.247
```

---

## 1. Copy the project onto web-01 and web-02

From the machine with a working key for the servers, run from the repo root:

```bash
tar czf /tmp/rethread.tar.gz --exclude='backend/venv' --exclude='backend/.env' backend frontend deploy
for host in $WEB01 $WEB02; do
  ssh -i "$KEY" ubuntu@$host "sudo mkdir -p /opt/rethread && sudo chown ubuntu:ubuntu /opt/rethread"
  scp -i "$KEY" /tmp/rethread.tar.gz ubuntu@$host:/tmp/
  ssh -i "$KEY" ubuntu@$host "tar xzf /tmp/rethread.tar.gz -C /opt/rethread && rm /tmp/rethread.tar.gz"
done
```

---

## 2. Database: Supabase, not self-hosted

Originally planned to run Postgres on web-01 itself. Changed to a managed
[Supabase](https://supabase.com/) Postgres instance instead — it was already provisioned and
tested working before the server deployment started, so standing up and hardening a second
piece of self-hosted infrastructure (plus wiring `pg_hba.conf` to trust web-01/web-02's private
IPs) would have added setup time and risk without the assignment requiring self-hosted Postgres
specifically. Supabase's pooler connection already requires TLS (`sslmode=require`) and
authenticates every connection, so there's no open port 5432 to firewall on either app server.

Nothing to do on the servers for this step — both web-01 and web-02 just get the same
`DATABASE_URL` in their `.env` in step 3.

---

## 3. Set up the app on web-01 AND web-02 (repeat for both)

```bash
ssh -i "$KEY" ubuntu@$WEB01   # then repeat this whole section for $WEB02
```

On the server:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip

cd /opt/rethread/backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp ../.env.example .env
nano .env
```

Fill in `.env` with:
- `GEOAPIFY_API_KEY` — your real Geoapify key (locator search returns a clean error without one;
  everything else still works)
- `DATABASE_URL=postgresql://<user>:<pass>@<supabase-pooler-host>:5432/postgres?sslmode=require`
  — the **exact same value on both web-01 and web-02**, copied from the Supabase project's
  "Session pooler" connection string
- `SESSION_SECRET` — **the exact same long random string on both servers** (JWTs signed on
  one must validate on the other); generate one with `openssl rand -hex 32`

Save and exit `nano` (Ctrl+O, Enter, Ctrl+X), then:

```bash
sudo cp ../deploy/rethread.service /etc/systemd/system/rethread.service
sudo systemctl daemon-reload
sudo systemctl enable --now rethread
sudo systemctl status rethread
```

You should see `active (running)`. Then:

```bash
exit
```

Repeat this entire section 3 for the other app server before moving on.

---

## 4. Set up the load balancer on lb-01

```bash
ssh -i "$KEY" ubuntu@$LB01
```

On lb-01:

```bash
sudo apt update && sudo apt install -y haproxy
sudo nano /etc/haproxy/haproxy.cfg
```

Paste in the contents of `deploy/haproxy.cfg` from the project — it already has web-01/web-02's
**private** IPs filled in:

```
    server web-01 10.227.50.192:8000 check inter 5s fall 3 rise 2
    server web-02 10.227.102.34:8000 check inter 5s fall 3 rise 2
```

Then:

```bash
sudo systemctl restart haproxy
sudo systemctl enable haproxy
exit
```

---

## 5. Verify from your machine

```bash
curl -s http://$LB01/healthz
```

Should return `{"status": "ok"}`. Open `http://$LB01/` in a browser — that's the live app.

To confirm both servers are actually taking traffic, open `http://<LB01>:8404/stats` in a
browser (HAProxy's built-in stats page) and watch the session counts for `web-01` and
`web-02` climb together while you refresh the app a few times.

---

## Firewall / security group checklist

- Port **80** on lb-01 — open to the internet. ✅
- Port **22** on all three — open (already working). ✅
- Port **8000** on web-01 — restricted to lb-01's private IP only via `ufw`:
  `sudo ufw allow from 10.227.41.131 to any port 8000 proto tcp`. ✅
- Port **8000** on web-02 — **not restricted**. This image didn't have `ufw` installed, and
  installing + enabling a firewall for the first time over SSH (with no console fallback) risks
  locking out the only access path if the rule order is wrong. Given the deadline, left open
  rather than risk that. To fix later, in this exact order (allow SSH *before* enabling):
  ```bash
  sudo apt install -y ufw
  sudo ufw allow 22/tcp
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw allow from 10.227.41.131 to any port 8000 proto tcp
  sudo ufw --force enable
  ```
- Port **5432** — not applicable; the database is Supabase, reached over TLS, not exposed by
  either app server.
- Port **8404** on lb-01 (HAProxy stats) — left open for verification (`/stats` page); worth
  restricting or removing before any long-term use.
