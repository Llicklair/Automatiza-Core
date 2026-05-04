import { request } from "./client";

export interface UnifiedCalendarEvent {
    id: string;
    source: "event" | "reservation" | "invoice_due" | "payroll";
    title: string;
    start: string;
    end: string | null;
    color: "blue" | "purple" | "red" | "amber" | "green";
    href: string;
    subtitle: string | null;
}

export const calendarUnified = {
    list: (start: string, end: string) =>
        request<UnifiedCalendarEvent[]>(
            `/api/v1/calendar/unified?start=${start}&end=${end}`
        ),
};
