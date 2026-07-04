"use client";

import * as React from "react";

import { API_BASE } from "@/lib/api/client";

function wsUrl(path: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}${path}`;
}

const MAX_BACKOFF_MS = 15_000;

/** Subscribes to a backend WS channel with automatic reconnect
 * (exponential backoff, capped). `onMessage` is called with each parsed
 * JSON message; `enabled=false` tears the connection down (e.g. while
 * logged out for auth-gated channels). */
export function useWebSocketChannel<T = unknown>(
  path: string,
  onMessage: (message: T) => void,
  enabled = true
): void {
  // useEffectEvent: always sees the latest onMessage without needing to be
  // a reactive dependency that would tear down and reconnect the socket.
  const handleMessage = React.useEffectEvent((message: T) => {
    onMessage(message);
  });

  React.useEffect(() => {
    if (!enabled) return;

    let socket: WebSocket | null = null;
    let attempt = 0;
    let closedByEffect = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    function connect() {
      socket = new WebSocket(wsUrl(path));

      socket.onmessage = (event) => {
        try {
          handleMessage(JSON.parse(event.data));
        } catch {
          // ignore malformed frames
        }
      };

      socket.onopen = () => {
        attempt = 0;
      };

      socket.onclose = () => {
        if (closedByEffect) return;
        const delay = Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      closedByEffect = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [path, enabled]);
}
