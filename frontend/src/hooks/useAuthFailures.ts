import { useQuery } from "@tanstack/react-query";
import type { AuthFailure } from "../types/reporting";
import { fetchAuthFailures } from "../api/reporting";

export function useAuthFailures() {
  return useQuery<AuthFailure[]>({
    queryKey: ["reporting", "auth-failures"],
    queryFn: fetchAuthFailures,
    staleTime: 30_000,
    retry: false,
  });
}
