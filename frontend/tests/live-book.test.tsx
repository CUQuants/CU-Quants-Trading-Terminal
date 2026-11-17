// @vitest-environment jsdom
import { useEffect } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { KrakenWsProvider, useKrakenWs } from "../src/contexts/KrakenWsContext";
import { StackedOrderbook } from "../src/components/StackedOrderbook";
import { DepthChart } from "../src/components/DepthChart";

class FakeWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  send = vi.fn();
  constructor(public url: string) { FakeWebSocket.instances.push(this); }
  open() { this.readyState = 1; this.onopen?.(); }
  close() { this.readyState = 3; this.onclose?.(); }
  message(type: string, bids: {price: number; qty: number}[], asks: {price: number; qty: number}[]) {
    this.onmessage?.({ data: JSON.stringify({ channel: "book", type, data: [{ symbol: "BTC/USD", bids, asks }] }) });
  }
}
function LiveBook({ pair = "BTC/USD" }: { pair?: string }) {
  const { subscribe, unsubscribe, orderbook, connectionStatus } = useKrakenWs();
  useEffect(() => { subscribe(pair); return () => unsubscribe(pair); }, [subscribe, unsubscribe, pair]);
  const data = orderbook[pair];
  return <><span>{connectionStatus}</span>{data ? <><StackedOrderbook data={data} pair={pair}/><DepthChart data={data}/></> : <span>Waiting for data</span>}</>;
}
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); FakeWebSocket.instances = []; });
it("feeds both layouts from provider snapshots and incremental updates, and cleans subscriptions", () => {
  vi.useFakeTimers(); vi.stubGlobal("WebSocket", FakeWebSocket);
  const { rerender } = render(<KrakenWsProvider><LiveBook/></KrakenWsProvider>);
  expect(screen.getByText("Waiting for data")).toBeTruthy();
  const ws = FakeWebSocket.instances[0];
  expect(ws.url).toBe("wss://ws.kraken.com/v2");
  act(() => ws.open());
  expect(JSON.parse(ws.send.mock.calls[0][0])).toMatchObject({ method: "subscribe", params: { symbol: ["BTC/USD"], channel: "book" } });
  act(() => { ws.message("snapshot", [{ price: 100, qty: 2 }], [{ price: 102, qty: 3 }]); vi.advanceTimersByTime(500); });
  expect(screen.getByRole("button", { name: "Use bid price 100" })).toBeTruthy();
  const before = screen.getByRole("img").outerHTML;
  act(() => { ws.message("update", [{ price: 100, qty: 0 }, { price: 99, qty: 4 }], []); vi.advanceTimersByTime(500); });
  expect(screen.queryByRole("button", { name: "Use bid price 100" })).toBeNull();
  expect(screen.getByRole("button", { name: "Use bid price 99" })).toBeTruthy();
  expect(screen.getByRole("img").outerHTML).not.toBe(before);
  rerender(<KrakenWsProvider><LiveBook pair="ETH/USD"/></KrakenWsProvider>);
  expect(screen.getByText("Waiting for data")).toBeTruthy();
  expect(ws.send.mock.calls.some(([raw]) => JSON.parse(raw).method === "unsubscribe")).toBe(true);
});
