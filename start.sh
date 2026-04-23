#!/bin/bash
# =============================================================================
# start.sh — Entrypoint for the kafka-spring Docker container.
# Starts Apache Kafka (KRaft mode) first, waits until it's healthy, then
# launches the Spring Boot application in the foreground.
# =============================================================================
set -e

echo "==================================================================="
echo "  Apache Kafka (KRaft) + Spring Boot — Single Container Startup"
echo "==================================================================="

# ── Kafka JVM heap (keep modest so both processes fit in the container) ──────
export KAFKA_HEAP_OPTS="-Xmx512m -Xms256m"

# ── 1. Generate a fresh cluster UUID for KRaft ───────────────────────────────
echo "[1/5] Generating Kafka cluster ID..."
KAFKA_CLUSTER_ID="$(/opt/kafka/bin/kafka-storage.sh random-uuid)"
echo "      Cluster ID: ${KAFKA_CLUSTER_ID}"

# ── 2. Format the KRaft log directory ────────────────────────────────────────
echo "[2/5] Formatting KRaft storage..."
/opt/kafka/bin/kafka-storage.sh format \
    --config /opt/kafka/config/kraft/server.properties \
    --cluster-id "${KAFKA_CLUSTER_ID}" \
    --ignore-formatted

# ── 3. Start the Kafka broker in the background ──────────────────────────────
echo "[3/5] Starting Kafka broker..."
/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/kraft/server.properties &
KAFKA_PID=$!

# ── 4. Wait until the broker is accepting connections ────────────────────────
echo "[4/5] Waiting for Kafka to be ready..."
MAX_RETRIES=30
RETRY=0
until nc -z localhost 9092 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ "${RETRY}" -ge "${MAX_RETRIES}" ]; then
        echo "ERROR: Kafka did not become ready after $((MAX_RETRIES * 2)) seconds."
        kill "${KAFKA_PID}" 2>/dev/null
        exit 1
    fi
    echo "      Not ready yet... (${RETRY}/${MAX_RETRIES})"
    sleep 2
done
echo "      Kafka is ready!"

# ── Create the default topic ─────────────────────────────────────────────────
TOPIC_NAME="${KAFKA_TOPIC_NAME:-messages}"
/opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --if-not-exists \
    --topic "${TOPIC_NAME}" \
    --partitions 3 \
    --replication-factor 1 \
    && echo "      Topic '${TOPIC_NAME}' ready." \
    || echo "      Topic '${TOPIC_NAME}' already exists or creation failed (non-fatal)."

# ── Graceful shutdown: stop Kafka when the script exits ──────────────────────
cleanup() {
    echo ""
    echo "Shutting down Kafka (PID ${KAFKA_PID})..."
    kill "${KAFKA_PID}" 2>/dev/null
    wait "${KAFKA_PID}" 2>/dev/null
    echo "Kafka stopped. Bye!"
}
trap cleanup EXIT

# ── 5. Start the Spring Boot application (foreground, becomes PID 1 child) ───
echo "[5/5] Starting Spring Boot application..."
echo "==================================================================="
exec java \
    -Xmx512m -Xms256m \
    -jar /app/app.jar
