import { Bot } from "lucide-react";

export function ChatBubble({ text }: { text: string }) {
    return (
        <div className="px-6 pb-5 pt-3 border-t border-border/50">
            <div className="flex gap-3 items-start">
                <div className="p-1.5 rounded-lg bg-primary/20 mt-0.5 flex-shrink-0">
                    <Bot className="w-4 h-4 text-primary" />
                </div>
                <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 max-w-[90%]">
                    <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{text}</p>
                </div>
            </div>
        </div>
    );
}
