"""
Performance monitoring utilities for WhatsApp message processing
"""

import time
import logging
from functools import wraps
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Context manager for monitoring performance metrics"""
    
    def __init__(self, operation_name, log_queries=False, log_slow_queries=True):
        self.operation_name = operation_name
        self.log_queries = log_queries
        self.log_slow_queries = log_slow_queries
        self.start_time = None
        self.initial_query_count = 0
        
    def __enter__(self):
        self.start_time = time.time()
        self.initial_query_count = len(connection.queries)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration = end_time - self.start_time
        query_count = len(connection.queries) - self.initial_query_count
        
        # Log performance metrics
        logger.info(f"PERFORMANCE [{self.operation_name}]: {duration:.3f}s, {query_count} queries")
        
        # Log slow operations
        if duration > 0.1:  # Log operations taking more than 100ms
            logger.warning(f"SLOW OPERATION [{self.operation_name}]: {duration:.3f}s, {query_count} queries")
        
        # Log queries if requested
        if self.log_queries and query_count > 0:
            recent_queries = connection.queries[-query_count:]
            for i, query in enumerate(recent_queries):
                logger.debug(f"Query {i+1}: {query['time']}s - {query['sql'][:100]}...")
        
        # Log slow queries
        if self.log_slow_queries and query_count > 0:
            recent_queries = connection.queries[-query_count:]
            slow_queries = [q for q in recent_queries if float(q['time']) > 0.01]
            if slow_queries:
                logger.warning(f"SLOW QUERIES [{self.operation_name}]: {len(slow_queries)} queries > 10ms")
                for query in slow_queries:
                    logger.warning(f"  {query['time']}s: {query['sql'][:150]}...")

def monitor_performance(operation_name, log_queries=False):
    """Decorator for monitoring function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceMonitor(operation_name, log_queries):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def log_performance_summary():
    """Log a summary of current performance metrics"""
    total_queries = len(connection.queries)
    if total_queries > 0:
        recent_queries = connection.queries[-10:]  # Last 10 queries
        avg_time = sum(float(q['time']) for q in recent_queries) / len(recent_queries)
        slow_queries = [q for q in recent_queries if float(q['time']) > 0.01]
        
        logger.info(f"PERFORMANCE SUMMARY: {total_queries} total queries, avg {avg_time:.3f}s, {len(slow_queries)} slow")

class QueryCounter:
    """Simple query counter for performance testing"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.start_count = len(connection.queries)
        self.start_time = time.time()
    
    def get_stats(self):
        current_count = len(connection.queries)
        current_time = time.time()
        
        return {
            'queries': current_count - self.start_count,
            'time': current_time - self.start_time,
            'queries_per_second': (current_count - self.start_count) / max(current_time - self.start_time, 0.001)
        }
    
    def log_stats(self, operation_name="Operation"):
        stats = self.get_stats()
        logger.info(f"{operation_name}: {stats['queries']} queries in {stats['time']:.3f}s ({stats['queries_per_second']:.1f} q/s)")

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'order_processing_max_time': 0.5,  # 500ms max for order processing
    'order_processing_max_queries': 50,  # 50 queries max for order processing
    'product_matching_max_time': 0.1,  # 100ms max for product matching
    'product_matching_max_queries': 10,  # 10 queries max for product matching
    'stock_checking_max_time': 0.05,  # 50ms max for stock checking
    'stock_checking_max_queries': 5,  # 5 queries max for stock checking
}

def check_performance_thresholds(operation_type, duration, query_count):
    """Check if performance metrics exceed thresholds"""
    time_threshold = PERFORMANCE_THRESHOLDS.get(f'{operation_type}_max_time', float('inf'))
    query_threshold = PERFORMANCE_THRESHOLDS.get(f'{operation_type}_max_queries', float('inf'))
    
    issues = []
    if duration > time_threshold:
        issues.append(f"Time exceeded: {duration:.3f}s > {time_threshold}s")
    if query_count > query_threshold:
        issues.append(f"Queries exceeded: {query_count} > {query_threshold}")
    
    if issues:
        logger.error(f"PERFORMANCE THRESHOLD EXCEEDED [{operation_type}]: {', '.join(issues)}")
        return False
    
    return True
