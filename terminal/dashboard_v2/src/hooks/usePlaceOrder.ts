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
      toast.success("Order placed");
    },

    onError: (error, variables) => {
      if (error instanceof ApiError && error.status >= 500) {
        queryClient.invalidateQueries({
          queryKey: ["orders", exchange, variables.pair],
        });
        toast.error("Order may have been placed — please check your orders");
      } else {
        toast.error(
          error instanceof Error ? error.message : "Failed to place order",
        );
      }
    },
  });
}
