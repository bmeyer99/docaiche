"""Browser logs endpoint for shipping client-side logs to Loki"""

import json
import aiohttp
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/logs", tags=["logging"])

class LogStream(BaseModel):
    stream: Dict[str, str]
    values: List[List[str]]

class BrowserLogsRequest(BaseModel):
    streams: List[LogStream]

# Loki push endpoint
LOKI_PUSH_URL = "http://loki:3100/loki/api/v1/push"

@router.post("/browser")
async def receive_browser_logs(request: BrowserLogsRequest):
    """
    Receive logs from browser and forward to Loki
    """
    try:
        # Forward to Loki
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
            }
            
            # Convert to Loki format
            loki_data = {
                "streams": []
            }
            
            for stream in request.streams:
                # Add server-side metadata
                enhanced_stream = {
                    "stream": {
                        **stream.stream,
                        "source": "browser",
                        "ingested_at": datetime.utcnow().isoformat(),
                    },
                    "values": stream.values
                }
                loki_data["streams"].append(enhanced_stream)
            
            async with session.post(
                LOKI_PUSH_URL,
                json=loki_data,
                headers=headers
            ) as response:
                if response.status != 204:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to forward logs to Loki: {error_text}"
                    )
        
        return {"status": "success", "message": "Logs received and forwarded"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing browser logs: {str(e)}"
        )

@router.get("/browser/status")
async def browser_logs_status():
    """Check if browser logging endpoint is available"""
    return {
        "status": "available",
        "loki_endpoint": LOKI_PUSH_URL,
        "accepting_logs": True
    }