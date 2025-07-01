"""
FastAPI Dashboard for Bot Provisional.
Main entry point for the web interface.
"""

import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.common.config import settings

# Setup logger
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    debug=settings.debug,
)


@app.get("/")
async def root():
    """Root endpoint returning simple HTML page."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{settings.project_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ color: #2c3e50; }}
            .status {{ color: #27ae60; }}
        </style>
    </head>
    <body>
        <h1 class="header">🤖 {settings.project_name}</h1>
        <p class="status">✅ Dashboard is running!</p>
        <p><strong>Version:</strong> {settings.version}</p>
        <p><strong>Debug Mode:</strong> {settings.debug}</p>
        
        <h2>Services</h2>
        <ul>
            <li>PostgreSQL: {settings.postgres_host}:{settings.postgres_port}</li>
            <li>Redis: {settings.redis_host}:{settings.redis_port}</li>
            <li>Neo4j: {settings.neo4j_uri}</li>
        </ul>
        
        <h2>API Endpoints</h2>
        <ul>
            <li><a href="/health">/health</a> - Health check</li>
            <li><a href="/docs">/docs</a> - API Documentation</li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring."""
    return {
        "status": "healthy",
        "service": "dashboard",
        "version": settings.version,
        "debug": settings.debug
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.dashboard.main:app",
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        reload=settings.dashboard_reload,
    )