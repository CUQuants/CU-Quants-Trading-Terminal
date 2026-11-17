// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrderPanel } from "../src/components/OrderPanel";
import { DepthChart } from "../src/components/DepthChart";

const { mutate } = vi.hoisted(() => ({ mutate: vi.fn() }));
vi.mock("../src/hooks/usePlaceOrder", () => ({ usePlaceOrder: () => ({ mutate, isPending: false }) }));
vi.mock("../src/hooks/useAvailableCash", () => ({ useAvailableCash: () => ({}) }));
vi.mock("../src/hooks/useAvailablePositions", () => ({ useAvailablePositions: () => ({}) }));
vi.mock("../src/components/OrderList", () => ({ OrderList: () => null }));
vi.mock("../src/contexts/ActiveOrdersContext", () => ({ useActiveOrders: () => ({ hasOrderAtPrice: (_exchange: string, _pair: string, price: number) => price === 100 }) }));
const book = { symbol: "BTC/USD", bids: [{ price: 100, qty: 2 }], asks: [{ price: 102, qty: 3 }] };
const panel = (data = book, pair = "BTC/USD") => <OrderPanel exchange="kraken" pair={pair} orderbook={data} onClose={() => {}}/>;
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("order-book selection", () => {
  it("fills the clicked price, preserves quantity and side, and never submits", async () => {
    const user = userEvent.setup();
    render(panel());
    await user.click(screen.getByRole("button", { name: "Sell", exact: true }));
    fireEvent.change(screen.getByLabelText("Size"), { target: { value: "0.25" } });
    await user.click(screen.getByRole("button", { name: "Use ask price 102" }));
    expect((screen.getByLabelText("Price") as HTMLInputElement).value).toBe("102");
    expect((screen.getByLabelText("Size") as HTMLInputElement).value).toBe("0.25");
    expect(screen.getByRole("button", { name: "Sell BTC/USD" })).toBeTruthy();
    expect(mutate).not.toHaveBeenCalled();
  });
  it("switches market to limit so the selected price is used", async () => {
    const user = userEvent.setup(); render(panel());
    await user.click(screen.getByRole("button", { name: "Market", exact: true }));
    expect(screen.queryByLabelText("Price")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Use bid price 100" }));
    expect((screen.getByLabelText("Price") as HTMLInputElement).value).toBe("100");
    expect(mutate).not.toHaveBeenCalled();
  });
  it("supports keyboard activation and reselecting the same level after editing", async () => {
    const user = userEvent.setup(); render(panel());
    const level = screen.getByRole("button", { name: "Use bid price 100" });
    level.focus(); await user.keyboard("{Enter}");
    fireEvent.change(screen.getByLabelText("Price"), { target: { value: "99" } });
    level.focus(); await user.keyboard(" ");
    expect((screen.getByLabelText("Price") as HTMLInputElement).value).toBe("100");
    expect(mutate).not.toHaveBeenCalled();
  });
  it("keeps iceberg and display quantity when picking a price", async () => {
    const user = userEvent.setup(); render(panel());
    await user.click(screen.getByRole("button", { name: "Iceberg" }));
    fireEvent.change(screen.getByPlaceholderText("Visible quantity in book"), { target: { value: "0.1" } });
    await user.click(screen.getByRole("button", { name: "Use ask price 102" }));
    expect((screen.getByPlaceholderText("Visible quantity in book") as HTMLInputElement).value).toBe("0.1");
    expect(mutate).not.toHaveBeenCalled();
  });
  it("allows selecting stacked levels and keeps active-order markers", async () => {
    const user = userEvent.setup(); render(panel());
    await user.click(screen.getByRole("button", { name: "Order book", exact: true }));
    expect(screen.getByLabelText("Your active order")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Use bid price 100" }));
    expect((screen.getByLabelText("Price") as HTMLInputElement).value).toBe("100");
  });
  it("incoming book updates refresh levels without overwriting the entered price", async () => {
    const user = userEvent.setup(); const { rerender } = render(panel());
    await user.click(screen.getByRole("button", { name: "Use bid price 100" }));
    rerender(panel({ ...book, bids: [{ price: 99, qty: 4 }] }));
    expect(screen.getByRole("button", { name: "Use bid price 99" })).toBeTruthy();
    expect((screen.getByLabelText("Price") as HTMLInputElement).value).toBe("100");
    expect(mutate).not.toHaveBeenCalled();
  });
  it("submits the selected limit price only after the explicit submit button", async () => {
    const user = userEvent.setup(); render(panel());
    fireEvent.change(screen.getByLabelText("Size"), { target: { value: "0.25" } });
    await user.click(screen.getByRole("button", { name: "Market", exact: true }));
    await user.click(screen.getByRole("button", { name: "Use ask price 102" }));
    expect(mutate).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Buy BTC/USD" }));
    expect(mutate).toHaveBeenCalledExactlyOnceWith({ pair: "BTC/USD", side: "buy", type: "limit", price: 102, size: 0.25, visible_size: undefined });
  });
  it("a different keyed pair starts with an empty form", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<OrderPanel key="BTC/USD" exchange="kraken" pair="BTC/USD" orderbook={book} onClose={() => {}}/>);
    await user.click(screen.getByRole("button", { name: "Use bid price 100" }));
    rerender(<OrderPanel key="ETH/USD" exchange="kraken" pair="ETH/USD" orderbook={{ ...book, symbol: "ETH/USD" }} onClose={() => {}}/>);
    expect((screen.getByLabelText("Price") as HTMLInputElement).value).toBe("");
  });
});

it("depth responds to new quantities and prices, handles empty books", () => {
  const { rerender } = render(<DepthChart data={book}/>);
  const before = screen.getByRole("img").outerHTML;
  rerender(<DepthChart data={{ ...book, bids: [{ price: 99, qty: 10 }] }}/>);
  expect(screen.getByRole("img").outerHTML).not.toBe(before);
  rerender(<DepthChart data={{ ...book, bids: [], asks: [] }}/>);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText(/Waiting for both bids and asks/)).toBeTruthy();
});
