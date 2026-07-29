#!/usr/bin/env python3
"""
StreamSocial Performance Testing - Quick Reference

This directory contains a single shell script (run.sh) that handles all
operations for the StreamSocial Kafka system:
  - Kafka cluster management
  - API server startup
  - Bulk event generation
  - Consumer instance scaling
  - Lag monitoring
  - Health checks
  - Performance testing

INSTALLATION
============

1. Make the script executable:
   $ chmod +x run.sh
   
   OR run setup:
   $ bash setup.sh

QUICK START (2 Minutes)
=======================

Terminal 1 - Start Kafka:
  $ ./run.sh --kafka

Terminal 2 - Start API:
  $ ./run.sh --api

Terminal 3 - Generate events:
  $ ./run.sh --generate 5000 60

Terminal 4 - Monitor lag:
  $ ./run.sh --monitor

COMMAND REFERENCE
=================

System Commands:
  ./run.sh --help              Show full help
  ./run.sh --setup             Check dependencies and install
  ./run.sh --health            Check API and consumer health
  ./run.sh --cleanup           Remove all containers

Kafka Commands:
  ./run.sh --kafka             Start Kafka cluster
  ./run.sh --stop-kafka        Stop Kafka cluster

API Commands:
  ./run.sh --api               Start backend API
  ./run.sh --api-logs          Show API logs

Consumer Commands:
  ./run.sh --consumers 3       Start 3 consumer instances
  ./run.sh --stop-consumers 2  Stop 2 consumer instances
  ./run.sh --list-consumers    List all active instances

Data Generation:
  ./run.sh --generate          1000 events/sec for 60 seconds
  ./run.sh --generate 5000 60  5000 events/sec for 60 seconds
  ./run.sh --generate 10000 30 10000 events/sec for 30 seconds

Monitoring & Metrics:
  ./run.sh --monitor           Monitor with 5-second refresh
  ./run.sh --monitor 2         Monitor with 2-second refresh
  ./run.sh --stats             Get consumer statistics
  ./run.sh --stats consumer-1  Get stats for specific consumer
  ./run.sh --lag               Get lag metrics
  ./run.sh --lag consumer-2    Get lag for specific consumer

Automated Tests:
  ./run.sh --load-test         Full load test (generates data, monitors)
  ./run.sh --scale-test 3      Scaling test with 3 consumers

WORKFLOWS
=========

1. BASIC LOAD TEST
   Terminal 1:
   $ ./run.sh --setup
   $ ./run.sh --kafka

   Terminal 2:
   $ ./run.sh --api

   Terminal 3:
   $ ./run.sh --generate 1000 60

   Terminal 4:
   $ ./run.sh --stats

2. REAL-TIME MONITORING
   Terminal 1:
   $ ./run.sh --monitor
   
   Terminal 2:
   $ ./run.sh --generate 5000 120

3. HORIZONTAL SCALING
   Terminal 1:
   $ ./run.sh --monitor

   Terminal 2:
   $ ./run.sh --generate 5000 180
   
   Terminal 3:
   $ ./run.sh --consumers 1
   
   (Wait 30 seconds, observe lag spike then decrease)
   
   $ ./run.sh --consumers 2
   
   (Another rebalance, lag decreases more)
   
   $ ./run.sh --consumers 3

4. AUTOMATED SCALING TEST
   $ ./run.sh --scale-test 5
   
   This automatically:
   - Generates sustained load
   - Starts instances one by one
   - Shows performance improvement

PERFORMANCE TESTING
===================

Example: Test consumer performance with varying load

Test 1 - Low load:
  $ ./run.sh --generate 1000 60
  $ ./run.sh --stats
  
Expected: High throughput, zero lag

Test 2 - Medium load:
  $ ./run.sh --generate 5000 60
  $ ./run.sh --stats
  
Expected: Stable throughput, manageable lag

Test 3 - High load, single consumer:
  $ ./run.sh --generate 10000 60
  $ ./run.sh --stats
  
Expected: Lag increases, consumer falls behind

Test 4 - High load, scaled consumers:
  $ ./run.sh --consumers 4
  $ ./run.sh --generate 10000 60
  $ ./run.sh --stats
  
Expected: Lag drops, better throughput

INTERPRETING OUTPUT
===================

Consumer Statistics:
  Total Events:  How many messages have been processed
  Throughput:    Processing rate (events/second)
  Lag:           Messages not yet processed
  Errors:        Processing failures
  Partitions:    Number of partitions assigned to this consumer

Consumer Lag:
  Total Lag:     Sum of lag across all partitions
  Per-topic:     Lag broken down by topic
  Lag = HighWaterMark - CommittedOffset
  
  Examples:
    Lag = 0:      Consumer caught up (no backlog)
    Lag = 1000:   1000 messages pending
    Growing lag:  Producer faster than consumer
    Shrinking lag: Consumer catching up

TROUBLESHOOTING
===============

Issue: "API server not responding"
Solution: 
  - Make sure Kafka is running: ./run.sh --kafka
  - Start API in its own terminal: ./run.sh --api
  - Check health: ./run.sh --health

Issue: "Kafka cluster failed to start"
Solution:
  - Check Docker is running: docker ps
  - Check logs: docker-compose logs
  - Cleanup and restart: ./run.sh --cleanup && ./run.sh --kafka

Issue: High lag not decreasing
Solution:
  - Add more consumers: ./run.sh --consumers 5
  - Check consumer throughput: ./run.sh --stats
  - Monitor in real-time: ./run.sh --monitor

Issue: Partitions not rebalancing
Solution:
  - Wait 30-60 seconds for rebalancing
  - Verify instances are running: ./run.sh --list-consumers
  - Check health: ./run.sh --health

ENVIRONMENT VARIABLES
====================

Set these before running scripts:

API_URL (default: http://localhost:8000)
  $ export API_URL=http://192.168.1.100:8000
  $ ./run.sh --monitor

KAFKA_BROKERS (default: localhost:9092,localhost:9093,localhost:9094)
  $ export KAFKA_BROKERS=broker1:9092,broker2:9092
  
BACKEND_DIR (default: auto-detected)
  $ export BACKEND_DIR=/path/to/backend

ADVANCED USAGE
==============

1. Run multiple tests sequentially:
   $ ./run.sh --kafka
   $ ./run.sh --api &
   $ ./run.sh --load-test
   $ ./run.sh --scale-test 3

2. Generate data while monitoring:
   Terminal 1: ./run.sh --monitor
   Terminal 2: ./run.sh --generate 5000 300

3. Start consumers programmatically:
   for i in {1..10}; do
     ./run.sh --consumers 1
     sleep 30
   done

4. Log test results:
   ./run.sh --stats > results_before.txt
   ./run.sh --generate 5000 60
   ./run.sh --stats > results_after.txt
   diff results_before.txt results_after.txt

FILE STRUCTURE
==============

/streamsocial/backend/performance/
├── run.sh              Main command script
├── setup.sh            Make run.sh executable
└── README.py           This file

Related files:
├── ../api_client.py    Underlying API client (called by run.sh)
├── ../consumer_manager.py   Consumer instance manager
├── ../producers/data_generator.py   Event generator
└── ../main.py          API server

QUICK COMMANDS CHEATSHEET
=========================

# Setup
./run.sh --setup

# Start services
./run.sh --kafka                    # Terminal 1
./run.sh --api                      # Terminal 2

# Generate load
./run.sh --generate 5000 60         # 5000 events/sec, 60 seconds

# Monitor
./run.sh --monitor                  # Real-time monitoring

# Scale
./run.sh --consumers 3              # Start 3 instances

# Check status
./run.sh --health                   # Health check
./run.sh --stats                    # Consumer statistics
./run.sh --lag                      # Lag metrics
./run.sh --list-consumers           # List instances

# Cleanup
./run.sh --cleanup                  # Remove all

SUPPORT & DOCUMENTATION
=======================

Full documentation:
  See ../USAGE_GUIDE.py for comprehensive guide
  See ../quick_start.py for practical examples

API Endpoints (when running):
  http://localhost:8000/docs        FastAPI documentation
  
Kafka UI:
  http://localhost:8080             Visual Kafka cluster management

For questions:
  - Check the help: ./run.sh --help
  - Review examples: ./run.sh --help | head -50
  - See full guide: cat ../USAGE_GUIDE.py

"""

if __name__ == "__main__":
    print(__doc__)
