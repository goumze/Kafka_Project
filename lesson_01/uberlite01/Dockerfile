# Multi-stage Docker build for Uber-Lite Spring Boot application

# Stage 1: Build with Maven
FROM maven:3.9.6-eclipse-temurin-21 AS builder

WORKDIR /build

# Copy pom.xml and download dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source code and build
COPY src ./src
RUN mvn clean package -DskipTests -B

# Stage 2: Runtime image with Java 21
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

# Copy built JAR from builder stage
COPY --from=builder /build/target/*.jar app.jar

# Create non-root user for security
RUN addgroup -g 1001 appuser && adduser -D -u 1001 appuser -G appuser
USER appuser

# Expose REST API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/api/locations/health || exit 1

# Start Spring Boot application
ENTRYPOINT ["java", "-jar", "app.jar"]
CMD ["--spring.profiles.active=docker"]
