# Multi-stage build for Spring Boot Consumer service
# Stage 1: Build
FROM maven:3.9-eclipse-temurin-21 as builder
WORKDIR /build

# Copy pom and source
COPY pom.xml .
COPY src/ src/

# Build with Maven
RUN mvn clean package -DskipTests -q

# Stage 2: Runtime
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Copy JAR from builder
COPY --from=builder /build/target/*.jar app.jar

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# No health check for consumer (runs indefinitely consuming from Kafka)

# Run Spring Boot consumer application
ENTRYPOINT ["java", "-jar", "app.jar"]
