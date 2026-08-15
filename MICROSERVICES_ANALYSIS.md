# StreamSocial Microservices Architecture Analysis

## Current State

### ✅ What's Already in Place

```
streamsocial/backend/api/
├── pom.xml                          [PRODUCER POM - API service config]
│
├── producer/
│   ├── Dockerfile                   [Multi-stage Maven build]
│   └── src/main/resources/
│       └── application.yml           [Producer Spring Boot config]
│
└── consumer/
    ├── pom.xml                      [CONSUMER POM - Independent microservice]
    ├── Dockerfile                   [Multi-stage Maven build]
    └── src/main/resources/
        └── application.yml           [Consumer Spring Boot config]
```

### ⚠️ Issues Identified

#### **Issue 1: Producer Missing Its Own pom.xml**
- ❌ `backend/api/producer/pom.xml` does NOT exist
- ✅ `backend/api/pom.xml` exists but is configured for streamsocial-api (shared)
- ✅ `backend/api/consumer/pom.xml` exists with independent configuration

**Impact**: 
- Producer builds using `backend/api/pom.xml` (shared with API logic if any)
- Cannot independently version/configure producer
- Not true microservices separation

---

#### **Issue 2: Docker Build Contexts Mismatch**

**Current docker-compose.yml**:
```yaml
backend-api:
    build:
      context: ./streamsocial/backend/api
      dockerfile: Dockerfile  # ❌ Looking for api/Dockerfile (doesn't exist)
      
kafka-consumer:
    build:
      context: ./streamsocial/backend/consumer  # ❌ Wrong path
      dockerfile: Dockerfile  # ❌ Looking for backend/consumer/Dockerfile (doesn't exist)
```

**Actual File Locations**:
```
api/Dockerfile             ← doesn't exist
api/producer/Dockerfile    ← exists
api/consumer/Dockerfile    ← exists
```

**Fix Needed**:
```yaml
backend-api:                            # Producer service
    build:
      context: ./streamsocial/backend/api/producer
      dockerfile: Dockerfile
      
kafka-consumer:                         # Consumer service
    build:
      context: ./streamsocial/backend/api/consumer
      dockerfile: Dockerfile
```

---

#### **Issue 3: POM.xml Coordination**

**Current pom.xml Structure**:

```
backend/api/pom.xml          ← streamsocial-api (production service)
  Dependencies: web, kafka, actuator, micrometer

backend/api/consumer/pom.xml ← streamsocial-consumer (consumer service)
  Dependencies: base, kafka, actuator, micrometer
```

**Problem**:
- Producer and Consumer are treated as **independent microservices**
- But Producer is configured at the parent `api/` level
- Dockerfiles need to reference their respective pom.xml files

---

## Architecture Recommendation

### **Proposed True Microservices Structure**

```
streamsocial/backend/
├── api/                          ← Producer Microservice
│   ├── pom.xml                  [INDEPENDENT producer pom]
│   ├── Dockerfile               [Build from this pom]
│   └── src/main/
│       ├── java/com/streamsocial/producer/
│       │   ├── StreamSocialProducerApplication.java
│       │   ├── controller/EventController.java
│       │   ├── service/EventProducerService.java
│       │   └── model/Event.java
│       └── resources/
│           └── application.yml
│
└── consumer/                     ← Consumer Microservice (SEPARATE)
    ├── pom.xml                  [INDEPENDENT consumer pom]
    ├── Dockerfile               [Build from this pom]
    └── src/main/
        ├── java/com/streamsocial/consumer/
        │   ├── StreamSocialConsumerApplication.java
        │   ├── service/EventConsumerService.java
        │   ├── handler/EventHandler.java
        │   └── model/Event.java
        └── resources/
            └── application.yml
```

**Benefits**:
✅ True microservices - independent deployment
✅ Separate pom.xml - independent dependencies/versions
✅ Clear build paths in docker-compose
✅ Consumer can scale horizontally independently
✅ Producer can be updated without affecting consumer
✅ Clear separation of concerns

---

## Docker Compose Alignment

### **Current Issue in docker-compose.yml**

```yaml
services:
  backend-api:
    build:
      context: ./streamsocial/backend/api        # ❌ Where's the Dockerfile?
      dockerfile: Dockerfile                      # ❌ Expected: api/Dockerfile
      
  kafka-consumer:
    build:
      context: ./streamsocial/backend/consumer   # ❌ Doesn't exist at backend level
      dockerfile: Dockerfile                      # ❌ Expected: backend/consumer/Dockerfile
```

### **Required Fixes**

**Fix 1**: Update docker-compose context paths

```yaml
services:
  backend-api:
    build:
      context: ./streamsocial/backend/api        # ✅ Points to producer service
      dockerfile: Dockerfile                      # ✅ Should be api/Dockerfile
      
  kafka-consumer:
    build:
      context: ./streamsocial/backend/consumer   # ✅ Points to consumer service
      dockerfile: Dockerfile                      # ✅ Should be backend/consumer/Dockerfile
```

**Fix 2**: Ensure Dockerfile locations match

```
api/Dockerfile                    ← Move producer Dockerfile here
api/pom.xml                       ← Producer pom (independent)

consumer/Dockerfile               ← Already at correct location
consumer/pom.xml                  ← Consumer pom (independent)
```

---

## Dependency Separation

### Producer (API) - Specific Dependencies

```xml
<!-- Only what producer needs -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>  <!-- REST endpoints -->
</dependency>
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>             <!-- Kafka producer -->
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### Consumer - Specific Dependencies

```xml
<!-- Only what consumer needs -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>      <!-- Base app, no web server -->
</dependency>
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>             <!-- Kafka consumer listeners -->
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

---

## Summary of Issues & Fixes

| Issue | Current | Required |
|-------|---------|----------|
| Producer pom.xml | Shared at `api/pom.xml` | Independent `api/pom.xml` |
| Consumer pom.xml | Independent ✅ | Keep independent ✅ |
| Producer Dockerfile | `api/producer/Dockerfile` | Move to `api/Dockerfile` |
| Consumer Dockerfile | `api/consumer/Dockerfile` | Move to `consumer/Dockerfile` |
| docker-compose producer build | `./streamsocial/backend/api` | `./streamsocial/backend/api` |
| docker-compose consumer build | `./streamsocial/backend/consumer` | `./streamsocial/backend/consumer` |
| Folder structure | Nested (producer inside api) | Flat (api & consumer siblings) |

---

## Next Steps

1. **Create `backend/api/pom.xml`** (independent producer config)
2. **Move `backend/api/producer/Dockerfile` → `backend/api/Dockerfile`**
3. **Move `backend/api/consumer/Dockerfile` → `backend/consumer/Dockerfile`**
4. **Update docker-compose.yml** build context paths
5. **Reorganize source code** to match new structure (optional)

