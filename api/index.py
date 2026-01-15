from __future__ import annotations

from datetime import datetime, timezone, timedelta
import random

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="APM Demo API", version="1.0.0")

# Vercel entrypoint: export `app` at module scope.


# Demo-only CORS so the static HTML can call the API from anywhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Simulated JSON "stores"
# (in-memory; frontend stores additions in localStorage)
# -----------------------------
BASE_SERVICES = [
    {
        "id": "svc-auth",
        "name": "auth-service",
        "type": "app",
        "env": "prod",
        "owner": "identity",
        "targets": {"target_latency_ms": 220, "target_error_rate": 0.8},
    },
    {
        "id": "svc-orders",
        "name": "orders-api",
        "type": "app",
        "env": "prod",
        "owner": "commerce",
        "targets": {"target_latency_ms": 300, "target_error_rate": 1.0},
    },
    {
        "id": "svc-postgres",
        "name": "postgres-primary",
        "type": "db",
        "env": "prod",
        "owner": "platform",
        "targets": {"target_latency_ms": 80, "target_error_rate": 0.2},
    },
    {
        "id": "svc-redis",
        "name": "redis-cache",
        "type": "cache",
        "env": "prod",
        "owner": "platform",
        "targets": {"target_latency_ms": 25, "target_error_rate": 0.1},
    },
    {
        "id": "svc-gateway",
        "name": "edge-gateway",
        "type": "gateway",
        "env": "prod",
        "owner": "network",
        "targets": {"target_latency_ms": 150, "target_error_rate": 0.5},
    },
]

SECURITY_EVENTS = [
    {"id": "evt-1", "severity": "high", "title": "Suspicious login burst", "detail": "Multiple failed logins from new ASN"},
    {"id": "evt-2", "severity": "medium", "title": "WAF rule triggered", "detail": "Possible SQLi pattern blocked"},
    {"id": "evt-3", "severity": "critical", "title": "Privilege escalation attempt", "detail": "Admin endpoint access anomaly"},
    {"id": "evt-4", "severity": "info", "title": "Key rotation reminder", "detail": "KMS key rotation due in 7 days"},
]


# -----------------------------
# Models
# -----------------------------
class ServicesResponse(BaseModel):
    ts: str
    services: list[dict]


class ServiceMetrics(BaseModel):
    ts: str
    latency_ms: float
    error_rate: float
    rps: float
    status: str


# -----------------------------
# Helpers
# -----------------------------
def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pick_status(score: float) -> str:
    # score in [0..1+] where higher is worse
    if score > 0.85:
        return "down"
    if score > 0.55:
        return "warn"
    return "ok"


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def stable_seed(service_id: str) -> int:
    # keeps each service "personality" stable across refreshes
    return abs(hash(service_id)) % (2**31 - 1)


def simulate_service_metrics(service_id: str) -> dict:
    # Stable base + time drift for demo (new value every 5 seconds)
    rng = random.Random(stable_seed(service_id) + int(datetime.now(timezone.utc).timestamp() // 5))
    base_latency = rng.uniform(20, 260)
    base_error = rng.uniform(0.0, 2.5)
    base_rps = rng.uniform(5, 250)

    # occasional spikes
    if rng.random() < 0.08:
        base_latency *= rng.uniform(2.0, 4.0)
        base_error *= rng.uniform(2.0, 6.0)

    latency = clamp(base_latency, 5, 2000)
    error = clamp(base_error, 0.0, 25.0)
    rps = clamp(base_rps, 0.1, 2000)

    # status heuristic
    score = clamp((latency / 900.0) * 0.6 + (error / 10.0) * 0.4, 0.0, 1.2)
    status = pick_status(score)

    return {
        "ts": iso_now(),
        "latency_ms": float(latency),
        "error_rate": float(error),
        "rps": float(rps),
        "status": status,
    }


def simulate_system() -> dict:
    rng = random.Random(int(datetime.now(timezone.utc).timestamp() // 3))
    cpu = clamp(rng.uniform(18, 92) + (10 if rng.random() < 0.12 else 0), 1, 100)
    mem = clamp(rng.uniform(30, 88), 1, 100)
    disk = clamp(rng.uniform(40, 93), 1, 100)
    uptime_hours = int(rng.uniform(12, 240))
    status = "ok"
    if cpu > 90 or mem > 90 or disk > 92:
        status = "warn"
    if cpu > 96 or mem > 96:
        status = "down"
    return {
        "ts": iso_now(),
        "cpu_percent": cpu,
        "mem_percent": mem,
        "disk_percent": disk,
        "uptime_human": f"{uptime_hours}h",
        "status": status,
    }


def simulate_app() -> dict:
    rng = random.Random(int(datetime.now(timezone.utc).timestamp() // 3) + 991)
    p95 = clamp(rng.uniform(90, 850) * (3.2 if rng.random() < 0.06 else 1.0), 10, 3000)
    rps = clamp(rng.uniform(20, 520), 1, 5000)
    err = clamp(rng.uniform(0.05, 3.5) * (4.0 if rng.random() < 0.05 else 1.0), 0, 30)
    status = "ok"
    if p95 > 900 or err > 3.5:
        status = "warn"
    if p95 > 1400 or err > 8:
        status = "down"
    return {
        "ts": iso_now(),
        "p95_latency_ms": p95,
        "rps": rps,
        "error_rate_percent": err,
        "version": f"v1.{rng.randint(2,9)}.{rng.randint(0,30)}",
        "status": status,
    }


def simulate_network() -> dict:
    rng = random.Random(int(datetime.now(timezone.utc).timestamp() // 3) + 42)
    rtt = clamp(rng.uniform(12, 180) * (3.0 if rng.random() < 0.05 else 1.0), 1, 2000)
    loss = clamp(rng.uniform(0.0, 1.2) * (5.0 if rng.random() < 0.03 else 1.0), 0, 30)
    dns = clamp(rng.uniform(8, 90) * (2.6 if rng.random() < 0.05 else 1.0), 1, 1200)
    status = "ok"
    if rtt > 220 or loss > 1.5 or dns > 140:
        status = "warn"
    if rtt > 480 or loss > 5.0:
        status = "down"
    return {
        "ts": iso_now(),
        "rtt_ms": rtt,
        "packet_loss_percent": loss,
        "dns_ms": dns,
        "status": status,
    }


def simulate_cloud() -> dict:
    rng = random.Random(int(datetime.now(timezone.utc).timestamp() // 5) + 777)
    total = rng.randint(6, 14)
    unhealthy = 0
    for _ in range(total):
        if rng.random() < 0.12:
            unhealthy += 1
    healthy = total - unhealthy
    cost = clamp(rng.uniform(120, 680) + unhealthy * rng.uniform(10, 40), 20, 5000)
    incidents = unhealthy + (1 if rng.random() < 0.08 else 0)

    status = "ok"
    if unhealthy >= 1 or incidents >= 1:
        status = "warn"
    if unhealthy >= 3 or incidents >= 4:
        status = "down"

    return {
        "ts": iso_now(),
        "total_count": total,
        "healthy_count": healthy,
        "estimated_cost_per_day_usd": cost,
        "open_incidents": incidents,
        "status": status,
    }


def simulate_security() -> dict:
    rng = random.Random(int(datetime.now(timezone.utc).timestamp() // 7) + 2024)
    # emit 2-5 events, random selection
    count = rng.randint(2, 5)
    chosen = rng.sample(SECURITY_EVENTS, k=count)

    # stamp timestamps near now
    out = []
    for ev in chosen:
        minutes_ago = rng.randint(0, 90)
        ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
        out.append({**ev, "ts": ts, "source": "backend"})

    # status derived from highest severity
    sev_rank = {"info": 0, "medium": 1, "high": 2, "critical": 3}
    max_rank = max(sev_rank.get(e["severity"], 0) for e in out)
    status = "ok"
    if max_rank >= 1:
        status = "warn"
    if max_rank >= 3:
        status = "down"

    return {"ts": iso_now(), "status": status, "events": out}


# -----------------------------
# API endpoints (unique handlers per domain)
# -----------------------------
@app.get("/api/system")
def get_system_status():
    return simulate_system()


@app.get("/api/app")
def get_app_status():
    return simulate_app()


@app.get("/api/network")
def get_network_status():
    return simulate_network()


@app.get("/api/cloud")
def get_cloud_status():
    return simulate_cloud()


@app.get("/api/security")
def get_security_events():
    return simulate_security()


@app.get("/api/services", response_model=ServicesResponse)
def list_services():
    return {"ts": iso_now(), "services": BASE_SERVICES}


@app.get("/api/services/{service_id}/metrics", response_model=ServiceMetrics)
def get_service_metrics(service_id: str):
    # Works for base services AND any local ids from the frontend
    return simulate_service_metrics(service_id)
