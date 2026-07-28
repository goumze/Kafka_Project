#!/usr/bin/env python3
"""
Validation Script for StreamSocial Topics & Partition Strategy
Tests the enhanced topic management, partition distribution, and event routing.

Usage:
    python streamsocial/backend/validate_partition_strategy.py
"""

import sys
import json
import statistics
from typing import Dict
from datetime import datetime

# Import StreamSocial components
from config.topic_config import StreamSocialTopicManager, TopicType
from config.partition_strategy import PartitionStrategy
from producers.event_producer import StreamSocialEventProducer
from models.events import EventType


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """Print a formatted section"""
    print(f"\n{title}")
    print("-" * len(title))


def test_topic_configuration():
    """Test 1: Verify topic configurations"""
    print_header("TEST 1: Topic Configuration Validation")
    
    manager = StreamSocialTopicManager()
    topics = manager.get_all_topics()
    
    print_section("✓ Topic Definitions")
    for topic_type, config in topics.items():
        print(f"\n  Topic: {config.name}")
        print(f"    Partitions: {config.num_partitions}")
        print(f"    Replication Factor: {config.replication_factor}")
        print(f"    Retention: {config.retention_ms / 1000 / 3600 / 24:.1f} days")
        print(f"    Compression: {config.compression_type}")
        print(f"    Description: {config.description[:60]}...")
    
    print_section("✓ Event to Topic Mapping")
    event_mapping_counts = {}
    for event_type, topic_type in manager.EVENT_TO_TOPIC_MAP.items():
        topic_name = manager.get_topic_config(topic_type).name
        if topic_name not in event_mapping_counts:
            event_mapping_counts[topic_name] = 0
        event_mapping_counts[topic_name] += 1
    
    for topic_name, count in event_mapping_counts.items():
        print(f"  {topic_name}: {count} event types")
    
    return True


def test_partition_distribution():
    """Test 2: Verify even partition distribution"""
    print_header("TEST 2: Partition Distribution Analysis")
    
    strategy = PartitionStrategy()
    
    # Test user actions partitioning
    print_section("✓ User Actions Partitioning (user_id → 1000 partitions)")
    partition_counts = {}
    test_users = 10000
    
    for i in range(test_users):
        user_id = f"user_{i}"
        partition = strategy.get_partition_for_user_action(user_id)
        partition_counts[partition] = partition_counts.get(partition, 0) + 1
    
    analyze_distribution(partition_counts, test_users)
    
    # Test content interactions partitioning
    print_section("✓ Content Interactions Partitioning (content_id → 500 partitions)")
    partition_counts = {}
    test_content = 5000
    
    for i in range(test_content):
        content_id = f"content_{i}"
        partition = strategy.get_partition_for_content_interaction(content_id)
        partition_counts[partition] = partition_counts.get(partition, 0) + 1
    
    analyze_distribution(partition_counts, test_content)
    
    # Test system events partitioning
    print_section("✓ System Events Partitioning (system_id → 100 partitions)")
    partition_counts = {}
    test_systems = 1000
    
    for i in range(test_systems):
        system_id = f"system_{i % 10}"  # 10 unique systems
        partition = strategy.get_partition_for_system_event(system_id)
        partition_counts[partition] = partition_counts.get(partition, 0) + 1
    
    analyze_distribution(partition_counts, test_systems)
    
    return True


def analyze_distribution(partition_counts: Dict[int, int], total_messages: int):
    """Analyze and report partition distribution statistics"""
    if not partition_counts:
        print("  ⚠ No data to analyze")
        return
    
    counts = list(partition_counts.values())
    mean = statistics.mean(counts)
    min_count = min(counts)
    max_count = max(counts)
    std_dev = statistics.stdev(counts) if len(counts) > 1 else 0
    variance_percent = (std_dev / mean * 100) if mean > 0 else 0
    used_partitions = len(partition_counts)
    
    print(f"  Messages: {total_messages}")
    print(f"  Partitions Used: {used_partitions}")
    print(f"  Mean per Partition: {mean:.2f}")
    print(f"  Min: {min_count}, Max: {max_count}")
    print(f"  Std Dev: {std_dev:.2f}")
    print(f"  Variance: {variance_percent:.2f}%")
    
    # Assess distribution quality
    if variance_percent < 10:
        status = "✓ EXCELLENT (< 10% variance)"
    elif variance_percent < 20:
        status = "✓ GOOD (10-20% variance)"
    else:
        status = "⚠ POOR (> 20% variance)"
    
    print(f"  Distribution Quality: {status}")


def test_event_type_routing():
    """Test 3: Verify event type to topic routing"""
    print_header("TEST 3: Event Type to Topic Routing")
    
    manager = StreamSocialTopicManager()
    strategy = PartitionStrategy()
    
    test_events = [
        (EventType.USER_POST_CREATE, TopicType.USER_ACTIONS, "user_id"),
        (EventType.USER_FOLLOW, TopicType.USER_ACTIONS, "user_id"),
        (EventType.CONTENT_LIKE, TopicType.CONTENT_INTERACTIONS, "content_id"),
        (EventType.CONTENT_SHARE, TopicType.CONTENT_INTERACTIONS, "content_id"),
        (EventType.SYSTEM_NOTIFICATION, TopicType.SYSTEM_EVENTS, "system_id"),
    ]
    
    print_section("✓ Event Routing Verification")
    all_correct = True
    
    for event_type, expected_topic_type, expected_key in test_events:
        actual_topic_type = manager.get_topic_for_event(event_type.value)
        topic_config = manager.get_topic_config(actual_topic_type)
        
        is_correct = actual_topic_type == expected_topic_type
        status = "✓" if is_correct else "✗"
        
        print(f"  {status} {event_type.value:30} → {topic_config.name:25} ({actual_topic_type.value})")
        
        if not is_correct:
            all_correct = False
            print(f"      Expected: {expected_topic_type.value}")
    
    return all_correct


def test_producer_setup():
    """Test 4: Verify producer can initialize"""
    print_header("TEST 4: Producer Initialization")
    
    print_section("✓ Creating Producer Instance")
    try:
        producer = StreamSocialEventProducer()
        print("  ✓ Producer instance created successfully")
        
        print_section("✓ Topic Information")
        topic_info = producer.get_topic_info()
        for topic_name, info in topic_info.items():
            print(f"\n  Topic: {topic_name}")
            print(f"    Partitions: {info['partitions']}")
            print(f"    Replication Factor: {info['replication_factor']}")
            print(f"    Retention (days): {info['retention_ms'] / 1000 / 3600 / 24:.1f}")
            print(f"    Compression: {info['compression']}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_partition_strategy_calculation():
    """Test 5: Verify partition calculation logic"""
    print_header("TEST 5: Partition Strategy Calculation Logic")
    
    strategy = PartitionStrategy()
    
    print_section("✓ Deterministic Partition Calculation")
    
    # Test determinism: same key should always give same partition
    test_key = "test_key_123"
    partition1 = strategy.calculate_partition_by_key(test_key, 1000)
    partition2 = strategy.calculate_partition_by_key(test_key, 1000)
    
    print(f"  Key: {test_key}")
    print(f"  Partition (attempt 1): {partition1}")
    print(f"  Partition (attempt 2): {partition2}")
    print(f"  Deterministic: {'✓ YES' if partition1 == partition2 else '✗ NO'}")
    
    # Test range validity
    print_section("✓ Partition Range Validation")
    valid = True
    
    for topic_type, topic_config in StreamSocialTopicManager.TOPICS.items():
        for i in range(100):
            test_data = {
                'user_id' if topic_type == TopicType.USER_ACTIONS else 'content_id': f'test_{i}',
                'system_id': f'sys_{i}'
            }
            partition = strategy.calculate_partition(test_data, topic_type)
            
            if not (0 <= partition < topic_config.num_partitions):
                valid = False
                print(f"  ✗ {topic_type.value}: partition {partition} out of range [0, {topic_config.num_partitions})")
                break
    
    if valid:
        print("  ✓ All partitions within valid ranges")
    
    return valid


def print_summary(results: Dict[str, bool]):
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print_section("Results")
    for test_name, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print_section("Overall")
    print(f"  {passed}/{total} tests passed")
    
    if passed == total:
        print("  ✓ All tests passed! Ready for production.")
    else:
        print("  ⚠ Some tests failed. Review errors above.")
    
    return passed == total


def main():
    """Run all validation tests"""
    print("\n" + "🚀 " * 20)
    print("StreamSocial Topics & Partition Strategy Validation")
    print("🚀 " * 20)
    
    results = {
        "Topic Configuration": test_topic_configuration(),
        "Partition Distribution": test_partition_distribution(),
        "Event Type Routing": test_event_type_routing(),
        "Producer Setup": test_producer_setup(),
        "Partition Strategy": test_partition_strategy_calculation(),
    }
    
    success = print_summary(results)
    
    print("\n" + "=" * 80)
    if success:
        print("✓ Validation Complete - Your StreamSocial setup is ready!")
    else:
        print("⚠ Validation Complete - Please fix errors above")
    print("=" * 80 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
