# StreamSocial Architecture Diagram

## System Architecture Overview

```mermaid
graph TB
    subgraph Frontend["🌐 Frontend Layer"]
        React["React App<br/>(App.js)"]
    end
    
    subgraph BackendLayer["🔧 Backend API Layer"]
        FastAPI["FastAPI Server<br/>(main.py)<br/>Port 8000"]
        Producer["Event Producer<br/>(event_producer.py)"]
        Consumer["Event Consumer<br/>(event_consumer.py)<br/>Background Thread"]
    end
    
    subgraph EventModels["📊 Event & Config Layer"]
        Events["Event Models<br/>(events.py)<br/>31 Event Types"]
        TopicConfig["Topic Config<br/>(topic_config.py)<br/>3 Topics"]
        PartitionStrat["Partition Strategy<br/>(partition_strategy.py)<br/>Hash-based"]
    end
    
    subgraph KafkaCluster["🎯 Kafka Cluster"]
        Broker1["Kafka Broker 1<br/>:9092"]
        Broker2["Kafka Broker 2<br/>:9093"]
        Broker3["Kafka Broker 3<br/>:9094"]
        
        subgraph Topics["Kafka Topics (Replication: 3x)"]
            UserActions["user-actions<br/>1000 partitions<br/>Partitioned by: user_id<br/>7-day retention"]
            ContentInt["content-interactions<br/>500 partitions<br/>Partitioned by: content_id<br/>1-day retention"]
            SystemEvt["system-events<br/>100 partitions<br/>Partitioned by: system_id<br/>3-day retention"]
        end
    end
    
    subgraph EventTypes["📋 Event Type Routing"]
        UserActionsEvts["User Actions:<br/>• Registration, Login, Logout<br/>• Post Create/Edit/Delete<br/>• Comment Create/Delete<br/>• Follow/Unfollow"]
        ContentEvts["Content Interactions:<br/>• Like, Unlike<br/>• Comment, Share<br/>• View, Bookmark<br/>• Analytics"]
        SystemEvts["System Events:<br/>• Notifications<br/>• Alerts, Errors<br/>• Health Checks"]
    end
    
    %% Frontend to Backend
    React -->|HTTP GET /events/recent| FastAPI
    React -->|HTTP POST /register| FastAPI
    React -->|HTTP POST /cluster/simulate_failure| FastAPI
    
    %% Backend components
    FastAPI -->|Creates & Uses| Producer
    FastAPI -->|Starts in Background| Consumer
    
    %% Configuration
    Producer -->|Uses| TopicConfig
    Producer -->|Uses| PartitionStrat
    Consumer -->|Uses| TopicConfig
    Events -->|Defines| UserActionsEvts
    Events -->|Defines| ContentEvts
    Events -->|Defines| SystemEvts
    
    %% Producer to Kafka
    Producer -->|Routes Events| Topics
    UserActionsEvts -->|Goes to| UserActions
    ContentEvts -->|Goes to| ContentInt
    SystemEvts -->|Goes to| SystemEvt
    
    %% Topics to Brokers
    UserActions -.->|Replicated Across| Broker1
    UserActions -.->|Replicated Across| Broker2
    UserActions -.->|Replicated Across| Broker3
    ContentInt -.->|Replicated Across| Broker1
    ContentInt -.->|Replicated Across| Broker2
    ContentInt -.->|Replicated Across| Broker3
    SystemEvt -.->|Replicated Across| Broker1
    SystemEvt -.->|Replicated Across| Broker2
    SystemEvt -.->|Replicated Across| Broker3
    
    %% Consumer from Kafka
    Consumer -->|Subscribes to All Topics| Topics
    
    style Frontend fill:#e1f5ff
    style BackendLayer fill:#fff3e0
    style EventModels fill:#f3e5f5
    style KafkaCluster fill:#e8f5e9
    style Topics fill:#c8e6c9
    style EventTypes fill:#fce4ec
```

## Data Flow Diagram

```mermaid
graph LR
    User["👤 User Action"]
    
    subgraph HTTPFlow["HTTP Request Flow"]
        FE["Frontend<br/>sends HTTP"]
        API["FastAPI Endpoint<br/>receives request"]
        Validate["Validate & Create<br/>StreamSocialEvent"]
        Route["Route to Topic<br/>based on EventType"]
    end
    
    subgraph ProducerFlow["Producer Flow"]
        Extract["Extract Partition Key<br/>user_id/content_id/system_id"]
        Hash["Hash Key<br/>consistent hashing"]
        Calc["Calculate Partition<br/>hash % num_partitions"]
        Send["Send to Kafka<br/>with acks='all'"]
    end
    
    subgraph ConsumerFlow["Consumer Flow"]
        Sub["Consumer Subscribes<br/>to 3 Topics"]
        Listen["Listen for Events<br/>in Background Thread"]
        Process["Process Events<br/>by Registered Handlers"]
        Store["Store in<br/>processed_events"]
    end
    
    User -->|1. User clicks/submits| FE
    FE -->|2. POST/GET| API
    API -->|3. Parse Request| Validate
    Validate -->|4. Determine Topic| Route
    Route -->|5. User Action Events| Extract
    Extract -->|6. e.g., 'user_123'| Hash
    Hash -->|7. compute hash| Calc
    Calc -->|8. hash % 1000| Send
    Send -->|9. To Broker| Sub
    Sub -->|10. Messages arrive| Listen
    Listen -->|11. Deserialize JSON| Process
    Process -->|12. Call handlers| Store
    
    style HTTPFlow fill:#fff9c4
    style ProducerFlow fill:#c8e6c9
    style ConsumerFlow fill:#bbdefb
```

## Topic Partitioning Strategy

```mermaid
graph TB
    subgraph Strategy["Partition Calculation"]
        Input["Event with key<br/>e.g., user_id='alice'"]
        Hash["MD5 Hash<br/>hash('alice')"]
        Mod["Modulo Operation<br/>hash_value % 1000"]
        Result["Partition #<br/>0-999"]
    end
    
    subgraph Distribution["User Actions Topic<br/>1000 Partitions"]
        P1["P0"]
        P2["P1"]
        P3["P2"]
        PX["..."]
        P999["P999"]
    end
    
    Input -->|Key: 'alice'| Hash
    Hash -->|0x3d7f...| Mod
    Mod -->|0x3d7f... % 1000 = 456| Result
    Result -->|Message to| P3
    
    P1 -.->|Each partition| Broker1
    P2 -.->|replicated to| Broker2
    P3 -.->|all 3 brokers| Broker3
    
    style Strategy fill:#e0f2f1
    style Distribution fill:#b2dfdb
```

## Component Interactions

```mermaid
sequenceDiagram
    participant React
    participant FastAPI
    participant Producer
    participant Consumer
    participant Kafka
    
    React->>FastAPI: 1. POST /register
    Note over FastAPI: Create UserRegistration
    
    FastAPI->>Producer: 2. ensure_topics_exist()
    Producer->>Kafka: 3. Create topics with admin client
    
    FastAPI->>Producer: 4. send_event(StreamSocialEvent)
    Note over Producer: Route to user-actions topic
    Producer->>Kafka: 5. KafkaProducer.send() with partition key
    
    Note over Kafka: Message stored in partition<br/>acks='all' = all replicas
    Kafka->>Producer: 6. Future.get() success
    
    FastAPI->>Consumer: 7. Running in background (thread)
    Consumer->>Kafka: 8. KafkaConsumer.poll() from 3 topics
    
    Kafka->>Consumer: 9. Return batch of messages
    Note over Consumer: Deserialize JSON<br/>Call registered handlers<br/>Store in processed_events
    
    FastAPI->>React: 10. GET /events/recent
    React->>React: 11. Filter & display stats
```

## Configuration & Event Routing

```mermaid
graph TB
    subgraph Events31["31 Event Types Defined"]
        UA["USER ACTIONS<br/>USER_REGISTRATION<br/>USER_LOGIN<br/>USER_LOGOUT<br/>USER_PROFILE_UPDATE<br/>USER_FOLLOW<br/>USER_UNFOLLOW<br/>USER_POST_CREATE<br/>USER_POST_DELETE<br/>USER_POST_EDIT<br/>USER_COMMENT_CREATE<br/>USER_COMMENT_DELETE"]
        
        CI["CONTENT INTERACTIONS<br/>CONTENT_LIKE<br/>CONTENT_UNLIKE<br/>CONTENT_COMMENT<br/>CONTENT_SHARE<br/>CONTENT_VIEW<br/>CONTENT_BOOKMARK<br/>CONTENT_ANALYTICS"]
        
        SE["SYSTEM EVENTS<br/>SYSTEM_NOTIFICATION<br/>SYSTEM_ALERT<br/>SYSTEM_ERROR<br/>SYSTEM_HEALTH_CHECK"]
    end
    
    UA -->|Route to| T1["user-actions topic"]
    CI -->|Route to| T2["content-interactions topic"]
    SE -->|Route to| T3["system-events topic"]
    
    T1 -->|Config| C1["1000 partitions<br/>Key: user_id<br/>7-day retention<br/>gzip compression"]
    T2 -->|Config| C2["500 partitions<br/>Key: content_id<br/>1-day retention<br/>gzip compression"]
    T3 -->|Config| C3["100 partitions<br/>Key: system_id<br/>3-day retention<br/>gzip compression"]
    
    style Events31 fill:#fce4ec
    style T1 fill:#c8e6c9
    style T2 fill:#c8e6c9
    style T3 fill:#c8e6c9
```

## Broker Cluster Replication

```mermaid
graph TB
    subgraph Cluster["Kafka Cluster - Replication Factor 3"]
        B1["Broker 1<br/>localhost:9092"]
        B2["Broker 2<br/>localhost:9093"]
        B3["Broker 3<br/>localhost:9094"]
    end
    
    subgraph Partitions["Each Topic"]
        P0["Partition 0"]
        P1["Partition 1"]
        Pn["Partition N"]
    end
    
    P0 -->|Leader| B1
    P0 -->|Replica| B2
    P0 -->|Replica| B3
    
    P1 -->|Replica| B1
    P1 -->|Leader| B2
    P1 -->|Replica| B3
    
    Pn -->|Replica| B1
    Pn -->|Replica| B2
    Pn -->|Leader| B3
    
    Note over Cluster: Each partition has 1 leader + 2 replicas<br/>Producer sends to leader<br/>Leader replicates to followers<br/>acks='all' waits for all replicas
    
    style Cluster fill:#e8f5e9
    style Partitions fill:#c8e6c9
```

---

## Key Concepts

### Producer Flow
1. **Receive Event**: FastAPI endpoint receives HTTP request
2. **Create Event Object**: Instantiate `StreamSocialEvent` with event type
3. **Route to Topic**: Event type determines target topic (user-actions, content-interactions, system-events)
4. **Extract Partition Key**: Get `user_id`, `content_id`, or `system_id` from event
5. **Calculate Partition**: Hash the key and mod by partition count
6. **Send to Broker**: KafkaProducer sends with `acks='all'` (waits for all replicas)

### Consumer Flow
1. **Subscribe**: Consumer subscribes to all 3 topics
2. **Poll**: Background thread continuously polls for new messages
3. **Deserialize**: JSON messages converted to Python dicts
4. **Handle**: Call registered handler functions
5. **Store**: Add to `processed_events` list for API queries

### Topic Strategy
- **user-actions** (1000 partitions): High-volume user events, ordered by user
- **content-interactions** (500 partitions): Ultra-high-volume content events, ordered by content
- **system-events** (100 partitions): Low-volume system notifications

### Replication
- **Factor**: 3 (each message replicated across all 3 brokers)
- **Durability**: `acks='all'` ensures all replicas acknowledge before success
- **Fault Tolerance**: Can lose up to 2 brokers without data loss
