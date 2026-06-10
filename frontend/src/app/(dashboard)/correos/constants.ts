import { Send, Bot, Inbox } from "lucide-react";

export const TABS = [
    { key: "bandeja", label: "Bandeja", icon: Inbox },
    { key: "componer", label: "Componer", icon: Send },
    { key: "ia", label: "Instrucción IA", icon: Bot },
] as const;
export type TabKey = (typeof TABS)[number]["key"];
