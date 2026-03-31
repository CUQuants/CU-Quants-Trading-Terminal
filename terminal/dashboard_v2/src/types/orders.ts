import type { Exchange } from "./orderbook";

export interface Order {
  id: string;
  pair: string;
  exchange: Exchange;
  side: "buy" | "sell";
  type: "limit" | "market" | "iceberg";
  price?: number;
  visible_size?: number;
  size: number;
  status: string;
  created_at?: string;
}

export interface OrderParams {
  pair: string;
  side: "buy" | "sell";
  type: "limit" | "market" | "iceberg";
  price?: number;
  visible_size?: number;
  size: number;
}

export interface OrderResult {
  id: string;
}

export interface OrderEvent {
  type: "order_event";
  exchange: Exchange;
  pair: string;
  orderId: string;
  status: string;
  side: string;
  price: number;
  size: number;
  timestamp: string;
}

export interface StatusEvent {
  type: "status";
  exchange: Exchange;
  connectionStatus: "connected" | "reconnecting" | "disconnected";
}

export interface PongEvent {
  type: "pong";
  id: string;
}

export type BackendWsMessage = OrderEvent | StatusEvent | PongEvent;
