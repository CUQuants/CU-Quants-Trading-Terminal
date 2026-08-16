export interface AvailableCash {
  exchange: string;
  currency: string;
  available: number;
  frozen: number;
  total: number;
}

export interface AvailablePosition {
  exchange: string;
  pair: string;
  base_currency: string;
  available: number;
  frozen: number;
  total: number;
}

export interface BalanceEntry {
  currency: string;
  available: number;
  frozen: number;
  total: number;
}

export interface AllBalances {
  exchange: string;
  currencies: BalanceEntry[];
}

export interface PositionEntry {
  currency: string;
  available: number;
  frozen: number;
  total: number;
}

export interface AllPositions {
  exchange: string;
  positions: PositionEntry[];
}
