# =============================================================================
# Dockerfile
# Apache Kafka 3.9.0 (KRaft, no ZooKeeper) + Spring Boot — single image
# =============================================================================

# ── Stage 1: Build the Spring Boot application ───────────────────────────────
FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /build

# Download dependencies first (improves layer caching on subsequent builds)
COPY pom.xml .
RUN mvn dependency:go-offline --no-transfer-progress -q

# Build the fat JAR (tests run inside the container via start.sh, skip here)
COPY src ./src
RUN mvn clean package -DskipTests --no-transfer-progress -q

# ── Stage 2: Runtime image ───────────────────────────────────────────────────
FROM amazoncorretto:21

LABEL maintainer="kafka-project" \
      description="Spring Boot + Apache Kafka 3.9.0 (KRaft) in a single plug-and-play container"

WORKDIR /opt

# Install minimal runtime utilities (Amazon Linux 2023 uses dnf)
RUN dnf install -y --setopt=install_weak_deps=False \
        wget \
        nmap-ncat \
        ca-certificates && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# ── Download and install Apache Kafka 3.9.0 (KRaft) ─────────────────────────
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

# ── Copy the Spring Boot fat JAR ─────────────────────────────────────────────
COPY --from=builder /build/target/*.jar /app/app.jar

# ── Copy and prepare the startup script ──────────────────────────────────────
COPY start.sh /start.sh
RUN chmod +x /start.sh

# ── Exposed ports ─────────────────────────────────────────────────────────────
# 8080 → Spring Boot REST API
# 9092 → Kafka broker (PLAINTEXT)
EXPOSE 8080 9092

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD nc -z localhost 9092 && \
        wget -q -O /dev/null http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["/start.sh"]
