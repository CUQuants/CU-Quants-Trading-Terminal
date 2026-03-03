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
