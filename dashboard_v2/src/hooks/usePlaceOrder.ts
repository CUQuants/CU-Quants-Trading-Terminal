import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { placeOrder, ApiError } from "../api/orders";
import type { Exchange } from "../types/orderbook";
import type { OrderParams } from "../types/orders";

export function usePlaceOrder(exchange: Exchange) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: OrderParams) => placeOrder(exchange, params),

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
      toast.success("Order placed");
    },

    onError: (error, variables) => {
      let message = "Failed to place order";
      if (error instanceof ApiError) {
        if (error.status >= 500) {
          queryClient.invalidateQueries({
            queryKey: ["orders", exchange, variables.pair],
          });
          toast.error("Order may have been placed — please check your orders");
          return;
        }
        if (error.status === 400) {
          try {
            const parsed = JSON.parse(error.message) as { detail?: string };
            if (parsed.detail) message = parsed.detail;
          } catch {
            message = error.message;
          }
        } else {
          message = error.message;
        }
      } else if (error instanceof Error) {
        message = error.message;
      }
      toast.error(message);
    },
  });
}
