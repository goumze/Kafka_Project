# Multi-stage build for Spring Boot API service
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

# Health check endpoint (Spring Boot Actuator)
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=40s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8000/actuator/health || exit 1

# Run Spring Boot application
ENTRYPOINT ["java", "-jar", "app.jar"]
