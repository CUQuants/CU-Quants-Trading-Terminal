import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { cancelOrder, ApiError } from "../api/orders";
import type { Exchange } from "../types/orderbook";

export function useCancelOrder(exchange: Exchange) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ orderId, pair }: { orderId: string; pair: string }) =>
      cancelOrder(exchange, orderId, pair),

    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["orders", exchange, variables.pair],
      });
      queryClient.invalidateQueries({
        queryKey: ["account", "cash", exchange, variables.pair],
      });
      queryClient.invalidateQueries({
        queryKey: ["account", "positions", exchange, variables.pair],
      });
      toast.success("Order cancelled");
    },

    onError: (error, variables) => {
      if (error instanceof ApiError && error.status >= 500) {
        queryClient.invalidateQueries({
          queryKey: ["orders", exchange, variables.pair],
        });
        toast.error(
          "Cancel may have succeeded — please check your orders",
        );
      } else {
        toast.error(
          error instanceof Error ? error.message : "Failed to cancel order",
        );
      }
    },
  });
}
