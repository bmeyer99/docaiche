"""
Pattern Detector for identifying common issues and anomalies in logs.

This module provides intelligent pattern detection for troubleshooting,
including error patterns, performance anomalies, and known issue detection.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Pattern
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DetectionPattern:
    """Represents a detection pattern for log analysis."""
    name: str
    category: str
    regex: Pattern
    severity: str
    description: str
    recommended_action: str
    tags: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.8


class PatternDetector:
    """
    Detect patterns and anomalies in log data.
    
    Features:
    - Pre-defined pattern library for common issues
    - Dynamic pattern learning
    - Anomaly detection using statistical methods
    - Pattern clustering and correlation
    """
    
    def __init__(self):
        """Initialize the pattern detector with default patterns."""
        self.patterns = self._load_default_patterns()
        self.dynamic_patterns = {}
        self.pattern_stats = defaultdict(lambda: {"count": 0, "last_seen": None})
        
    def _load_default_patterns(self) -> Dict[str, DetectionPattern]:
        """Load default detection patterns."""
        patterns = {}
        
        # Connection/Network patterns
        patterns["connection_timeout"] = DetectionPattern(
            name="connection_timeout",
            category="connectivity",
            regex=re.compile(r"(connection|connect).*(timeout|timed out)", re.IGNORECASE),
            severity="high",
            description="Connection timeout detected",
            recommended_action="Check network connectivity and service availability",
            tags=["network", "timeout", "connectivity"]
        )
        
        patterns["connection_refused"] = DetectionPattern(
            name="connection_refused",
            category="connectivity",
            regex=re.compile(r"connection.*(refused|rejected)|ECONNREFUSED", re.IGNORECASE),
            severity="high",
            description="Connection refused by target service",
            recommended_action="Verify service is running and accepting connections",
            tags=["network", "connectivity", "service_down"]
        )
        
        patterns["dns_resolution_failure"] = DetectionPattern(
            name="dns_resolution_failure",
            category="connectivity",
            regex=re.compile(r"(dns|name).*(resolution|resolve).*(fail|error)|ENOTFOUND", re.IGNORECASE),
            severity="high",
            description="DNS resolution failure",
            recommended_action="Check DNS configuration and hostname validity",
            tags=["network", "dns", "configuration"]
        )
        
        # Performance patterns
        patterns["slow_query"] = DetectionPattern(
            name="slow_query",
            category="performance",
            regex=re.compile(r"(slow|long).*(query|request)|(query|request).*(slow|took|duration).*(ms|seconds?)", re.IGNORECASE),
            severity="medium",
            description="Slow query or request detected",
            recommended_action="Optimize query performance or add appropriate indexes",
            tags=["performance", "database", "optimization"]
        )
        
        patterns["high_latency"] = DetectionPattern(
            name="high_latency",
            category="performance",
            regex=re.compile(r"(high|increased|excessive).*(latency|response time)|latency.*(\d{4,}ms|\d+s)", re.IGNORECASE),
            severity="medium",
            description="High latency detected",
            recommended_action="Investigate service performance and resource utilization",
            tags=["performance", "latency", "slo"]
        )
        
        patterns["memory_pressure"] = DetectionPattern(
            name="memory_pressure",
            category="performance",
            regex=re.compile(r"(out of memory|OOM|memory.*(exhaust|pressure|limit))", re.IGNORECASE),
            severity="critical",
            description="Memory pressure or OOM condition",
            recommended_action="Increase memory limits or optimize memory usage",
            tags=["performance", "memory", "resources"]
        )
        
        # AI/ML specific patterns
        patterns["token_limit_exceeded"] = DetectionPattern(
            name="token_limit_exceeded",
            category="ai",
            regex=re.compile(r"token.*(limit|exceed|maximum)|context.*(length|size).*(exceed|too)", re.IGNORECASE),
            severity="medium",
            description="AI model token limit exceeded",
            recommended_action="Reduce prompt size or use a model with higher token limit",
            tags=["ai", "tokens", "limits"]
        )
        
        patterns["model_timeout"] = DetectionPattern(
            name="model_timeout",
            category="ai",
            regex=re.compile(r"(model|completion|inference).*(timeout|timed out)", re.IGNORECASE),
            severity="high",
            description="AI model request timeout",
            recommended_action="Increase timeout or optimize prompt complexity",
            tags=["ai", "timeout", "performance"]
        )
        
        patterns["rate_limit_exceeded"] = DetectionPattern(
            name="rate_limit_exceeded",
            category="ai",
            regex=re.compile(r"rate.*(limit|exceed)|429|too many requests", re.IGNORECASE),
            severity="medium",
            description="API rate limit exceeded",
            recommended_action="Implement request queuing or backoff strategy",
            tags=["ai", "rate_limit", "api"]
        )
        
        # Security patterns
        patterns["auth_failure"] = DetectionPattern(
            name="auth_failure",
            category="security",
            regex=re.compile(r"(auth|authentication|authorization).*(fail|denied|reject|invalid)", re.IGNORECASE),
            severity="high",
            description="Authentication or authorization failure",
            recommended_action="Verify credentials and permissions",
            tags=["security", "auth", "access"]
        )
        
        patterns["invalid_token"] = DetectionPattern(
            name="invalid_token",
            category="security",
            regex=re.compile(r"(token|jwt|bearer).*(invalid|expired|malformed)", re.IGNORECASE),
            severity="high",
            description="Invalid or expired token",
            recommended_action="Refresh authentication token",
            tags=["security", "token", "auth"]
        )
        
        # Data patterns
        patterns["data_validation_error"] = DetectionPattern(
            name="data_validation_error",
            category="data",
            regex=re.compile(r"(validation|schema).*(error|fail)|invalid.*(data|input|format)", re.IGNORECASE),
            severity="medium",
            description="Data validation error",
            recommended_action="Review input data format and validation rules",
            tags=["data", "validation", "input"]
        )
        
        patterns["json_parse_error"] = DetectionPattern(
            name="json_parse_error",
            category="data",
            regex=re.compile(r"json.*(parse|parsing).*(error|fail)|unexpected.*token", re.IGNORECASE),
            severity="medium",
            description="JSON parsing error",
            recommended_action="Validate JSON format and encoding",
            tags=["data", "json", "parsing"]
        )
        
        # Infrastructure patterns
        patterns["disk_space_low"] = DetectionPattern(
            name="disk_space_low",
            category="infrastructure",
            regex=re.compile(r"disk.*(space|full)|no space left|ENOSPC", re.IGNORECASE),
            severity="critical",
            description="Low disk space",
            recommended_action="Free up disk space or increase storage capacity",
            tags=["infrastructure", "disk", "storage"]
        )
        
        patterns["service_unavailable"] = DetectionPattern(
            name="service_unavailable",
            category="infrastructure",
            regex=re.compile(r"service.*(unavailable|down)|503|cannot connect to", re.IGNORECASE),
            severity="high",
            description="Service unavailable",
            recommended_action="Check service health and dependencies",
            tags=["infrastructure", "availability", "service"]
        )
        
        return patterns
    
    def detect_patterns(self, 
                       logs: List[Dict[str, Any]], 
                       custom_patterns: Optional[List[DetectionPattern]] = None) -> Dict[str, Any]:
        """
        Detect patterns in log entries.
        
        Args:
            logs: List of log entries
            custom_patterns: Additional patterns to check
            
        Returns:
            Pattern detection results
        """
        results = {
            "detected_patterns": [],
            "pattern_counts": defaultdict(int),
            "pattern_timeline": defaultdict(list),
            "anomalies": [],
            "statistics": {}
        }
        
        # Combine default and custom patterns
        all_patterns = dict(self.patterns)
        if custom_patterns:
            for pattern in custom_patterns:
                all_patterns[pattern.name] = pattern
        
        # Analyze each log
        for log in logs:
            message = log.get("message", "")
            timestamp = log.get("timestamp")
            service = log.get("service", "unknown")
            
            # Check against all patterns
            for pattern_name, pattern in all_patterns.items():
                if pattern.regex.search(message):
                    detection = {
                        "pattern": pattern_name,
                        "category": pattern.category,
                        "severity": pattern.severity,
                        "timestamp": timestamp,
                        "service": service,
                        "message": message,
                        "description": pattern.description,
                        "recommended_action": pattern.recommended_action,
                        "tags": pattern.tags
                    }
                    
                    results["detected_patterns"].append(detection)
                    results["pattern_counts"][pattern_name] += 1
                    results["pattern_timeline"][pattern_name].append({
                        "timestamp": timestamp,
                        "service": service
                    })
                    
                    # Update pattern statistics
                    self.pattern_stats[pattern_name]["count"] += 1
                    self.pattern_stats[pattern_name]["last_seen"] = timestamp
        
        # Detect anomalies
        results["anomalies"] = self._detect_anomalies(logs, results["detected_patterns"])
        
        # Calculate statistics
        results["statistics"] = self._calculate_statistics(
            logs, 
            results["detected_patterns"],
            results["pattern_counts"]
        )
        
        return results
    
    def _detect_anomalies(self, 
                         logs: List[Dict[str, Any]], 
                         detected_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalous patterns in logs."""
        anomalies = []
        
        # Time-based anomaly detection
        if logs:
            time_anomalies = self._detect_time_anomalies(logs)
            anomalies.extend(time_anomalies)
        
        # Pattern frequency anomalies
        pattern_anomalies = self._detect_pattern_anomalies(detected_patterns)
        anomalies.extend(pattern_anomalies)
        
        # Service behavior anomalies
        service_anomalies = self._detect_service_anomalies(logs)
        anomalies.extend(service_anomalies)
        
        return anomalies
    
    def _detect_time_anomalies(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in log timing patterns."""
        anomalies = []
        
        # Group logs by minute
        minute_buckets = defaultdict(list)
        for log in logs:
            if log.get("timestamp"):
                minute_key = log["timestamp"].replace(second=0, microsecond=0)
                minute_buckets[minute_key].append(log)
        
        if len(minute_buckets) < 5:
            return anomalies
        
        # Calculate statistics
        counts = [len(logs) for logs in minute_buckets.values()]
        if counts:
            mean_count = statistics.mean(counts)
            stdev_count = statistics.stdev(counts) if len(counts) > 1 else 0
            
            # Detect spikes (>2 standard deviations)
            for minute, minute_logs in minute_buckets.items():
                count = len(minute_logs)
                if stdev_count > 0 and count > mean_count + 2 * stdev_count:
                    anomalies.append({
                        "type": "traffic_spike",
                        "timestamp": minute,
                        "severity": "medium",
                        "description": f"Traffic spike detected: {count} logs/minute (normal: {mean_count:.1f})",
                        "details": {
                            "count": count,
                            "mean": mean_count,
                            "deviation": (count - mean_count) / stdev_count if stdev_count > 0 else 0
                        }
                    })
        
        # Detect gaps in logging
        if minute_buckets:
            sorted_minutes = sorted(minute_buckets.keys())
            for i in range(1, len(sorted_minutes)):
                gap = (sorted_minutes[i] - sorted_minutes[i-1]).total_seconds() / 60
                if gap > 5:  # Gap longer than 5 minutes
                    anomalies.append({
                        "type": "logging_gap",
                        "timestamp": sorted_minutes[i-1],
                        "severity": "low",
                        "description": f"Logging gap detected: {gap:.1f} minutes",
                        "details": {
                            "gap_minutes": gap,
                            "start": sorted_minutes[i-1],
                            "end": sorted_minutes[i]
                        }
                    })
        
        return anomalies
    
    def _detect_pattern_anomalies(self, detected_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in pattern occurrences."""
        anomalies = []
        
        # Group patterns by time window
        window_size = timedelta(minutes=5)
        pattern_windows = defaultdict(lambda: defaultdict(int))
        
        for detection in detected_patterns:
            if detection.get("timestamp"):
                window_key = detection["timestamp"].replace(
                    minute=detection["timestamp"].minute // 5 * 5,
                    second=0,
                    microsecond=0
                )
                pattern_windows[window_key][detection["pattern"]] += 1
        
        # Detect sudden pattern appearances
        for pattern_name in set(d["pattern"] for d in detected_patterns):
            pattern_timeline = sorted([
                d["timestamp"] for d in detected_patterns 
                if d["pattern"] == pattern_name and d.get("timestamp")
            ])
            
            if len(pattern_timeline) >= 5:
                # Check for burst (many occurrences in short time)
                for i in range(len(pattern_timeline) - 4):
                    time_span = (pattern_timeline[i+4] - pattern_timeline[i]).total_seconds()
                    if time_span < 60:  # 5 occurrences within 1 minute
                        anomalies.append({
                            "type": "pattern_burst",
                            "timestamp": pattern_timeline[i],
                            "severity": "high",
                            "description": f"Burst of '{pattern_name}' pattern detected",
                            "details": {
                                "pattern": pattern_name,
                                "count": 5,
                                "time_span_seconds": time_span
                            }
                        })
                        break
        
        return anomalies
    
    def _detect_service_anomalies(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in service behavior."""
        anomalies = []
        
        # Group by service
        service_logs = defaultdict(list)
        for log in logs:
            service = log.get("service", "unknown")
            service_logs[service].append(log)
        
        # Analyze each service
        for service, logs in service_logs.items():
            # Error rate anomalies
            error_logs = [l for l in logs if l.get("level") in ["error", "fatal"]]
            error_rate = len(error_logs) / len(logs) if logs else 0
            
            if error_rate > 0.3 and len(logs) > 10:  # >30% errors with sufficient samples
                anomalies.append({
                    "type": "high_error_rate",
                    "timestamp": max(l.get("timestamp") for l in error_logs if l.get("timestamp")),
                    "severity": "high",
                    "description": f"High error rate in {service}: {error_rate:.1%}",
                    "details": {
                        "service": service,
                        "error_rate": error_rate,
                        "error_count": len(error_logs),
                        "total_logs": len(logs)
                    }
                })
        
        return anomalies
    
    def _calculate_statistics(self,
                            logs: List[Dict[str, Any]],
                            detected_patterns: List[Dict[str, Any]],
                            pattern_counts: Dict[str, int]) -> Dict[str, Any]:
        """Calculate pattern detection statistics."""
        total_logs = len(logs)
        total_detections = len(detected_patterns)
        
        # Top patterns by count
        top_patterns = sorted(
            pattern_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Pattern distribution by category
        category_counts = defaultdict(int)
        for detection in detected_patterns:
            category_counts[detection["category"]] += 1
        
        # Severity distribution
        severity_counts = defaultdict(int)
        for detection in detected_patterns:
            severity_counts[detection["severity"]] += 1
        
        # Service impact
        affected_services = set()
        for detection in detected_patterns:
            affected_services.add(detection["service"])
        
        return {
            "total_logs_analyzed": total_logs,
            "total_patterns_detected": total_detections,
            "detection_rate": total_detections / total_logs if total_logs > 0 else 0,
            "unique_patterns": len(pattern_counts),
            "top_patterns": [
                {"pattern": p[0], "count": p[1], "percentage": p[1] / total_detections * 100}
                for p in top_patterns
            ] if total_detections > 0 else [],
            "category_distribution": dict(category_counts),
            "severity_distribution": dict(severity_counts),
            "affected_services": len(affected_services),
            "pattern_density": total_detections / total_logs if total_logs > 0 else 0
        }
    
    def learn_dynamic_patterns(self, 
                              logs: List[Dict[str, Any]], 
                              min_frequency: int = 5) -> List[DetectionPattern]:
        """
        Learn new patterns from log data using frequency analysis.
        
        Args:
            logs: List of log entries
            min_frequency: Minimum frequency for pattern consideration
            
        Returns:
            List of newly discovered patterns
        """
        # Extract error messages
        error_messages = [
            log.get("message", "")
            for log in logs
            if log.get("level") in ["error", "fatal"]
        ]
        
        if not error_messages:
            return []
        
        # Tokenize and find common subsequences
        # This is a simplified version - in production, use more sophisticated NLP
        word_sequences = defaultdict(int)
        
        for message in error_messages:
            words = re.findall(r'\b\w+\b', message.lower())
            
            # Find 2-3 word sequences
            for i in range(len(words) - 1):
                seq2 = " ".join(words[i:i+2])
                word_sequences[seq2] += 1
                
                if i < len(words) - 2:
                    seq3 = " ".join(words[i:i+3])
                    word_sequences[seq3] += 1
        
        # Filter by frequency
        frequent_sequences = [
            (seq, count) for seq, count in word_sequences.items()
            if count >= min_frequency
        ]
        
        # Create patterns from frequent sequences
        new_patterns = []
        for seq, count in sorted(frequent_sequences, key=lambda x: x[1], reverse=True)[:10]:
            # Skip common words
            if any(word in ["the", "a", "an", "is", "at", "to", "for"] for word in seq.split()):
                continue
                
            pattern_name = f"dynamic_{seq.replace(' ', '_')}"
            
            if pattern_name not in self.dynamic_patterns:
                new_pattern = DetectionPattern(
                    name=pattern_name,
                    category="learned",
                    regex=re.compile(re.escape(seq), re.IGNORECASE),
                    severity="medium",
                    description=f"Frequently occurring pattern: '{seq}'",
                    recommended_action="Investigate recurring issue",
                    tags=["learned", "dynamic"],
                    confidence_threshold=0.7
                )
                
                self.dynamic_patterns[pattern_name] = new_pattern
                new_patterns.append(new_pattern)
                
                logger.info(f"Learned new pattern: {pattern_name} (frequency: {count})")
        
        return new_patterns
    
    def get_pattern_library(self) -> Dict[str, List[str]]:
        """Get organized pattern library by category."""
        library = defaultdict(list)
        
        # Add default patterns
        for name, pattern in self.patterns.items():
            library[pattern.category].append(name)
        
        # Add dynamic patterns
        for name, pattern in self.dynamic_patterns.items():
            library[pattern.category].append(name)
        
        return dict(library)
    
    def export_patterns(self) -> List[Dict[str, Any]]:
        """Export all patterns in a serializable format."""
        patterns = []
        
        for name, pattern in {**self.patterns, **self.dynamic_patterns}.items():
            patterns.append({
                "name": name,
                "category": pattern.category,
                "regex": pattern.regex.pattern,
                "severity": pattern.severity,
                "description": pattern.description,
                "recommended_action": pattern.recommended_action,
                "tags": pattern.tags,
                "is_dynamic": name in self.dynamic_patterns
            })
        
        return patterns