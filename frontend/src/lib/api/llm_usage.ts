import { request } from "./client";

export interface LlmAgentUsage {
  agent: string;
  provider: string;
  calls: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
}

export interface LlmMonthStats {
  month: string;
  total_calls: number;
  total_tokens_in: number;
  total_tokens_out: number;
  estimated_cost_usd: number;
  by_agent: LlmAgentUsage[];
}

export interface LlmUsageStats {
  months: LlmMonthStats[];
}

export const llmUsage = {
  stats: (months = 3) =>
    request<LlmUsageStats>(`/api/v1/llm-usage/stats?months=${months}`),
};
