import { useEffect, useRef, useState, useCallback } from "react";
import type {
  OrderbookData,
  OrderbookLevel,
  OkxBookMessage,
  OkxRawLevel,
} from "../types/orderbook";

const OKX_WS_URL = "wss://wsuspap.okx.com:8443/ws/v5/public";

interface UseOkxOrderbookOptions {
  symbol: string;
  depth?: number;
  autoConnect?: boolean;
  flushInterval?: number;
}

interface UseOkxOrderbookReturn {
  orderbook: OrderbookData | null;
  isConnected: boolean;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
}

function parseOkxLevels(raw: OkxRawLevel[]): OrderbookLevel[] {
  return raw.map(([price, qty]) => ({
    price: parseFloat(price),
    qty: parseFloat(qty),
  }));
}

/**
 * Hook for subscribing to OKX orderbook data via WebSocket.
 * Updates are batched in a ref and flushed to React state on an interval.
 */
export function useOkxOrderbook({
  symbol,
  depth = 10,
  autoConnect = true,
  flushInterval = 500,
}: UseOkxOrderbookOptions): UseOkxOrderbookReturn {
  const [orderbook, setOrderbook] = useState<OrderbookData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const orderbookRef = useRef<OrderbookData | null>(null);
  const dirtyRef = useRef(false);

  const applyUpdate = useCallback(
    (
      currentLevels: OrderbookLevel[],
      updates: OrderbookLevel[],
      isBids: boolean
    ): OrderbookLevel[] => {
      const levelMap = new Map<number, number>();
      currentLevels.forEach((level) => levelMap.set(level.price, level.qty));
      updates.forEach((update) => {
        if (update.qty === 0) {
          levelMap.delete(update.price);
        } else {
          levelMap.set(update.price, update.qty);
        }
      });
      return Array.from(levelMap.entries())
        .map(([price, qty]) => ({ price, qty }))
        .sort((a, b) => (isBids ? b.price - a.price : a.price - b.price))
        .slice(0, depth);
    },
    [depth]
  );

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setOrderbook(null);
    orderbookRef.current = null;
    dirtyRef.current = false;
  }, []);

  const connect = useCallback(() => {
    setError(null);
    const ws = new WebSocket(OKX_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (wsRef.current !== ws) return;
      setIsConnected(true);
      ws.send(
        JSON.stringify({
          op: "subscribe",
          args: [{ channel: "books", instId: symbol }],
        })
      );
    };

    ws.onmessage = (event: MessageEvent) => {
      if (wsRef.current !== ws) return;
      try {
        const raw = JSON.parse(event.data);

        // Ignore subscription confirmations
        if ("event" in raw) return;

        const message = raw as OkxBookMessage;
        if (!message.data || !message.action) return;

        const data = message.data[0];
        if (message.arg.instId !== symbol) return;

        if (message.action === "snapshot") {
          const newOrderbook: OrderbookData = {
            symbol,
            bids: parseOkxLevels(data.bids).slice(0, depth),
            asks: parseOkxLevels(data.asks).slice(0, depth),
            checksum: data.checksum,
          };
          orderbookRef.current = newOrderbook;
          setOrderbook(newOrderbook);
        } else if (message.action === "update" && orderbookRef.current) {
          const current = orderbookRef.current;
          const newOrderbook: OrderbookData = {
            symbol: current.symbol,
            bids:
              data.bids.length > 0
                ? applyUpdate(current.bids, parseOkxLevels(data.bids), true)
                : current.bids,
            asks:
              data.asks.length > 0
                ? applyUpdate(current.asks, parseOkxLevels(data.asks), false)
                : current.asks,
            checksum: data.checksum,
          };
          orderbookRef.current = newOrderbook;
          dirtyRef.current = true;
        }
      } catch (e) {
        console.error("Failed to parse OKX message:", e);
      }
    };

    ws.onerror = () => {
      if (wsRef.current !== ws) return;
      setError("WebSocket connection error");
    };

    ws.onclose = () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
        setIsConnected(false);
      }
    };
  }, [symbol, depth, applyUpdate]);

  // Batched flush: push ref state to React on an interval
  useEffect(() => {
    const id = setInterval(() => {
      if (dirtyRef.current && orderbookRef.current) {
        setOrderbook({ ...orderbookRef.current });
        dirtyRef.current = false;
      }
    }, flushInterval);
    return () => clearInterval(id);
  }, [flushInterval]);

  // Disconnect and reconnect whenever symbol, depth, or autoConnect changes
  useEffect(() => {
    if (!autoConnect) {
      disconnect();
      return;
    }
    disconnect();
    connect();
    return () => disconnect();
  }, [symbol, depth, autoConnect, connect, disconnect]);

  return {
    orderbook,
    isConnected,
    error,
    connect,
    disconnect,
  };
}
