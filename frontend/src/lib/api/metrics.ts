import { request } from "./client";

export interface TimeSavedBreakdownItem {
    action_type: string;
    count: number;
    minutes_each: number;
    minutes: number;
}

export interface TimeSavedSummary {
    days: number;
    total_actions: number;
    total_minutes: number;
    total_hours: number;
    breakdown: TimeSavedBreakdownItem[];
}

export const metricsApi = {
    timeSaved: (days = 30) =>
        request<TimeSavedSummary>(`/api/v1/metrics/time-saved?days=${days}`),
};
