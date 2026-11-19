import type { Exchange } from "../types/orderbook";
import type {
  AvailableCash,
  AvailablePosition,
  AllBalances,
  AllPositions,
} from "../types/account";
import { request } from "./client";


export function fetchAvailableCash(
  exchange: Exchange,
  pair: string,
): Promise<AvailableCash> {
  return request(
    `/account/cash/${exchange}?pair=${encodeURIComponent(pair)}`,
  );
}

export function fetchAvailablePositions(
  exchange: Exchange,
  pair: string,
): Promise<AvailablePosition> {
  return request(
    `/account/positions/${exchange}?pair=${encodeURIComponent(pair)}`,
  );
}

export function fetchAllBalances(exchange: Exchange): Promise<AllBalances> {
  return request(`/account/balances/${exchange}`);
}

export function fetchAllPositions(exchange: Exchange): Promise<AllPositions> {
  return request(`/account/positions/${exchange}`);
}
