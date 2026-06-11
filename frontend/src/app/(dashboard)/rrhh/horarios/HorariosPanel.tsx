"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Clock, Loader2, Save, Download, Mail, Send, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { useToastStore } from "@/stores/toast";
import { api } from "@/lib/api";
import {
    useHorarios, DAYS, calcWeeklyHours,
    buildScheduleHTML,
} from "./_hooks/useHorarios";

export function HorariosPanel() {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    const { employees, grids, saving, isLoading, updateCell, handleSave, applyAISuggestions } = useHorarios();
    const toast = useToastStore();

    const [showAI, setShowAI] = useState(false);
    const [aiInstruction, setAiInstruction] = useState("");
    const [aiLoading, setAiLoading] = useState(false);

    async function handleAISuggest(e: React.FormEvent) {
        e.preventDefault();
        if (!aiInstruction.trim()) { toast.error(t("horarios.toasts.writeInstruction")); return; }
        setAiLoading(true);
        try {
            const res = await api.hr.schedules.aiSuggest(aiInstruction.trim());
            if (res.suggestions.length === 0) {
                toast.error(t("horarios.toasts.noProposals"));
                return;
            }
            applyAISuggestions(res.suggestions);
            toast.success(
                res.rationale
                    ? t("horarios.toasts.proposalAppliedRationale", { rationale: res.rationale })
                    : t("horarios.toasts.proposalAppliedCount", { n: res.suggestions.length })
            );
            setShowAI(false);
            setAiInstruction("");
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("horarios.toasts.proposalError"));
        } finally {
            setAiLoading(false);
        }
    }

    const [showEmail, setShowEmail] = useState(false);
    const [emailForm, setEmailForm] = useState(() => ({
        to: "",
        subject: t("horarios.emailModal.defaultSubject"),
        message: t("horarios.emailModal.defaultMessage"),
    }));
    const [sending, setSending] = useState(false);

    async function handleExport(format: "xlsx" | "pdf") {
        if (employees.length === 0) {
            toast.error(t("horarios.toasts.noEmployeesToExport"));
            return;
        }
        try {
            await api.hr.schedules.export(format);
            toast.success(t("horarios.toasts.exported"));
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("horarios.toasts.exportError"));
        }
    }

    async function handleSendEmail(e: React.FormEvent) {
        e.preventDefault();
        if (!emailForm.to.trim()) { toast.error(t("horarios.toasts.missingRecipient")); return; }
        setSending(true);
        try {
            const html = buildScheduleHTML(employees, grids, {
                employee: t("horarios.email.tableEmployee"),
                days: DAYS.map((d) => t(d.fullKey)),
                hoursPerWeek: t("horarios.email.tableHoursPerWeek"),
            });
            const body = `${emailForm.message}\n\n${html}`;
            await api.messaging.email.send(emailForm.to.trim(), emailForm.subject, body);
            toast.success(t("horarios.toasts.emailSent"));
            setShowEmail(false);
        } catch (err) {
            toast.error(err instanceof Error ? err.message : t("horarios.toasts.sendError"));
        } finally {
            setSending(false);
        }
    }

    if (isLoading) {
        return (
            <div className="p-8 flex items-center justify-center text-muted-foreground gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> {t("horarios.loading")}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <PageHeader
                    title={t("horarios.title")}
                    description={t("horarios.description")}
                    icon={Clock}
                />
                {employees.length > 0 && (
                    <div className="flex items-center gap-2">
                        <Button size="sm" onClick={() => setShowAI(true)}>
                            <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                            {t("horarios.aiAssistant")}
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleExport("xlsx")}>
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            {t("horarios.exportExcel")}
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleExport("pdf")}>
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            {t("horarios.exportPdf")}
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowEmail(true)}>
                            <Mail className="w-3.5 h-3.5 mr-1.5" />
                            {t("horarios.sendByEmail")}
                        </Button>
                    </div>
                )}
            </div>

            {employees.length === 0 && (
                <div className="text-center text-muted-foreground py-12 border-2 border-dashed border-border rounded-xl">
                    {t("horarios.noActiveEmployees")}
                </div>
            )}

            {employees.length > 0 && (
                <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-foreground flex items-start gap-3">
                    <Clock className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <p className="font-medium">{t("horarios.howToEditTitle")}</p>
                        <p className="text-muted-foreground text-xs mt-0.5">
                            {t.rich("horarios.howToEditDescription", {
                                b: (chunks) => <span className="text-foreground font-medium">{chunks}</span>,
                            })}
                        </p>
                    </div>
                </div>
            )}

            <div className="space-y-4">
                {employees.map((emp) => {
                    const grid = grids[emp.id] ?? {};
                    const weeklyHours = calcWeeklyHours(grid);
                    const applyWeekdays = () => {
                        for (let i = 0; i < 5; i++) {
                            updateCell(emp.id, i, "active", true);
                            updateCell(emp.id, i, "start_time", "09:00");
                            updateCell(emp.id, i, "end_time", "17:00");
                        }
                        updateCell(emp.id, 5, "active", false);
                        updateCell(emp.id, 6, "active", false);
                    };
                    return (
                        <Card key={emp.id}>
                            <CardContent className="p-5">
                                <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-foreground border border-border">
                                            {emp.name.substring(0, 2).toUpperCase()}
                                        </div>
                                        <div>
                                            <p className="font-medium text-foreground text-sm">{emp.name}</p>
                                            <p className="text-xs text-muted-foreground">{emp.role || emp.department || "—"}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <Badge variant="secondary" className="text-xs">
                                            {t("horarios.weeklyHours", { hours: weeklyHours.toFixed(1) })}
                                        </Badge>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            className="text-xs h-8 text-muted-foreground hover:text-foreground"
                                            onClick={applyWeekdays}
                                            title={t("horarios.weekdaysPresetTitle")}
                                        >
                                            {t("horarios.weekdaysPreset")}
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            disabled={saving[emp.id]}
                                            onClick={() => handleSave(emp.id)}
                                        >
                                            {saving[emp.id]
                                                ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                                                : <Save className="w-3.5 h-3.5 mr-1.5" />}
                                            {tc("save")}
                                        </Button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-7 gap-2">
                                    {DAYS.map((d, i) => {
                                        const day = grid[i] ?? { start_time: "09:00", end_time: "17:00", active: false };
                                        const cellId = `cell-${emp.id}-${i}`;
                                        return (
                                            <div
                                                key={i}
                                                className={`flex flex-col gap-1.5 rounded-lg border p-2 transition-colors ${
                                                    day.active
                                                        ? "border-primary/30 bg-primary/5"
                                                        : "border-dashed border-border bg-muted/20"
                                                }`}
                                            >
                                                <label
                                                    htmlFor={cellId}
                                                    className="flex items-center justify-between cursor-pointer select-none gap-1"
                                                    title={day.active ? t("horarios.dayActiveTitle") : t("horarios.dayInactiveTitle")}
                                                >
                                                    <span className={`text-xs font-semibold ${day.active ? "text-foreground" : "text-muted-foreground"}`}>{t(d.shortKey)}</span>
                                                    <input
                                                        id={cellId}
                                                        type="checkbox"
                                                        checked={day.active}
                                                        onChange={(e) => updateCell(emp.id, i, "active", e.target.checked)}
                                                        className="h-4 w-4 rounded accent-primary cursor-pointer"
                                                    />
                                                </label>
                                                {day.active ? (
                                                    <>
                                                        <Input
                                                            type="time"
                                                            value={day.start_time}
                                                            onChange={(e) => updateCell(emp.id, i, "start_time", e.target.value)}
                                                            className="h-8 text-xs px-2"
                                                        />
                                                        <Input
                                                            type="time"
                                                            value={day.end_time}
                                                            onChange={(e) => updateCell(emp.id, i, "end_time", e.target.value)}
                                                            className="h-8 text-xs px-2"
                                                        />
                                                    </>
                                                ) : (
                                                    <div className="flex-1 flex items-center justify-center text-[11px] uppercase tracking-wider text-muted-foreground/60 py-1">
                                                        {t("horarios.dayOff")}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {/* Send by email modal */}
            <Dialog open={showEmail} onOpenChange={setShowEmail}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{t("horarios.emailModal.title")}</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleSendEmail} className="space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="hr-to">{t("horarios.emailModal.to")}</Label>
                            <Input
                                id="hr-to"
                                type="email"
                                required
                                value={emailForm.to}
                                onChange={(e) => setEmailForm((f) => ({ ...f, to: e.target.value }))}
                                placeholder={t("horarios.emailModal.toPlaceholder")}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="hr-subject">{t("horarios.emailModal.subject")}</Label>
                            <Input
                                id="hr-subject"
                                value={emailForm.subject}
                                onChange={(e) => setEmailForm((f) => ({ ...f, subject: e.target.value }))}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="hr-msg">{t("horarios.emailModal.message")}</Label>
                            <textarea
                                id="hr-msg"
                                rows={3}
                                value={emailForm.message}
                                onChange={(e) => setEmailForm((f) => ({ ...f, message: e.target.value }))}
                                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                            />
                            <p className="text-[11px] text-muted-foreground">
                                {t("horarios.emailModal.tableNote")}
                            </p>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowEmail(false)} disabled={sending}>
                                {tc("cancel")}
                            </Button>
                            <Button type="submit" disabled={sending}>
                                {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Send className="w-3.5 h-3.5 mr-1.5" />}
                                {t("horarios.emailModal.send")}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* AI assistant modal */}
            <Dialog open={showAI} onOpenChange={setShowAI}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-primary" />
                            {t("horarios.aiModal.title")}
                        </DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleAISuggest} className="space-y-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="ai-inst">{t("horarios.aiModal.instruction")}</Label>
                            <textarea
                                id="ai-inst"
                                rows={4}
                                required
                                value={aiInstruction}
                                onChange={(e) => setAiInstruction(e.target.value)}
                                placeholder={t("horarios.aiModal.placeholder")}
                                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                            />
                            <p className="text-[11px] text-muted-foreground">
                                {t.rich("horarios.aiModal.note", {
                                    b: (chunks) => <strong>{chunks}</strong>,
                                })}
                            </p>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowAI(false)} disabled={aiLoading}>
                                {tc("cancel")}
                            </Button>
                            <Button type="submit" disabled={aiLoading}>
                                {aiLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Sparkles className="w-3.5 h-3.5 mr-1.5" />}
                                {t("horarios.aiModal.generateProposal")}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
