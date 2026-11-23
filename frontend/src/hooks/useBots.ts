import { useQuery } from "@tanstack/react-query";
import type { BotStatus } from "../types/bots";
import { fetchBotStatus } from "../api/bots";

/** Live status of every speedbyte market on the box. 3s, as in xlrts. */
export function useBotStatus(refreshMs: number | false = 3_000) {
  return useQuery<BotStatus>({
    queryKey: ["bots"],
    queryFn: fetchBotStatus,
    refetchInterval: refreshMs,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
