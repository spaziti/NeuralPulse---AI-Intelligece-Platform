import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.redis_client import redis_client

logger = logging.getLogger("neuralpulse.websocket")
router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New WebSocket client connected")

    if not redis_client.client:
        logger.error("Redis client not initialized, closing WebSocket")
        await websocket.close(code=1011, reason="Cache layer unavailable")
        return

    # Create a pub/sub subscription for this connection
    pubsub = redis_client.client.pubsub()
    await pubsub.subscribe("live_news_feed")

    try:
        # Send initial confirmation status
        await websocket.send_json({
            "type": "SYSTEM_STATUS",
            "message": "Connected to NeuralPulse real-time news stream"
        })

        while True:
            # Periodically poll for Redis pub/sub events
            # We use a short timeout so the loop yields control and keeps connection responsive
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message and message.get("data"):
                payload_str = message.get("data")
                await websocket.send_text(payload_str)
            
            # Simple heartbeat check/receive to detect client disconnection
            # We can use websocket.receive_text with a timeout or just depend on WebSocketDisconnect
            # from standard keepalive. To avoid blocking, we do a short delay
            await asyncio.sleep(0.05)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}")
    finally:
        # Clean up subscription
        try:
            await pubsub.unsubscribe("live_news_feed")
            await pubsub.close()
        except Exception as e:
            logger.error(f"Error during pubsub shutdown: {e}")
