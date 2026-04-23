# =============================================================================
# Dockerfile
# Apache Kafka 3.9.0 (KRaft, no ZooKeeper) + Spring Boot — single image
#
# No Java or Maven required on the host. Everything (JDK 21, Maven, Kafka,
# and the Spring Boot application build) is fully self-contained inside this
# one container image.
# =============================================================================

# ── Single stage: JDK 21 + Maven (host needs nothing installed) ──────────────
FROM maven:3.9-eclipse-temurin-21

LABEL maintainer="kafka-project" \
      description="Spring Boot + Apache Kafka 3.9.0 (KRaft) in a single plug-and-play container"

# Install runtime utilities (Debian-based image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        netcat-openbsd \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ── Download and install Apache Kafka 3.9.0 (KRaft, no ZooKeeper) ───────────
ENV KAFKA_VERSION=3.9.0
ENV SCALA_VERSION=2.13
ENV KAFKA_HOME=/opt/kafka
ENV PATH="${KAFKA_HOME}/bin:${PATH}"

RUN wget -q \
        "https://archive.apache.org/dist/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz" \
        -O /tmp/kafka.tgz && \
    tar -xzf /tmp/kafka.tgz -C /opt && \
    mv "/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}" "${KAFKA_HOME}" && \
    rm /tmp/kafka.tgz

# ── Overlay our KRaft configuration ─────────────────────────────────────────
COPY config/kraft/server.properties ${KAFKA_HOME}/config/kraft/server.properties

# ── Maven build: resolve dependencies then compile the fat JAR ───────────────
WORKDIR /build

COPY pom.xml .
RUN mvn dependency:go-offline --no-transfer-progress -q

COPY src ./src
RUN mvn clean package -DskipTests --no-transfer-progress -q && \
    mkdir -p /app && \
    cp target/*.jar /app/app.jar

# ── Copy and prepare the startup script ──────────────────────────────────────
COPY start.sh /start.sh
RUN chmod +x /start.sh

WORKDIR /opt

# ── Exposed ports ─────────────────────────────────────────────────────────────
# 8080 → Spring Boot REST API
# 9092 → Kafka broker (PLAINTEXT)
EXPOSE 8080 9092

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD nc -z localhost 9092 && \
        wget -q -O /dev/null http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["/start.sh"]
