"use client";
import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import { Umbrella, Plus, Check, X, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    useVacaciones,
    LEAVE_TYPE_LABEL_KEYS,
    STATUS_LABEL_KEYS,
    type StatusFilter,
} from "./_hooks/useVacaciones";

// I18N — config estructural + labelKey/emptyKey; el componente traduce en render.
const STATUS_TABS: { labelKey: string; emptyKey: string; value: StatusFilter }[] = [
    { labelKey: "vacaciones.tabs.all", emptyKey: "vacaciones.empty.all", value: "all" },
    { labelKey: "vacaciones.tabs.pending", emptyKey: "vacaciones.empty.pending", value: "pending" },
    { labelKey: "vacaciones.tabs.approved", emptyKey: "vacaciones.empty.approved", value: "approved" },
    { labelKey: "vacaciones.tabs.rejected", emptyKey: "vacaciones.empty.rejected", value: "rejected" },
];

const STATUS_BADGE: Record<string, string> = {
    pending: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-red-500/10 text-red-400 border-red-500/20",
};

function daysBetween(start: string, end: string) {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    return Math.round(ms / 86400000) + 1;
}

export function VacacionesPanel() {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    const { fmtDate } = useFormat();
    const {
        requests,
        employees,
        loading,
        statusFilter,
        setStatusFilter,
        showModal,
        openModal,
        setShowModal,
        form,
        setForm,
        saving,
        error,
        handleCreate,
        handleApprove,
        handleReject,
        handleDelete,
        getEmployee,
    } = useVacaciones();

    const formatDate = (d: string) => fmtDate(d, { day: "2-digit", month: "short", year: "numeric" });
    const activeTab = STATUS_TABS.find((tab) => tab.value === statusFilter) ?? STATUS_TABS[0];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                        <Umbrella className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-foreground tracking-tight">{t("vacaciones.title")}</h1>
                        <p className="text-xs text-muted-foreground">{t("vacaciones.description")}</p>
                    </div>
                </div>
                <Button onClick={openModal} size="sm" className="gap-2">
                    <Plus className="w-4 h-4" />
                    {t("vacaciones.newRequest")}
                </Button>
            </div>

            {/* Status filter tabs */}
            <div className="flex gap-1 border-b border-border">
                {STATUS_TABS.map((tab) => (
                    <button
                        key={tab.value}
                        onClick={() => setStatusFilter(tab.value)}
                        className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                            statusFilter === tab.value
                                ? "border-primary text-foreground"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        {t(tab.labelKey)}
                    </button>
                ))}
            </div>

            {/* Table */}
            {loading ? (
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">{tc("loading")}</div>
            ) : requests.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <Umbrella className="w-8 h-8 opacity-30" />
                    <p className="text-sm">{t(activeTab.emptyKey)}</p>
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/30 text-muted-foreground">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.employee")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.type")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.from")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.to")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.days")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.status")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("vacaciones.table.notes")}</th>
                                <th className="px-4 py-3" />
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {requests.map((req) => {
                                const emp = getEmployee(req.employee_id);
                                return (
                                    <tr key={req.id} className="bg-card hover:bg-muted/20 transition-colors">
                                        <td className="px-4 py-3 font-medium text-foreground">
                                            {emp?.name ?? req.employee_id.slice(0, 8)}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {LEAVE_TYPE_LABEL_KEYS[req.leave_type] ? t(LEAVE_TYPE_LABEL_KEYS[req.leave_type]) : req.leave_type}
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">{formatDate(req.start_date)}</td>
                                        <td className="px-4 py-3 text-muted-foreground">{formatDate(req.end_date)}</td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {t("vacaciones.daysShort", { n: daysBetween(req.start_date, req.end_date) })}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[req.status] ?? ""}`}>
                                                {STATUS_LABEL_KEYS[req.status] ? t(STATUS_LABEL_KEYS[req.status]) : req.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground text-xs max-w-[160px] truncate">
                                            {req.notes ?? "—"}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-1 justify-end">
                                                {req.status === "pending" && (
                                                    <>
                                                        <button
                                                            onClick={() => handleApprove(req.id)}
                                                            title={t("common.approve")}
                                                            className="p-1.5 rounded-lg hover:bg-emerald-500/10 text-muted-foreground hover:text-emerald-400 transition-colors"
                                                         aria-label={t("common.approve")}>
                                                            <Check className="w-4 h-4" aria-hidden="true" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleReject(req.id)}
                                                            title={t("vacaciones.reject")}
                                                            className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                                                         aria-label={t("vacaciones.reject")}>
                                                            <X className="w-4 h-4" aria-hidden="true" />
                                                        </button>
                                                    </>
                                                )}
                                                <button
                                                    onClick={() => handleDelete(req.id)}
                                                    title={tc("delete")}
                                                    className="p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                                                 aria-label={tc("delete")}>
                                                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* New request modal */}
            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{t("vacaciones.modal.title")}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <Label>{t("vacaciones.modal.employee")}</Label>
                            <Select
                                value={form.employee_id}
                                onValueChange={(v) => setForm((f) => ({ ...f, employee_id: v }))}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={t("vacaciones.modal.selectEmployee")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {employees.map((e) => (
                                        <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("vacaciones.modal.leaveType")}</Label>
                            <Select
                                value={form.leave_type}
                                onValueChange={(v) => setForm((f) => ({ ...f, leave_type: v }))}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {Object.entries(LEAVE_TYPE_LABEL_KEYS).map(([k, labelKey]) => (
                                        <SelectItem key={k} value={k}>{t(labelKey)}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label>{t("vacaciones.modal.startDate")}</Label>
                                <Input
                                    type="date"
                                    value={form.start_date}
                                    onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label>{t("vacaciones.modal.endDate")}</Label>
                                <Input
                                    type="date"
                                    value={form.end_date}
                                    onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                                />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label>{t("vacaciones.table.notes")}</Label>
                            <Input
                                value={form.notes}
                                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                                placeholder={t("vacaciones.modal.notesPlaceholder")}
                            />
                        </div>
                        {error && <p className="text-xs text-destructive">{error}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowModal(false)} disabled={saving}>
                            {tc("cancel")}
                        </Button>
                        <Button onClick={handleCreate} disabled={saving}>
                            {saving ? t("vacaciones.modal.saving") : t("vacaciones.modal.create")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
