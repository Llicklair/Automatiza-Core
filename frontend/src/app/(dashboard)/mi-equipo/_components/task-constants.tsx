import React from "react";
import { Clock, Bot, Loader2, AlertCircle, CheckCircle2, X } from "lucide-react";
import type { Task } from "@/lib/api";

type Translator = (key: string) => string;

export const STATUS_COLOR: Record<string, string> = {
    pending: "text-muted-foreground bg-muted border-border",
    planning: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    executing: "text-primary bg-primary/10 border-primary/20",
    awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    done: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    failed: "text-red-400 bg-red-500/10 border-red-500/20",
    cancelled: "text-muted-foreground bg-accent border-border",
};

export const getStatusLabel = (t: Translator): Record<string, string> => ({
    pending: t("taskConstants.statusPending"),
    planning: t("taskConstants.statusPlanning"),
    executing: t("taskConstants.statusExecuting"),
    awaiting_approval: t("taskConstants.statusAwaitingApproval"),
    done: t("taskConstants.statusDone"),
    failed: t("taskConstants.statusFailed"),
    cancelled: t("taskConstants.statusCancelled"),
});

export const STATUS_ICON: Record<string, React.ReactNode> = {
    pending: <Clock className="w-3 h-3" />,
    planning: <Bot className="w-3 h-3" />,
    executing: <Loader2 className="w-3 h-3 animate-spin" />,
    awaiting_approval: <AlertCircle className="w-3 h-3" />,
    done: <CheckCircle2 className="w-3 h-3" />,
    failed: <X className="w-3 h-3" />,
    cancelled: <X className="w-3 h-3" />,
};

export const getChatOption = (t: Translator) => ({
    value: "chat",
    label: `\u{1F4AC} ${t("taskConstants.chatLabel")}`,
    desc: t("taskConstants.chatDesc"),
});

export const getCoordinatorOption = (t: Translator) => ({
    value: "coordinator",
    label: `\u{1F9E0} ${t("taskConstants.coordinatorLabel")}`,
    desc: t("taskConstants.coordinatorDesc"),
});

export const getDomainOptions = (t: Translator) => [
    { value: "billing", label: `\u{1F4B0} ${t("taskConstants.domainBillingLabel")}`, desc: t("taskConstants.domainBillingDesc") },
    { value: "documents", label: `\u{1F4C4} ${t("taskConstants.domainDocumentsLabel")}`, desc: t("taskConstants.domainDocumentsDesc") },
    { value: "hr", label: `\u{1F465} ${t("taskConstants.domainHrLabel")}`, desc: t("taskConstants.domainHrDesc") },
    { value: "compliance", label: `⚖️ ${t("taskConstants.domainComplianceLabel")}`, desc: t("taskConstants.domainComplianceDesc") },
    { value: "banking", label: `\u{1F3E6} ${t("taskConstants.domainBankingLabel")}`, desc: t("taskConstants.domainBankingDesc") },
    { value: "crm", label: `\u{1F91D} ${t("taskConstants.domainCrmLabel")}`, desc: t("taskConstants.domainCrmDesc") },
    { value: "excel", label: `\u{1F4CA} ${t("taskConstants.domainExcelLabel")}`, desc: t("taskConstants.domainExcelDesc") },
    { value: "email", label: `\u{1F4E7} ${t("taskConstants.domainEmailLabel")}`, desc: t("taskConstants.domainEmailDesc") },
];

export const getAllDomainOptions = (t: Translator) => [
    getChatOption(t),
    getCoordinatorOption(t),
    ...getDomainOptions(t),
];

export function getChatResponse(task: Task): string | null {
    if (!Array.isArray(task.agent_results)) return null;
    const results = task.agent_results as any[];
    // Buscar resumen conversacional o respuesta de chat
    for (let i = results.length - 1; i >= 0; i--) {
        const r = results[i];
        if ((r.agent === "chat" || r.agent === "summary") && r.output?.action === "chat_response" && r.output?.response) {
            return r.output.response;
        }
    }
    return null;
}
