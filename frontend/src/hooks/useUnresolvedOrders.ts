import { useQuery } from "@tanstack/react-query";
import type { UnresolvedOrder } from "../types/reporting";
import { fetchUnresolvedOrders } from "../api/reporting";

export function useUnresolvedOrders() {
  return useQuery<UnresolvedOrder[]>({
    queryKey: ["reporting", "unresolved"],
    queryFn: fetchUnresolvedOrders,
    staleTime: 30_000,
    retry: false,
  });
}
