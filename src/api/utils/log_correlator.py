"""
Log Correlator for tracing requests across services.

This module provides intelligent correlation of logs across multiple services
using correlation IDs, timing analysis, and service flow visualization.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import networkx as nx
import json

logger = logging.getLogger(__name__)


class LogCorrelator:
    """
    Correlate logs across services to trace request flows.
    
    Features:
    - Automatic service flow detection
    - Timing analysis and bottleneck identification
    - Error propagation tracking
    - Visual graph generation
    """
    
    def __init__(self):
        """Initialize the log correlator."""
        self.logger = logger
        
    def build_correlation_graph(self, 
                               logs: List[Dict[str, Any]], 
                               correlation_id: str) -> nx.DiGraph:
        """
        Build a directed graph representing the flow of a request.
        
        Args:
            logs: List of log entries with correlation_id
            correlation_id: The correlation ID to analyze
            
        Returns:
            NetworkX directed graph of the request flow
        """
        graph = nx.DiGraph()
        
        # Sort logs by timestamp
        sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", datetime.min))
        
        # Track service interactions
        service_states = {}
        last_service = None
        
        for log in sorted_logs:
            service = log.get("service", "unknown")
            timestamp = log.get("timestamp")
            
            # Add node if not exists
            if service not in graph:
                graph.add_node(service, 
                             first_seen=timestamp,
                             logs=[],
                             errors=0,
                             total_duration=0)
            
            # Update node data
            node_data = graph.nodes[service]
            node_data["logs"].append(log)
            node_data["last_seen"] = timestamp
            
            if log.get("level") in ["error", "fatal"]:
                node_data["errors"] += 1
                
            # Add edge if transitioning between services
            if last_service and last_service != service:
                if not graph.has_edge(last_service, service):
                    graph.add_edge(last_service, service, 
                                 transitions=0,
                                 avg_latency=0,
                                 latencies=[])
                
                edge_data = graph.edges[last_service, service]
                edge_data["transitions"] += 1
                
                # Calculate latency if possible
                if service_states.get(last_service, {}).get("last_timestamp"):
                    latency = (timestamp - service_states[last_service]["last_timestamp"]).total_seconds() * 1000
                    edge_data["latencies"].append(latency)
                    edge_data["avg_latency"] = sum(edge_data["latencies"]) / len(edge_data["latencies"])
            
            # Update service state
            if service not in service_states:
                service_states[service] = {}
            service_states[service]["last_timestamp"] = timestamp
            
            last_service = service
        
        # Calculate total duration for each service
        for service, data in graph.nodes(data=True):
            if data["logs"]:
                first_log = min(data["logs"], key=lambda x: x.get("timestamp", datetime.min))
                last_log = max(data["logs"], key=lambda x: x.get("timestamp", datetime.max))
                
                if first_log.get("timestamp") and last_log.get("timestamp"):
                    duration = (last_log["timestamp"] - first_log["timestamp"]).total_seconds() * 1000
                    data["total_duration"] = duration
        
        return graph
    
    def identify_bottlenecks(self, 
                           graph: nx.DiGraph, 
                           threshold_percentile: float = 0.8) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks in the request flow.
        
        Args:
            graph: Service flow graph
            threshold_percentile: Percentile threshold for bottleneck detection
            
        Returns:
            List of bottleneck services with details
        """
        bottlenecks = []
        
        # Get all service durations
        durations = []
        for service, data in graph.nodes(data=True):
            if data["total_duration"] > 0:
                durations.append((service, data["total_duration"]))
        
        if not durations:
            return bottlenecks
        
        # Sort by duration
        durations.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate total duration
        total_duration = sum(d[1] for d in durations)
        
        # Find services exceeding threshold
        threshold = total_duration * threshold_percentile
        cumulative = 0
        
        for service, duration in durations:
            cumulative += duration
            
            # Check if this service is a bottleneck
            percentage = (duration / total_duration) * 100 if total_duration > 0 else 0
            
            bottlenecks.append({
                "service": service,
                "duration_ms": duration,
                "percentage": percentage,
                "severity": self._calculate_bottleneck_severity(percentage),
                "log_count": len(graph.nodes[service]["logs"]),
                "error_count": graph.nodes[service]["errors"]
            })
            
            if cumulative >= threshold:
                break
        
        return bottlenecks
    
    def _calculate_bottleneck_severity(self, percentage: float) -> str:
        """Calculate bottleneck severity based on percentage of total time."""
        if percentage >= 70:
            return "critical"
        elif percentage >= 50:
            return "high"
        elif percentage >= 30:
            return "medium"
        else:
            return "low"
    
    def trace_error_propagation(self, 
                               graph: nx.DiGraph) -> Dict[str, Any]:
        """
        Trace how errors propagate through the service graph.
        
        Args:
            graph: Service flow graph
            
        Returns:
            Error propagation analysis
        """
        error_sources = []
        error_sinks = []
        error_chains = []
        
        # Find services with errors
        error_services = [(s, d) for s, d in graph.nodes(data=True) if d["errors"] > 0]
        
        if not error_services:
            return {
                "has_errors": False,
                "error_sources": [],
                "error_sinks": [],
                "error_chains": [],
                "total_errors": 0
            }
        
        # Sort by first error occurrence
        error_services.sort(key=lambda x: min(
            log.get("timestamp", datetime.max) 
            for log in x[1]["logs"] 
            if log.get("level") in ["error", "fatal"]
        ))
        
        # Identify error sources (services that first reported errors)
        if error_services:
            first_error_service = error_services[0][0]
            error_sources.append({
                "service": first_error_service,
                "error_count": error_services[0][1]["errors"],
                "first_error": self._get_first_error(error_services[0][1]["logs"])
            })
        
        # Trace error propagation paths
        for service, data in error_services:
            # Find downstream services that also have errors
            downstream_errors = []
            
            for successor in nx.descendants(graph, service):
                if graph.nodes[successor]["errors"] > 0:
                    downstream_errors.append(successor)
            
            if downstream_errors:
                error_chains.append({
                    "source": service,
                    "affected_services": downstream_errors,
                    "chain_length": len(downstream_errors) + 1
                })
        
        # Identify error sinks (services with errors but no downstream errors)
        for service, data in error_services:
            has_downstream_errors = any(
                graph.nodes[successor]["errors"] > 0 
                for successor in graph.successors(service)
            )
            
            if not has_downstream_errors and list(graph.successors(service)):
                error_sinks.append({
                    "service": service,
                    "error_count": data["errors"],
                    "contained": True
                })
        
        total_errors = sum(data["errors"] for _, data in error_services)
        
        return {
            "has_errors": True,
            "error_sources": error_sources,
            "error_sinks": error_sinks,
            "error_chains": error_chains,
            "total_errors": total_errors,
            "affected_services": len(error_services),
            "error_rate": total_errors / len(logs) if logs else 0
        }
    
    def _get_first_error(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get the first error from a list of logs."""
        error_logs = [
            log for log in logs 
            if log.get("level") in ["error", "fatal"]
        ]
        
        if not error_logs:
            return {}
            
        first_error = min(error_logs, key=lambda x: x.get("timestamp", datetime.max))
        
        return {
            "timestamp": first_error.get("timestamp").isoformat() if first_error.get("timestamp") else None,
            "message": first_error.get("message", ""),
            "error_type": first_error.get("error", first_error.get("error_type", "unknown"))
        }
    
    def calculate_service_dependencies(self, 
                                     graph: nx.DiGraph) -> Dict[str, Any]:
        """
        Calculate service dependencies and interaction patterns.
        
        Args:
            graph: Service flow graph
            
        Returns:
            Service dependency analysis
        """
        dependencies = {
            "services": {},
            "critical_path": [],
            "parallel_branches": [],
            "circular_dependencies": []
        }
        
        # Analyze each service
        for service in graph.nodes():
            predecessors = list(graph.predecessors(service))
            successors = list(graph.successors(service))
            
            dependencies["services"][service] = {
                "depends_on": predecessors,
                "dependency_count": len(predecessors),
                "depended_by": successors,
                "dependent_count": len(successors),
                "is_entry_point": len(predecessors) == 0,
                "is_exit_point": len(successors) == 0
            }
        
        # Find critical path (longest path through the graph)
        try:
            if graph.nodes():
                # Find all paths from entry points to exit points
                entry_points = [n for n in graph.nodes() if graph.in_degree(n) == 0]
                exit_points = [n for n in graph.nodes() if graph.out_degree(n) == 0]
                
                longest_path = []
                longest_duration = 0
                
                for entry in entry_points:
                    for exit in exit_points:
                        try:
                            paths = list(nx.all_simple_paths(graph, entry, exit))
                            for path in paths:
                                # Calculate path duration
                                path_duration = sum(
                                    graph.nodes[node]["total_duration"] 
                                    for node in path
                                )
                                
                                if path_duration > longest_duration:
                                    longest_duration = path_duration
                                    longest_path = path
                        except nx.NetworkXNoPath:
                            continue
                
                dependencies["critical_path"] = {
                    "path": longest_path,
                    "duration_ms": longest_duration,
                    "service_count": len(longest_path)
                }
        except Exception as e:
            logger.warning(f"Could not calculate critical path: {e}")
        
        # Detect circular dependencies
        try:
            cycles = list(nx.simple_cycles(graph))
            dependencies["circular_dependencies"] = [
                {
                    "cycle": cycle,
                    "services": len(cycle)
                }
                for cycle in cycles
            ]
        except Exception as e:
            logger.warning(f"Could not detect cycles: {e}")
        
        # Identify parallel branches
        dependencies["parallel_branches"] = self._identify_parallel_branches(graph)
        
        return dependencies
    
    def _identify_parallel_branches(self, graph: nx.DiGraph) -> List[Dict[str, Any]]:
        """Identify parallel execution branches in the graph."""
        parallel_branches = []
        
        # Find nodes with multiple successors (fan-out)
        for node in graph.nodes():
            successors = list(graph.successors(node))
            
            if len(successors) > 1:
                # Check if these successors eventually converge
                convergence_points = []
                
                for i, succ1 in enumerate(successors):
                    for succ2 in successors[i+1:]:
                        # Find common descendants
                        desc1 = set(nx.descendants(graph, succ1))
                        desc2 = set(nx.descendants(graph, succ2))
                        common = desc1.intersection(desc2)
                        
                        if common:
                            convergence_points.extend(common)
                
                parallel_branches.append({
                    "split_point": node,
                    "branches": successors,
                    "branch_count": len(successors),
                    "convergence_points": list(set(convergence_points))
                })
        
        return parallel_branches
    
    def generate_recommendations(self, 
                               graph: nx.DiGraph,
                               bottlenecks: List[Dict[str, Any]],
                               error_analysis: Dict[str, Any],
                               dependencies: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations based on correlation analysis.
        
        Args:
            graph: Service flow graph
            bottlenecks: Identified bottlenecks
            error_analysis: Error propagation analysis
            dependencies: Service dependency analysis
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Performance recommendations
        if bottlenecks:
            critical_bottlenecks = [b for b in bottlenecks if b["severity"] in ["critical", "high"]]
            if critical_bottlenecks:
                services = ", ".join(b["service"] for b in critical_bottlenecks[:3])
                recommendations.append(
                    f"Optimize performance in critical services: {services}"
                )
                
            # Check for services with both high duration and errors
            problematic = [
                b for b in bottlenecks 
                if b["error_count"] > 0 and b["severity"] in ["critical", "high"]
            ]
            if problematic:
                recommendations.append(
                    f"Address errors in slow services: {', '.join(p['service'] for p in problematic)}"
                )
        
        # Error recommendations
        if error_analysis["has_errors"]:
            if error_analysis["error_sources"]:
                source = error_analysis["error_sources"][0]["service"]
                recommendations.append(
                    f"Fix root cause errors in {source} service"
                )
                
            if error_analysis["error_chains"]:
                longest_chain = max(error_analysis["error_chains"], key=lambda x: x["chain_length"])
                recommendations.append(
                    f"Improve error handling to prevent cascading failures (chain length: {longest_chain['chain_length']})"
                )
        
        # Architecture recommendations
        if dependencies["circular_dependencies"]:
            recommendations.append(
                f"Resolve {len(dependencies['circular_dependencies'])} circular dependencies"
            )
            
        # Check for overly complex flows
        if len(graph.nodes()) > 10:
            recommendations.append(
                "Consider simplifying service architecture (>10 services in request flow)"
            )
            
        # Parallel processing opportunities
        sequential_services = [
            s for s, d in dependencies["services"].items()
            if d["dependency_count"] == 1 and d["dependent_count"] == 1
        ]
        if len(sequential_services) > 5:
            recommendations.append(
                "Explore parallel processing opportunities for sequential service chain"
            )
        
        # Caching recommendations
        total_duration = sum(
            data["total_duration"] 
            for _, data in graph.nodes(data=True)
        )
        if total_duration > 5000:  # 5 seconds
            recommendations.append(
                "Implement caching for frequently accessed data (total duration >5s)"
            )
        
        # Rate limiting recommendations
        if error_analysis["has_errors"]:
            rate_limit_errors = any(
                "rate" in log.get("message", "").lower() or 
                "limit" in log.get("message", "").lower()
                for _, data in graph.nodes(data=True)
                for log in data["logs"]
                if log.get("level") in ["error", "fatal"]
            )
            if rate_limit_errors:
                recommendations.append(
                    "Implement request queuing or backoff strategies for rate-limited services"
                )
        
        return recommendations[:5]  # Return top 5 recommendations