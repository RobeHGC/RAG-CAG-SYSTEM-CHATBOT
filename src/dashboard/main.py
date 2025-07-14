"""
FastAPI Dashboard for Bot Provisional.
Main entry point for the web interface with real-time WebSocket support.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import redis.asyncio as redis

from src.common.config import settings
from src.common.monitoring import monitor
from src.common.enhanced_logging import enhanced_logger, with_logging_context, log_performance
from src.common.sentry_config import sentry_config, SentryContextManager
from src.common.profiling import profile_performance, profiler_manager
from src.common.health_checks import health_manager
from src.common.alerts import alert_manager
from .websocket_manager import websocket_manager, ConversationMessage, MessageType
from .auth import auth_system, get_current_user, require_permission, authenticate_and_create_session

# Setup enhanced logger
logger = enhanced_logger.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=f"{settings.project_name} - Dashboard",
    version=settings.version,
    debug=settings.debug,
    description="Real-time dashboard for monitoring conversations and system configuration"
)

# Setup templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Initialize Redis for WebSocket manager
redis_client = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global redis_client
    try:
        # Generate correlation ID for startup
        correlation_id = enhanced_logger.generate_correlation_id()
        enhanced_logger.set_correlation_id(correlation_id)
        enhanced_logger.set_request_context("startup", "SYSTEM")
        
        # Initialize Sentry
        sentry_config.initialize()
        SentryContextManager.add_breadcrumb("Dashboard startup initiated", "startup")
        
        # Initialize monitoring
        monitor.start_prometheus_server(port=8001, path='/metrics')
        logger.info("Prometheus metrics server started on port 8001")
        
        # Enable profiling and memory tracking
        profiler_manager.enable_memory_tracking()
        profiler_manager.profiling_enabled = True
        logger.info("Performance profiling enabled")
        
        # Initialize Redis connection
        redis_client = redis.from_url(f"redis://{settings.redis_host}:{settings.redis_port}/0")
        websocket_manager.redis = redis_client
        await redis_client.ping()
        
        # Record startup metrics
        monitor.increment_counter('app_startups_total', {'service': 'dashboard'})
        
        logger.info("Dashboard startup completed successfully")
        SentryContextManager.add_breadcrumb("Dashboard startup completed", "startup", level="info")
        
    except Exception as e:
        logger.error(f"Failed to initialize dashboard services: {e}")
        SentryContextManager.add_breadcrumb(f"Startup failed: {e}", "startup", level="error")
        # Don't re-raise to allow partial startup
        

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        correlation_id = enhanced_logger.generate_correlation_id()
        enhanced_logger.set_correlation_id(correlation_id)
        enhanced_logger.set_request_context("shutdown", "SYSTEM")
        
        SentryContextManager.add_breadcrumb("Dashboard shutdown initiated", "shutdown")
        
        # Close Redis connection
        if redis_client:
            await redis_client.close()
            
        # Record shutdown metrics
        monitor.increment_counter('app_shutdowns_total', {'service': 'dashboard'})
        
        logger.info("Dashboard shutdown completed")
        SentryContextManager.add_breadcrumb("Dashboard shutdown completed", "shutdown", level="info")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        SentryContextManager.add_breadcrumb(f"Shutdown error: {e}", "shutdown", level="error")


@app.post("/api/auth/login")
@profile_performance("dashboard_login")
@log_performance("dashboard_login", threshold_ms=500.0)
async def login(request: Request, credentials: Dict[str, str]):
    """Login endpoint for dashboard authentication."""
    correlation_id = enhanced_logger.generate_correlation_id()
    enhanced_logger.set_correlation_id(correlation_id)
    enhanced_logger.set_request_context("/api/auth/login", "POST")
    
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            monitor.increment_counter('auth_failures_total', {'reason': 'missing_credentials'})
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Set user context for logging
        enhanced_logger.set_user_context(username)
        SentryContextManager.set_user_context(username)
        SentryContextManager.add_breadcrumb(f"Login attempt for user: {username}", "auth")
        
        # Get client info
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent")
        
        # Authenticate and create session
        session_id = authenticate_and_create_session(username, password, client_ip, user_agent)
        
        if session_id:
            monitor.increment_counter('auth_successes_total', {'user': username})
            logger.info(f"Successful login for user: {username}")
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Login successful"
            }
        else:
            monitor.increment_counter('auth_failures_total', {'reason': 'invalid_credentials'})
            logger.warning(f"Failed login attempt for user: {username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except HTTPException:
        raise
    except Exception as e:
        monitor.increment_counter('auth_errors_total')
        logger.error(f"Login error: {e}")
        SentryContextManager.add_breadcrumb(f"Login error: {e}", "auth", level="error")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/auth/logout")
async def logout(session_id: str = None):
    """Logout endpoint."""
    if session_id and auth_system.invalidate_session(session_id):
        return {"status": "success", "message": "Logged out successfully"}
    return {"status": "success", "message": "No active session"}


@app.get("/api/auth/me")
async def get_current_user_info(user: Dict = Depends(get_current_user)):
    """Get current user information."""
    return {
        "status": "success",
        "user": {
            "username": user.username,
            "permissions": list(user.permissions),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "active": user.active
        }
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve login page."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard Login</title>
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .login-container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 400px; width: 100%; }
            .login-header { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            .form-control { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }
            .btn { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
            .btn:hover { background: #5a6fd8; }
            .error { color: #e53e3e; margin-top: 10px; }
            .success { color: #38a169; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>🤖 Dashboard Login</h1>
                <p>Enter your credentials to access the dashboard</p>
            </div>
            <form id="loginForm">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="username" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" class="form-control" required>
                </div>
                <button type="submit" class="btn">Login</button>
                <div id="message"></div>
            </form>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const messageDiv = document.getElementById('message');
                
                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        messageDiv.innerHTML = '<div class="success">Login successful! Redirecting...</div>';
                        localStorage.setItem('dashboard_session', data.session_id);
                        setTimeout(() => window.location.href = '/', 1000);
                    } else {
                        messageDiv.innerHTML = `<div class="error">${data.detail}</div>`;
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="error">Login failed. Please try again.</div>';
                }
            });
        </script>
    </body>
    </html>
    """)


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, user: Dict = Depends(get_current_user)):
    """Serve the main dashboard interface."""
    try:
        with open(os.path.join(templates_dir, "dashboard.html"), "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Dashboard Loading...</title></head>
            <body>
                <h1>🤖 {settings.project_name} Dashboard</h1>
                <p>Dashboard is initializing...</p>
                <p><a href="/health">Health Check</a> | <a href="/docs">API Docs</a></p>
            </body>
            </html>
            """,
            status_code=200
        )


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication."""
    try:
        await websocket_manager.connect(websocket, client_id)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data) if data else {}
            
            # Handle the message
            await websocket_manager.handle_message(client_id, message_data)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        await websocket_manager.disconnect(client_id)


@app.get("/api/stats")
async def get_dashboard_stats():
    """Get current dashboard statistics."""
    return await websocket_manager.get_dashboard_stats()


@app.post("/api/message/simulate")
async def simulate_message(message_data: Dict[str, Any]):
    """Simulate a new conversation message (for testing)."""
    try:
        message = ConversationMessage(
            message_id=f"sim_{datetime.now().timestamp()}",
            user_id=message_data.get("user_id", "test_user"),
            content=message_data.get("content", "Test message"),
            message_type=message_data.get("message_type", "user"),
            timestamp=datetime.now(),
            status="pending",
            emotional_state=message_data.get("emotional_state"),
            response_candidates=message_data.get("response_candidates", [])
        )
        
        await websocket_manager.add_conversation_message(message)
        
        return {
            "status": "success",
            "message": "Simulated message added",
            "message_id": message.message_id
        }
    except Exception as e:
        logger.error(f"Error simulating message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/pending")
async def get_pending_messages():
    """Get all pending messages."""
    pending = []
    for message_id, message in websocket_manager.pending_messages.items():
        pending.append(message.to_dict())
    
    return {
        "status": "success",
        "pending_messages": pending,
        "count": len(pending)
    }


@app.post("/api/message/{message_id}/approve")
async def approve_message_api(message_id: str, data: Dict[str, Any] = None):
    """API endpoint to approve a message."""
    try:
        if message_id in websocket_manager.pending_messages:
            await websocket_manager._handle_approve_request("api_client", {"message_id": message_id})
            return {"status": "success", "message": "Message approved"}
        else:
            raise HTTPException(status_code=404, detail="Message not found")
    except Exception as e:
        logger.error(f"Error approving message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/message/{message_id}/reject")
async def reject_message_api(message_id: str, data: Dict[str, Any]):
    """API endpoint to reject a message."""
    try:
        if message_id in websocket_manager.pending_messages:
            reason = data.get("reason", "Rejected via API")
            await websocket_manager._handle_reject_request("api_client", {
                "message_id": message_id,
                "reason": reason
            })
            return {"status": "success", "message": "Message rejected"}
        else:
            raise HTTPException(status_code=404, detail="Message not found")
    except Exception as e:
        logger.error(f"Error rejecting message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/message/{message_id}/edit")
async def edit_message_api(message_id: str, data: Dict[str, Any]):
    """API endpoint to edit a message."""
    try:
        if message_id in websocket_manager.pending_messages:
            new_content = data.get("new_content")
            if not new_content:
                raise HTTPException(status_code=400, detail="new_content is required")
            
            await websocket_manager._handle_edit_request("api_client", {
                "message_id": message_id,
                "new_content": new_content
            })
            return {"status": "success", "message": "Message edited"}
        else:
            raise HTTPException(status_code=404, detail="Message not found")
    except Exception as e:
        logger.error(f"Error editing message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics")
async def get_analytics():
    """Get analytics data for the dashboard."""
    stats = await websocket_manager.get_dashboard_stats()
    
    # Calculate additional analytics
    total_processed = len(websocket_manager.approved_messages) + len(websocket_manager.rejected_messages)
    approval_rate = (
        len(websocket_manager.approved_messages) / total_processed * 100 
        if total_processed > 0 else 0
    )
    
    return {
        "status": "success",
        "analytics": {
            **stats,
            "approval_rate": round(approval_rate, 2),
            "total_processed": total_processed,
            "avg_response_time": "< 200ms",  # Placeholder
            "active_users": len(set(msg.user_id for msg in websocket_manager.pending_messages.values()))
        }
    }


@app.get("/health")
@profile_performance("dashboard_health_check")
async def health_check():
    """Comprehensive health check endpoint for Docker and monitoring."""
    correlation_id = enhanced_logger.generate_correlation_id()
    enhanced_logger.set_correlation_id(correlation_id)
    enhanced_logger.set_request_context("/health", "GET")
    
    try:
        # Get comprehensive health status
        health_status = await health_manager.get_overall_health()
        
        # Add dashboard-specific metrics
        dashboard_metrics = {
            "dashboard_specific": {
                "active_connections": len(websocket_manager.active_connections),
                "pending_messages": len(websocket_manager.pending_messages),
                "approved_messages": len(websocket_manager.approved_messages),
                "rejected_messages": len(websocket_manager.rejected_messages),
                "websocket_uptime": (datetime.now() - websocket_manager.last_activity).total_seconds()
            },
            "service_info": {
                "name": "dashboard",
                "version": settings.version,
                "debug": settings.debug,
                "environment": getattr(settings, 'environment', 'development')
            }
        }
        
        # Merge with comprehensive health data
        health_status.update(dashboard_metrics)
        
        # Record health check metrics
        monitor.increment_counter('health_checks_total', {'service': 'dashboard'})
        
        # Set appropriate status code based on overall health
        status_code = 200
        if health_status.get('overall_status') == 'unhealthy':
            status_code = 503
        elif health_status.get('overall_status') == 'degraded':
            status_code = 200  # Still return 200 for degraded
            
        return health_status
        
    except Exception as e:
        monitor.increment_counter('health_check_errors_total', {'service': 'dashboard'})
        logger.error(f"Health check error: {e}")
        SentryContextManager.add_breadcrumb(f"Health check failed: {e}", "health", level="error")
        
        # Return minimal health info on error
        return {
            "status": "error",
            "service": "dashboard",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    try:
        # Return metrics from the monitoring system
        return monitor.get_metrics()
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")


@app.get("/api/monitoring/status")
@profile_performance("dashboard_monitoring_status")
async def monitoring_status():
    """Get detailed monitoring and performance status."""
    correlation_id = enhanced_logger.generate_correlation_id()
    enhanced_logger.set_correlation_id(correlation_id)
    
    try:
        # Get performance statistics
        perf_stats = profiler_manager.get_all_stats()
        
        # Get alert status
        alert_status = alert_manager.get_alert_status()
        
        # Get health check results
        health_results = await health_manager.run_all_checks()
        
        return {
            "status": "success",
            "monitoring": {
                "performance_stats": perf_stats,
                "alert_status": alert_status,
                "health_checks": {name: result.to_dict() for name, result in health_results.items()},
                "profiling_enabled": profiler_manager.profiling_enabled,
                "memory_tracking_enabled": profiler_manager.memory_tracking_enabled
            }
        }
        
    except Exception as e:
        logger.error(f"Monitoring status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.dashboard.main:app",
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        reload=settings.dashboard_reload,
    )