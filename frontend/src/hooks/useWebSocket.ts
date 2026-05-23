import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketHookResult<T> {
  isConnected: boolean;
  messages: T[];
  sendMessage: (msg: any) => void;
  clearMessages: () => void;
}

export function useWebSocket<T>(url?: string): WebSocketHookResult<T> {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<T[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const wsUrl = url || process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/ws/live';

  const connect = useCallback(() => {
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.info('WebSocket connection established:', wsUrl);
      };

      ws.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setMessages((prev) => [parsedData, ...prev].slice(0, 100)); // Cap local list at 100
        } catch (err) {
          console.warn('Failed to parse WebSocket message data:', event.data, err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.warn('WebSocket connection closed. Attempting reconnect in 5s...');
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket connection error:', error);
      };
    } catch (err) {
      console.error('Error instantiating WebSocket:', err);
    }
  }, [wsUrl]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn('Cannot send message, WebSocket is not open');
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { isConnected, messages, sendMessage, clearMessages };
}
