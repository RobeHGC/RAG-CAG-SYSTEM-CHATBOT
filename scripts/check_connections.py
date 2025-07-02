#!/usr/bin/env python3
"""
Database connection health check script for Bot Provisional.
Quick health check utility to verify all database connections are working.
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import settings
from src.common.database import DatabaseManager, DatabaseError

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message: str, status: str = "info"):
    """Print colored status message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "success":
        print(f"[{timestamp}] {Colors.GREEN}✓{Colors.END} {message}")
    elif status == "error":
        print(f"[{timestamp}] {Colors.RED}✗{Colors.END} {message}")
    elif status == "warning":
        print(f"[{timestamp}] {Colors.YELLOW}⚠{Colors.END} {message}")
    elif status == "info":
        print(f"[{timestamp}] {Colors.BLUE}ℹ{Colors.END} {message}")
    elif status == "progress":
        print(f"[{timestamp}] {Colors.CYAN}→{Colors.END} {message}")
    else:
        print(f"[{timestamp}] {message}")

def print_header(title: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}{'='*50}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}{title.center(50)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}{'='*50}{Colors.END}")

def check_postgresql(db_manager: DatabaseManager) -> Dict[str, any]:
    """
    Check PostgreSQL connection and basic functionality.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        Dictionary with check results
    """
    result = {
        "name": "PostgreSQL",
        "status": "unknown",
        "details": {},
        "errors": []
    }
    
    try:
        print_status("Testing PostgreSQL connection...", "progress")
        
        # Basic connection test
        start_time = time.time()
        connected = db_manager.postgres.test_connection()
        connection_time = time.time() - start_time
        
        if not connected:
            result["status"] = "failed"
            result["errors"].append("Connection test failed")
            return result
        
        result["details"]["connection_time_ms"] = round(connection_time * 1000, 2)
        print_status(f"Connection successful ({connection_time:.3f}s)", "success")
        
        # Check database version
        try:
            version_result = db_manager.postgres.execute_query("SELECT version() as version")
            if version_result:
                result["details"]["version"] = version_result[0]["version"]
                print_status("Database version retrieved", "info")
        except Exception as e:
            result["errors"].append(f"Version check failed: {e}")
        
        # Check schemas
        try:
            schema_result = db_manager.postgres.execute_query(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('fine_tuning', 'analytics')"
            )
            schemas = [row["schema_name"] for row in schema_result]
            result["details"]["schemas"] = schemas
            
            if "fine_tuning" in schemas and "analytics" in schemas:
                print_status("Required schemas found", "success")
            else:
                result["errors"].append(f"Missing schemas. Found: {schemas}")
                print_status(f"Schema check failed. Found: {schemas}", "warning")
        except Exception as e:
            result["errors"].append(f"Schema check failed: {e}")
        
        # Check table count
        try:
            table_result = db_manager.postgres.execute_query(
                "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema IN ('fine_tuning', 'analytics')"
            )
            if table_result:
                table_count = table_result[0]["count"]
                result["details"]["table_count"] = table_count
                print_status(f"Found {table_count} tables", "info")
        except Exception as e:
            result["errors"].append(f"Table count check failed: {e}")
        
        # Performance test
        try:
            start_time = time.time()
            db_manager.postgres.execute_query("SELECT COUNT(*) FROM pg_stat_activity")
            query_time = time.time() - start_time
            result["details"]["query_time_ms"] = round(query_time * 1000, 2)
            print_status(f"Query performance test passed ({query_time:.3f}s)", "success")
        except Exception as e:
            result["errors"].append(f"Performance test failed: {e}")
        
        result["status"] = "healthy" if not result["errors"] else "degraded"
        
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Unexpected error: {e}")
        print_status(f"PostgreSQL check failed: {e}", "error")
    
    return result

def check_redis(db_manager: DatabaseManager) -> Dict[str, any]:
    """
    Check Redis connection and basic functionality.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        Dictionary with check results
    """
    result = {
        "name": "Redis",
        "status": "unknown",
        "details": {},
        "errors": []
    }
    
    try:
        print_status("Testing Redis connection...", "progress")
        
        # Basic connection test
        start_time = time.time()
        connected = db_manager.redis.test_connection()
        connection_time = time.time() - start_time
        
        if not connected:
            result["status"] = "failed"
            result["errors"].append("Connection test failed")
            return result
        
        result["details"]["connection_time_ms"] = round(connection_time * 1000, 2)
        print_status(f"Connection successful ({connection_time:.3f}s)", "success")
        
        # Get Redis info
        try:
            redis_info = db_manager.redis.client.info()
            result["details"]["version"] = redis_info.get("redis_version", "unknown")
            result["details"]["memory_used"] = redis_info.get("used_memory_human", "unknown")
            result["details"]["connected_clients"] = redis_info.get("connected_clients", 0)
            print_status(f"Redis v{result['details']['version']}", "info")
        except Exception as e:
            result["errors"].append(f"Info retrieval failed: {e}")
        
        # Test SET/GET operations
        try:
            test_key = "health_check:test"
            test_value = f"test_{int(time.time())}"
            
            start_time = time.time()
            db_manager.redis.set(test_key, test_value, ex=60)
            set_time = time.time() - start_time
            
            start_time = time.time()
            retrieved_value = db_manager.redis.get(test_key)
            get_time = time.time() - start_time
            
            if retrieved_value == test_value:
                result["details"]["set_time_ms"] = round(set_time * 1000, 2)
                result["details"]["get_time_ms"] = round(get_time * 1000, 2)
                print_status("SET/GET operations successful", "success")
                
                # Clean up
                db_manager.redis.delete(test_key)
            else:
                result["errors"].append("SET/GET test failed - value mismatch")
        except Exception as e:
            result["errors"].append(f"SET/GET test failed: {e}")
        
        # Check keyspace
        try:
            db_info = db_manager.redis.client.info("keyspace")
            keyspace_data = {}
            for key, value in db_info.items():
                if key.startswith("db"):
                    keyspace_data[key] = value
            result["details"]["keyspace"] = keyspace_data
            
            if keyspace_data:
                print_status(f"Keyspace info: {len(keyspace_data)} databases", "info")
            else:
                print_status("Empty keyspace", "info")
        except Exception as e:
            result["errors"].append(f"Keyspace check failed: {e}")
        
        result["status"] = "healthy" if not result["errors"] else "degraded"
        
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Unexpected error: {e}")
        print_status(f"Redis check failed: {e}", "error")
    
    return result

def check_neo4j(db_manager: DatabaseManager) -> Dict[str, any]:
    """
    Check Neo4j connection and basic functionality.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        Dictionary with check results
    """
    result = {
        "name": "Neo4j",
        "status": "unknown",
        "details": {},
        "errors": []
    }
    
    try:
        print_status("Testing Neo4j connection...", "progress")
        
        # Basic connection test
        start_time = time.time()
        connected = db_manager.neo4j.test_connection()
        connection_time = time.time() - start_time
        
        if not connected:
            result["status"] = "failed"
            result["errors"].append("Connection test failed")
            return result
        
        result["details"]["connection_time_ms"] = round(connection_time * 1000, 2)
        print_status(f"Connection successful ({connection_time:.3f}s)", "success")
        
        # Get Neo4j version and edition
        try:
            version_result = db_manager.neo4j.run_query("CALL dbms.components() YIELD name, versions, edition")
            if version_result:
                for component in version_result:
                    if component["name"] == "Neo4j Kernel":
                        result["details"]["version"] = component["versions"][0] if component["versions"] else "unknown"
                        result["details"]["edition"] = component["edition"]
                        print_status(f"Neo4j {result['details']['edition']} v{result['details']['version']}", "info")
                        break
        except Exception as e:
            result["errors"].append(f"Version check failed: {e}")
        
        # Count nodes and relationships
        try:
            node_result = db_manager.neo4j.run_query("MATCH (n) RETURN COUNT(n) as node_count")
            if node_result:
                result["details"]["node_count"] = node_result[0]["node_count"]
                print_status(f"Found {result['details']['node_count']} nodes", "info")
            
            rel_result = db_manager.neo4j.run_query("MATCH ()-[r]->() RETURN COUNT(r) as rel_count")
            if rel_result:
                result["details"]["relationship_count"] = rel_result[0]["rel_count"]
                print_status(f"Found {result['details']['relationship_count']} relationships", "info")
        except Exception as e:
            result["errors"].append(f"Count check failed: {e}")
        
        # Test basic operations
        try:
            test_query = """
            CREATE (test:HealthCheck {id: $test_id, timestamp: datetime()})
            RETURN test.id as created_id
            """
            test_id = f"health_check_{int(time.time())}"
            
            start_time = time.time()
            create_result = db_manager.neo4j.run_query(test_query, {"test_id": test_id})
            create_time = time.time() - start_time
            
            if create_result and create_result[0]["created_id"] == test_id:
                result["details"]["create_time_ms"] = round(create_time * 1000, 2)
                print_status("Node creation test successful", "success")
                
                # Clean up test node
                cleanup_query = "MATCH (test:HealthCheck {id: $test_id}) DELETE test"
                db_manager.neo4j.run_query(cleanup_query, {"test_id": test_id})
            else:
                result["errors"].append("Node creation test failed")
        except Exception as e:
            result["errors"].append(f"Operation test failed: {e}")
        
        # Check constraints
        try:
            constraints_result = db_manager.neo4j.run_query("SHOW CONSTRAINTS")
            constraint_count = len(constraints_result) if constraints_result else 0
            result["details"]["constraint_count"] = constraint_count
            print_status(f"Found {constraint_count} constraints", "info")
        except Exception as e:
            result["errors"].append(f"Constraint check failed: {e}")
        
        result["status"] = "healthy" if not result["errors"] else "degraded"
        
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Unexpected error: {e}")
        print_status(f"Neo4j check failed: {e}", "error")
    
    return result

def generate_report(results: List[Dict[str, any]], output_file: Optional[str] = None) -> Dict[str, any]:
    """
    Generate a health check report.
    
    Args:
        results: List of database check results
        output_file: Optional file path to save JSON report
        
    Returns:
        Complete report dictionary
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "unknown",
        "databases": results,
        "summary": {
            "total": len(results),
            "healthy": 0,
            "degraded": 0,
            "failed": 0
        }
    }
    
    # Calculate summary
    for result in results:
        if result["status"] == "healthy":
            report["summary"]["healthy"] += 1
        elif result["status"] == "degraded":
            report["summary"]["degraded"] += 1
        elif result["status"] == "failed":
            report["summary"]["failed"] += 1
    
    # Determine overall status
    if report["summary"]["failed"] > 0:
        report["overall_status"] = "critical"
    elif report["summary"]["degraded"] > 0:
        report["overall_status"] = "degraded"
    elif report["summary"]["healthy"] == report["summary"]["total"]:
        report["overall_status"] = "healthy"
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print_status(f"Report saved to {output_file}", "info")
        except Exception as e:
            print_status(f"Failed to save report: {e}", "warning")
    
    return report

def main():
    """Main health check function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Health Check for Bot Provisional")
    parser.add_argument("--output", "-o", help="Output file for JSON report")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode - minimal output")
    parser.add_argument("--json", "-j", action="store_true", help="Output only JSON report")
    
    args = parser.parse_args()
    
    if not args.quiet and not args.json:
        print_header("Database Health Check")
        print_status("Starting health check...", "info")
        print_status(f"Project: {settings.project_name}", "info")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    results = []
    
    try:
        # Check each database
        databases = [
            ("PostgreSQL", check_postgresql),
            ("Redis", check_redis),
            ("Neo4j", check_neo4j)
        ]
        
        for db_name, check_function in databases:
            if not args.quiet and not args.json:
                print(f"\n{Colors.CYAN}Checking {db_name}...{Colors.END}")
            
            result = check_function(db_manager)
            results.append(result)
            
            if not args.quiet and not args.json:
                status_color = Colors.GREEN if result["status"] == "healthy" else Colors.YELLOW if result["status"] == "degraded" else Colors.RED
                print_status(f"{db_name}: {status_color}{result['status'].upper()}{Colors.END}", "info")
        
        # Generate report
        report = generate_report(results, args.output)
        
        if args.json:
            print(json.dumps(report, indent=2))
        elif not args.quiet:
            print_header("Health Check Summary")
            print_status(f"Overall Status: {report['overall_status'].upper()}", "info")
            print_status(f"Healthy: {report['summary']['healthy']}", "success")
            print_status(f"Degraded: {report['summary']['degraded']}", "warning")
            print_status(f"Failed: {report['summary']['failed']}", "error")
            
            if report["overall_status"] == "healthy":
                print_status("All databases are healthy! 🎉", "success")
            elif report["overall_status"] == "degraded":
                print_status("Some databases have issues but are functional", "warning")
            else:
                print_status("Critical issues detected - some databases are down", "error")
        
        # Return appropriate exit code
        if report["overall_status"] == "healthy":
            return 0
        elif report["overall_status"] == "degraded":
            return 1
        else:
            return 2
            
    except KeyboardInterrupt:
        if not args.quiet:
            print_status("\nHealth check interrupted by user", "warning")
        return 130
    except Exception as e:
        if not args.quiet:
            print_status(f"Health check failed: {e}", "error")
        return 1
    finally:
        # Clean up connections
        db_manager.close_all()

if __name__ == "__main__":
    sys.exit(main())