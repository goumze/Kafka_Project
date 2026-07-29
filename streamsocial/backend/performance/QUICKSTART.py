#!/usr/bin/env python3
"""
STREAMSOCIAL KAFKA - SIMPLIFIED QUICK START
============================================

Everything is now in ONE shell script: performance/run.sh

No more managing multiple Python scripts - just use ./run.sh

INSTALLATION (30 seconds)
=========================

cd streamsocial/backend/performance
chmod +x run.sh
./run.sh --setup

SIMPLEST WORKFLOW (Copy & Paste)
================================

# Terminal 1: Start Kafka
cd streamsocial/backend/performance
./run.sh --kafka

# Terminal 2: Start API
cd streamsocial/backend/performance
./run.sh --api

# Terminal 3: Monitor Lag
cd streamsocial/backend/performance
./run.sh --monitor

# Terminal 4: Generate Events
cd streamsocial/backend/performance
./run.sh --generate 5000 60

SCALING DEMO
============

# After events have been generating for 30 seconds, add consumers:

# Terminal 5: Start first consumer
./run.sh --consumers 1

# Wait 30 seconds, then add more (automatic rebalancing)
./run.sh --consumers 2

# Add more
./run.sh --consumers 3

Watch Terminal 3 (monitor) - lag should decrease as you scale up!

ALL COMMANDS (Type these in performance directory)
==================================================

# Help & Setup
./run.sh --help              Show all commands
./run.sh --setup             Check dependencies

# Services
./run.sh --kafka             Start Kafka cluster
./run.sh --stop-kafka        Stop Kafka
./run.sh --api               Start API server
./run.sh --api-logs          Show API logs

# Data & Monitoring
./run.sh --generate 5000 60  Generate 5000 events/sec for 60 seconds
./run.sh --monitor           Monitor lag (updates every 5 seconds)
./run.sh --monitor 2         Monitor with 2-second refresh

# Consumers
./run.sh --consumers 3       Start 3 consumer instances
./run.sh --list-consumers    See all instances
./run.sh --stop-consumers 2  Stop 2 instances

# Status
./run.sh --health            Check everything
./run.sh --stats             Consumer statistics
./run.sh --lag               Lag per partition

# Automated Tests
./run.sh --load-test         Full load test
./run.sh --scale-test 5      Scaling test with 5 consumers

# Cleanup
./run.sh --cleanup           Remove everything

BEFORE vs AFTER
===============

OLD WAY (Many scripts):
  # Terminal 1
  docker-compose up -d
  
  # Terminal 2
  python -m uvicorn main:app --host 0.0.0.0 --port 8000
  
  # Terminal 3
  python api_client.py --command generate --rate 5000 --duration 60
  
  # Terminal 4
  python api_client.py --command monitor
  
  # Terminal 5
  python api_client.py --command start-instance --instance consumer-1
  python api_client.py --command start-instance --instance consumer-2

NEW WAY (One script):
  # Terminal 1
  ./run.sh --kafka
  
  # Terminal 2
  ./run.sh --api
  
  # Terminal 3
  ./run.sh --generate 5000 60
  
  # Terminal 4
  ./run.sh --monitor
  
  # Terminal 5
  ./run.sh --consumers 2

WHAT'S DIFFERENT
================

1. Single Entry Point
   OLD: python api_client.py --command ...
   NEW: ./run.sh --command

2. Simpler Syntax
   OLD: python api_client.py --command generate --rate 5000 --duration 60
   NEW: ./run.sh --generate 5000 60

3. Better Feedback
   - Colored output (green, yellow, red)
   - Progress indicators
   - Clear error messages

4. New Convenience Commands
   - ./run.sh --load-test (full automated test)
   - ./run.sh --scale-test 5 (scaling demo)
   - ./run.sh --examples (quick reference)

HOW IT WORKS
============

All the underlying Python code still exists:
  - producers/data_generator.py
  - consumers/event_consumer.py
  - controllers/*.py
  - main.py (API)

The shell script simply calls them with nice formatting and user-friendly commands.

DIRECTORY STRUCTURE
===================

streamsocial/backend/
├── performance/
│   ├── run.sh              ← MAIN SCRIPT (use this!)
│   ├── examples.sh         ← Copy-paste examples
│   ├── setup.sh            ← Setup helper
│   └── README.py           ← Full documentation
│
├── api_client.py           (Called by run.sh)
├── consumer_manager.py     (Called by run.sh)
├── main.py                 (API server)
├── producers/
│   └── data_generator.py   (Called by run.sh)
├── consumers/
│   └── event_consumer.py   (Called by run.sh)
└── ... other files ...

EXAMPLE SCENARIOS
=================

Scenario 1: Quick Test
  $ ./run.sh --kafka
  $ ./run.sh --api &
  $ ./run.sh --generate 1000 60
  $ ./run.sh --stats

Scenario 2: Real-time Monitoring
  # Terminal 1
  $ ./run.sh --monitor
  
  # Terminal 2
  $ ./run.sh --generate 5000 300

Scenario 3: Horizontal Scaling
  # Terminal 1
  $ ./run.sh --monitor
  
  # Terminal 2
  $ ./run.sh --generate 5000 300
  
  # Terminal 3 (after 30 seconds)
  $ ./run.sh --consumers 1
  $ ./run.sh --consumers 2  # after 30 more seconds
  $ ./run.sh --consumers 3  # one more time

Scenario 4: Automated Testing
  $ ./run.sh --load-test      # Full test
  $ ./run.sh --scale-test 5   # Scaling test with 5 consumers

TROUBLESHOOTING
===============

Problem: "Command not found: ./run.sh"
Solution: cd streamsocial/backend/performance

Problem: "Permission denied"
Solution: chmod +x run.sh

Problem: "API server not responding"
Solution: 
  1. Make sure Kafka is running: ./run.sh --health
  2. Start API: ./run.sh --api
  3. Wait a few seconds

Problem: "Docker not found"
Solution: Install Docker and Docker Compose

For detailed help:
  ./run.sh --help

PERFORMANCE DIRECTORY
====================

Location: streamsocial/backend/performance/

This is your command center for:
  ✓ Starting/stopping Kafka
  ✓ Starting/stopping API
  ✓ Generating load
  ✓ Monitoring performance
  ✓ Scaling consumers
  ✓ Running tests

Just use: cd performance && ./run.sh [command]

QUICK REFERENCE CARD
====================

# Start services
./run.sh --kafka              # Terminal 1
./run.sh --api                # Terminal 2

# Test data
./run.sh --generate 1000 60   # 1000 events/sec
./run.sh --generate 5000 60   # 5000 events/sec
./run.sh --generate 10000 60  # 10000 events/sec

# Monitor
./run.sh --monitor            # Real-time view
./run.sh --stats              # Current stats
./run.sh --lag                # Lag metrics

# Scale
./run.sh --consumers 1        # 1 instance
./run.sh --consumers 3        # 3 instances
./run.sh --consumers 5        # 5 instances

# Check
./run.sh --health             # System health
./run.sh --list-consumers     # Show instances

# Tests
./run.sh --load-test          # Auto test
./run.sh --scale-test 3       # Scaling test

# Stop
./run.sh --stop-kafka         # Stop cluster
./run.sh --cleanup            # Clean everything

That's it! You now have everything in one simple shell script.
"""

if __name__ == "__main__":
    print(__doc__)
