#!/usr/bin/env python3
"""
Simple metrics server for database service.
Provides basic filesystem and health metrics for Prometheus.
"""

import os
import time
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.end_headers()
            
            # Generate metrics
            metrics = self.generate_metrics()
            self.wfile.write(metrics.encode('utf-8'))
            
        elif path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            health_status = '{"status": "healthy", "service": "database", "timestamp": "' + time.strftime('%Y-%m-%dT%H:%M:%SZ') + '"}'
            self.wfile.write(health_status.encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def generate_metrics(self):
        """Generate Prometheus-style metrics."""
        metrics = []
        
        # Database up metric
        metrics.append("# HELP db_up Whether the database service is up")
        metrics.append("# TYPE db_up gauge")
        metrics.append("db_up 1")
        
        # Database file exists
        db_file_exists = 1 if os.path.exists("/data/docaiche.db") else 0
        metrics.append("# HELP db_file_exists Whether the database file exists")
        metrics.append("# TYPE db_file_exists gauge")
        metrics.append(f"db_file_exists {db_file_exists}")
        
        # Database file size
        try:
            db_size = os.path.getsize("/data/docaiche.db") if os.path.exists("/data/docaiche.db") else 0
            metrics.append("# HELP db_file_size_bytes Database file size in bytes")
            metrics.append("# TYPE db_file_size_bytes gauge")
            metrics.append(f"db_file_size_bytes {db_size}")
        except OSError:
            pass
        
        # Disk usage of data directory
        try:
            total, used, free = shutil.disk_usage("/data")
            metrics.append("# HELP db_disk_total_bytes Total disk space in bytes")
            metrics.append("# TYPE db_disk_total_bytes gauge")
            metrics.append(f"db_disk_total_bytes {total}")
            
            metrics.append("# HELP db_disk_used_bytes Used disk space in bytes")
            metrics.append("# TYPE db_disk_used_bytes gauge")
            metrics.append(f"db_disk_used_bytes {used}")
            
            metrics.append("# HELP db_disk_free_bytes Free disk space in bytes")
            metrics.append("# TYPE db_disk_free_bytes gauge")
            metrics.append(f"db_disk_free_bytes {free}")
        except OSError:
            pass
        
        # Uptime (approximated by file modification time)
        try:
            start_time = os.path.getmtime("/data")
            uptime = time.time() - start_time
            metrics.append("# HELP db_uptime_seconds Service uptime in seconds")
            metrics.append("# TYPE db_uptime_seconds counter")
            metrics.append(f"db_uptime_seconds {uptime}")
        except OSError:
            pass
        
        return "\n".join(metrics) + "\n"
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_server():
    """Run the metrics server."""
    print("Database metrics server starting on port 5432...")
    try:
        server = HTTPServer(('0.0.0.0', 5432), MetricsHandler)
        print("Server bound successfully, serving requests...")
        server.serve_forever()
    except Exception as e:
        print(f"Error starting server: {e}")
        raise
    except KeyboardInterrupt:
        print("Server stopping...")
        server.shutdown()


if __name__ == '__main__':
    run_server()