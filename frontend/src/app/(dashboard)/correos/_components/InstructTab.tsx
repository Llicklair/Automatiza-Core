"use client";

import type { Dispatch, SetStateAction } from "react";
import { useTranslations } from "next-intl";
import { Bot, Loader2 } from "lucide-react";

interface InstructTabProps {
    instruction: string;
    setInstruction: Dispatch<SetStateAction<string>>;
    loading: boolean;
    handleInstruct: (e: React.FormEvent) => void;
}

export function InstructTab({ instruction, setInstruction, loading, handleInstruct }: InstructTabProps) {
    const t = useTranslations("correos");
    return (
        <form onSubmit={handleInstruct} className="space-y-4">
            <p className="text-sm text-muted-foreground">
                {t("instruct.help")}
            </p>
            <textarea
                required
                rows={4}
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                placeholder={t("instruct.placeholder")}
                className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
            <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                {t("instruct.run")}
            </button>
        </form>
    );
}
