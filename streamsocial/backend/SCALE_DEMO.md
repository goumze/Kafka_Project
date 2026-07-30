# StreamSocial Kafka Scale / Lag Demo

## Narrative

1. Start brokers + API + **one** consumer
2. Flood produce (`POST /events/bulk/generate`)
3. Watch **lag rise** via `GET /metrics` and consumer logs (`lag_report`)
4. Scale consumers: `docker compose ... --scale kafka-consumer=3`
5. Watch **lag drain**

## Start

```bash
# from repo root
docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d --build
# optional: start with more consumers
docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d --scale kafka-consumer=1
```

Create the shared network if you start files separately; with both `-f` files together the network is created automatically.

## Produce load

```bash
curl -s -X POST http://localhost:8000/events/bulk/generate \
  -H 'Content-Type: application/json' \
  -d '{"events_per_second":3000,"duration_seconds":45,"background":true}'
```

## Observe lag

```bash
curl -s http://localhost:8000/metrics | jq .
curl -s http://localhost:8000/consumer/lag | jq .
docker compose -f docker-compose.yml -f docker-compose.backend.yml logs -f kafka-consumer
```

Look for log lines: `lag_report ... total_lag=...`

## Scale consumers

```bash
docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d --scale kafka-consumer=3 --no-recreate
# re-check lag
watch -n2 'curl -s http://localhost:8000/metrics/lag | jq .total_lag'
```

## Demo knobs (env)

| Variable | Role |
|----------|------|
| `CONSUMER_PROCESSING_DELAY_MS` | Artificial work per message (default `5`) to induce lag |
| `CONSUMER_GROUP` | Shared group id across replicas |
| `PRODUCER_LINGER_MS` / `PRODUCER_BATCH_SIZE` | Producer throughput |
| `LOADGEN_BURST_SIZE` | Events per loadgen burst before rate pacing |
| `PARTITIONS_*` | Parallelism for scale-out |
| `API_EMBED_CONSUMER` | `true` embeds consumer in API (not for scale demo) |

## Process layout

- `backend-api` — FastAPI + producer + lag metrics API
- `kafka-consumer` — `python -m workers.consumer_worker` (scale this)


## Architecture notes (post layering refactor)

- Controllers are HTTP-only; orchestration lives under `services/` (`LagQueryService`, `LoadGenerationService`, `ClusterOpsService`, `EmbeddedConsumerService`).
- Topic ensure/create is `config/topic_bootstrap.py` (not metrics).
- `POST /consumer/start` is **disabled** for the scale path — use Compose `kafka-consumer` replicas (or `API_EMBED_CONSUMER=true` for local single-process embed at API startup).
- Cluster docker ops (`/cluster/*` failure sim, docker exec) require `CLUSTER_OPS_ENABLED=true` and docker socket; prefer `/metrics` and `/consumer/lag` for lag.
- Broker container allowlist: `BROKER_CONTAINER_NAMES` (default `kafka-broker-1,kafka-broker-2,kafka-broker-3`).


## Lag probe isolation

`GET /metrics` and `GET /consumer/lag` use a **non-member** admin/metadata probe.
They must not join `CONSUMER_GROUP` so polling metrics does not rebalance
`kafka-consumer` replicas.
