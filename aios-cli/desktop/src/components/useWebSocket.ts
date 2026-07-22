import { useEffect, useRef, useCallback, useState } from "react";

const WS_URL = "ws://127.0.0.1:8765";

export type EventHandler = (event: string, payload: Record<string, unknown>) => void;
export type ResponseHandler = (id: number | string | null, result: unknown) => void;

export function useWebSocket(onEvent: EventHandler, onResponse: ResponseHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const msgIdRef = useRef(1);
  const [connected, setConnected] = useState(false);
  const eventRef = useRef(onEvent);
  const responseRef = useRef(onResponse);
  eventRef.current = onEvent;
  responseRef.current = onResponse;

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        eventRef.current("connection", { status: "connected" });
      };

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.method === "event") {
            eventRef.current(msg.params.event, msg.params.payload as Record<string, unknown>);
          } else if (msg.id !== undefined) {
            // JSON-RPC response
            if (msg.result !== undefined) {
              responseRef.current(msg.id, msg.result);
            } else if (msg.error !== undefined) {
              const errMsg = typeof msg.error === "object" && msg.error !== null
                ? (msg.error.message || JSON.stringify(msg.error))
                : String(msg.error);
              responseRef.current(msg.id, { error: errMsg });
            }
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setConnected(false);
        eventRef.current("connection", { status: "disconnected" });
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  const send = useCallback((method: string, params: Record<string, unknown> = {}) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return undefined;
    const id = msgIdRef.current++;
    ws.send(
      JSON.stringify({
        jsonrpc: "2.0",
        id,
        method,
        params,
      })
    );
    return id;
  }, []);

  const sendBinary = useCallback((data: ArrayBufferLike) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(data);
  }, []);

  const sendChat = useCallback(
    (text: string) => {
      send("chat.send", { text, stream: true });
    },
    [send]
  );

  const queryTools = useCallback(() => {
    send("tools.list");
  }, [send]);

  const queryTimeline = useCallback(() => {
    send("timeline.history", { limit: 50 });
  }, [send]);

  return { connected, send, sendBinary, sendChat, queryTools, queryTimeline };
}
