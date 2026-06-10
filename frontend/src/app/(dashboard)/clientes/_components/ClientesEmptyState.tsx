"use client";

import { useTranslations } from "next-intl";

import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Building2 } from "lucide-react";

interface ClientesEmptyStateProps {
    openCreateModal: () => void;
    sendAiTask: (suggestion: string) => void;
}

export function ClientesEmptyState({ openCreateModal, sendAiTask }: ClientesEmptyStateProps) {
    const t = useTranslations("clientes");

    return (
        <div className="flex flex-col items-center">
            <EmptyState
                icon={Building2}
                title={t("emptyTitle")}
                description={t("emptyDescription")}
                action={{ label: t("newClient"), onClick: openCreateModal }}
            />
            <div className="flex flex-col items-center gap-2 pb-8">
                <p className="text-xs text-muted-foreground uppercase tracking-widest font-medium">{t("orCreateWithAI")}</p>
                <div className="flex flex-wrap justify-center gap-2">
                    {[t("aiSuggestion1"), t("aiSuggestion2"), t("aiSuggestion3")].map((suggestion) => (
                        <Button
                            key={suggestion}
                            variant="outline"
                            size="sm"
                            className="text-xs"
                            onClick={() => sendAiTask(suggestion)}
                        >
                            {suggestion}
                        </Button>
                    ))}
                </div>
            </div>
        </div>
    );
}
