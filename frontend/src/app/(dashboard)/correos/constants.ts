import { Send, Bot, Inbox } from "lucide-react";

export const TABS = [
    { key: "bandeja", labelKey: "inbox", icon: Inbox },
    { key: "componer", labelKey: "compose", icon: Send },
    { key: "ia", labelKey: "ai", icon: Bot },
] as const;
export type TabKey = (typeof TABS)[number]["key"];
