"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
    Receipt, Plus, Check, X, Loader2, Download, Upload, Trash2, RefreshCw, Camera, Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import type { Expense, Employee } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageContainer } from "@/components/shared/PageContainer";

const CATEGORIES = [
    { value: "viaje", label: "Viaje / Transporte" },
    { value: "dieta", label: "Dieta / Manutención" },
    { value: "alojamiento", label: "Alojamiento" },
    { value: "material", label: "Material de oficina" },
    { value: "formacion", label: "Formación" },
    { value: "otro", label: "Otro" },
];

const STATUS_TABS = [
    { value: "", label: "Todos" },
    { value: "pending", label: "Pendientes" },
    { value: "approved", label: "Aprobados" },
    { value: "reimbursed", label: "Reembolsados" },
    { value: "rejected", label: "Rechazados" },
];

const STATUS_STYLE: Record<string, string> = {
    pending:    "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved:   "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected:   "bg-red-500/10 text-red-400 border-red-500/20",
    reimbursed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};
const STATUS_LABEL: Record<string, string> = {
    pending: "Pendiente", approved: "Aprobado", rejected: "Rechazado", reimbursed: "Reembolsado",
};

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });

type ExpenseForm = {
    employee_id: string;
    amount: string;
    category: string;
    description: string;
    date: string;
    notes: string;
};

const emptyForm = (): ExpenseForm => ({
    employee_id: "",
    amount: "",
    category: "viaje",
    description: "",
    date: new Date().toISOString().slice(0, 10),
    notes: "",
});

export default function GastosPage() {
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [statusTab, setStatusTab] = useState("");
    const [isLoading, setIsLoading] = useState(true);

    const [showCreate, setShowCreate] = useState(false);
    const [form, setForm] = useState<ExpenseForm>(emptyForm());
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const [actionId, setActionId] = useState<string | null>(null);
    const [uploadingId, setUploadingId] = useState<string | null>(null);
    const [scanning, setScanning] = useState(false);
    const [scanConfidence, setScanConfidence] = useState<number | null>(null);
    const [scanMerchant, setScanMerchant] = useState<string | null>(null);
    const toast = useToastStore();

    const handleScanTicket = useCallback(async (file: File) => {
        if (!file.type.startsWith("image/")) {
            toast.error("Solo se aceptan imágenes (JPG, PNG, WEBP).");
            return;
        }
        setScanning(true);
        setScanConfidence(null);
        setScanMerchant(null);
        try {
            const draft = await api.hr.expenses.scanReceipt(file);
            const employeeId = employees.length > 0 ? employees[0].id : "";
            setForm({
                employee_id: employeeId,
                amount: draft.amount.toFixed(2),
                category: draft.category || "otro",
                description: draft.description || `Ticket de ${draft.merchant}`,
                date: draft.date,
                notes: [
                    draft.merchant && `Comercio: ${draft.merchant}`,
                    draft.merchant_nif && `NIF: ${draft.merchant_nif}`,
                    draft.vat_amount != null && `IVA: ${draft.vat_amount.toFixed(2)} €${draft.vat_rate ? ` (${draft.vat_rate}%)` : ""}`,
                ].filter(Boolean).join(" · "),
            });
            setScanConfidence(draft.confidence);
            setScanMerchant(draft.merchant);
            setFormError(null);
            setShowCreate(true);
            toast.success(`Ticket leído: ${draft.merchant} · ${draft.amount.toFixed(2)} €`);
        } catch (e) {
            const msg = e instanceof Error ? e.message : "No se pudo leer el ticket";
            toast.error(msg);
        } finally {
            setScanning(false);
        }
    }, [employees, toast]);

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            const [exp, emp] = await Promise.all([
                api.hr.expenses.list(statusTab || undefined),
                api.hr.employees.list(),
            ]);
            setExpenses(exp);
            setEmployees(emp);
        } catch { /* noop */ }
        finally { setIsLoading(false); }
    }, [statusTab]);

    useEffect(() => { load(); }, [load]);

    const pendingTotal = expenses.filter((e) => e.status === "pending").reduce((s, e) => s + e.amount, 0);
    const pendingCount = expenses.filter((e) => e.status === "pending").length;
    const approvedTotal = expenses.filter((e) => e.status === "approved").reduce((s, e) => s + e.amount, 0);

    const handleCreate = async () => {
        if (!form.employee_id || !form.amount || !form.description || !form.date) {
            setFormError("Completa los campos obligatorios."); return;
        }
        setSaving(true); setFormError(null);
        try {
            await api.hr.expenses.create({
                employee_id: form.employee_id,
                amount: parseFloat(form.amount),
                category: form.category,
                description: form.description,
                date: form.date,
                notes: form.notes || undefined,
            });
            setShowCreate(false);
            setForm(emptyForm());
            await load();
        } catch { setFormError("Error al crear el gasto."); }
        finally { setSaving(false); }
    };

    const handleAction = async (id: string, action: "approve" | "reject" | "reimburse" | "delete") => {
        setActionId(id);
        try {
            if (action === "approve") await api.hr.expenses.approve(id);
            else if (action === "reject") await api.hr.expenses.reject(id);
            else if (action === "reimburse") await api.hr.expenses.reimburse(id);
            else await api.hr.expenses.delete(id);
            await load();
        } catch { /* noop */ }
        finally { setActionId(null); }
    };

    const handleUploadReceipt = async (id: string, file: File) => {
        setUploadingId(id);
        try {
            await api.hr.expenses.uploadReceipt(id, file);
            await load();
        } catch { /* noop */ }
        finally { setUploadingId(null); }
    };

    return (
        <PageContainer width="full">
            <PageHeader
                title="Gestión de Gastos"
                description="Aprueba y reembolsa dietas y gastos de empleados."
                icon={Receipt}
                actions={
                    <div className="flex items-center gap-2">
                        <label className={`inline-flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 px-3 h-9 text-sm font-medium cursor-pointer transition-colors ${scanning ? "opacity-50 pointer-events-none" : ""}`}>
                            {scanning
                                ? <><Loader2 className="h-4 w-4 animate-spin" /> Leyendo ticket…</>
                                : <><Sparkles className="h-4 w-4" /> Escanear ticket</>}
                            <input
                                type="file"
                                accept="image/png,image/jpeg,image/webp"
                                capture="environment"
                                className="hidden"
                                onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) handleScanTicket(f);
                                    e.target.value = "";
                                }}
                            />
                        </label>
                        <Button onClick={() => { setShowCreate(true); setFormError(null); setForm(emptyForm()); setScanConfidence(null); setScanMerchant(null); }}>
                            <Plus className="mr-2 h-4 w-4" /> Nuevo gasto
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <KpiCard title="Pendientes de aprobar" value={pendingCount} icon={Receipt} />
                <KpiCard title="Importe pendiente" value={fmt(pendingTotal)} icon={Receipt} />
                <KpiCard title="Aprobado (pendiente reembolso)" value={fmt(approvedTotal)} icon={Receipt} />
            </div>

            {/* Status tabs */}
            <div className="flex gap-1 border-b border-border">
                {STATUS_TABS.map((t) => (
                    <button
                        key={t.value}
                        onClick={() => setStatusTab(t.value)}
                        className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                            statusTab === t.value
                                ? "border-primary text-foreground"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Table */}
            {isLoading ? (
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                </div>
            ) : expenses.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <Receipt className="w-8 h-8 opacity-30" />
                    <p className="text-sm">No hay gastos en esta categoría</p>
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/30 text-muted-foreground">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium">Empleado</th>
                                <th className="text-left px-4 py-3 font-medium">Categoría</th>
                                <th className="text-left px-4 py-3 font-medium">Descripción</th>
                                <th className="text-left px-4 py-3 font-medium">Fecha</th>
                                <th className="text-right px-4 py-3 font-medium">Importe</th>
                                <th className="text-left px-4 py-3 font-medium">Estado</th>
                                <th className="text-left px-4 py-3 font-medium">Recibo</th>
                                <th className="text-right px-4 py-3 font-medium">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {expenses.map((exp) => (
                                <tr key={exp.id} className="bg-card hover:bg-muted/20 transition-colors">
                                    <td className="px-4 py-3 font-medium text-foreground">{exp.employee_name ?? "—"}</td>
                                    <td className="px-4 py-3 text-muted-foreground capitalize">
                                        {CATEGORIES.find((c) => c.value === exp.category)?.label ?? exp.category}
                                    </td>
                                    <td className="px-4 py-3 text-muted-foreground max-w-[200px] truncate" title={exp.description}>
                                        {exp.description}
                                    </td>
                                    <td className="px-4 py-3 text-muted-foreground">{fmtDate(exp.date)}</td>
                                    <td className="px-4 py-3 text-right font-semibold text-foreground tabular-nums">
                                        {fmt(exp.amount)}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLE[exp.status] ?? ""}`}>
                                            {STATUS_LABEL[exp.status] ?? exp.status}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        {exp.receipt_filename ? (
                                            <button
                                                onClick={() => api.hr.expenses.downloadReceipt(exp.id, exp.receipt_filename!)}
                                                className="flex items-center gap-1 text-xs text-primary hover:underline"
                                                title={exp.receipt_filename}
                                            >
                                                <Download className="w-3 h-3" />
                                                Ver
                                            </button>
                                        ) : (
                                            <label className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
                                                {uploadingId === exp.id
                                                    ? <Loader2 className="w-3 h-3 animate-spin" />
                                                    : <Upload className="w-3 h-3" />}
                                                <span>Subir</span>
                                                <input
                                                    type="file"
                                                    className="hidden"
                                                    accept=".pdf,.jpg,.jpeg,.png"
                                                    onChange={(e) => {
                                                        const f = e.target.files?.[0];
                                                        if (f) handleUploadReceipt(exp.id, f);
                                                    }}
                                                />
                                            </label>
                                        )}
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex items-center justify-end gap-1">
                                            {exp.status === "pending" && (
                                                <>
                                                    <Button
                                                        variant="ghost" size="icon"
                                                        className="h-7 w-7 text-emerald-500 hover:text-emerald-400"
                                                        title="Aprobar"
                                                        disabled={actionId === exp.id}
                                                        onClick={() => handleAction(exp.id, "approve")}
                                                     aria-label="Aprobar">
                                                        {actionId === exp.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Check className="h-3.5 w-3.5" aria-hidden="true" />}
                                                    </Button>
                                                    <Button
                                                        variant="ghost" size="icon"
                                                        className="h-7 w-7 text-red-500 hover:text-red-400"
                                                        title="Rechazar"
                                                        disabled={actionId === exp.id}
                                                        onClick={() => handleAction(exp.id, "reject")}
                                                     aria-label="Rechazar">
                                                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                                                    </Button>
                                                </>
                                            )}
                                            {exp.status === "approved" && (
                                                <Button
                                                    variant="ghost" size="icon"
                                                    className="h-7 w-7 text-blue-500 hover:text-blue-400"
                                                    title="Marcar reembolsado"
                                                    disabled={actionId === exp.id}
                                                    onClick={() => handleAction(exp.id, "reimburse")}
                                                 aria-label="Marcar reembolsado">
                                                    {actionId === exp.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
                                                </Button>
                                            )}
                                            <Button
                                                variant="ghost" size="icon"
                                                className="h-7 w-7 text-destructive hover:text-destructive"
                                                title="Eliminar"
                                                disabled={actionId === exp.id}
                                                onClick={() => handleAction(exp.id, "delete")}
                                             aria-label="Eliminar">
                                                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Create modal */}
            <Dialog open={showCreate} onOpenChange={setShowCreate}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{scanConfidence !== null ? "Revisar gasto escaneado" : "Nuevo gasto"}</DialogTitle>
                        {scanConfidence !== null && (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                                <Sparkles className="w-3.5 h-3.5 text-primary" />
                                {scanMerchant ? `Detectado: ${scanMerchant}.` : "Datos extraídos del ticket."}
                                <span className={`ml-1 font-medium ${scanConfidence >= 0.8 ? "text-emerald-500" : scanConfidence >= 0.5 ? "text-amber-500" : "text-rose-500"}`}>
                                    Confianza {(scanConfidence * 100).toFixed(0)}%
                                </span>
                                <span className="text-muted-foreground/70">· revisa antes de guardar</span>
                            </div>
                        )}
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <Label>Empleado *</Label>
                            <Select value={form.employee_id} onValueChange={(v) => setForm((f) => ({ ...f, employee_id: v }))}>
                                <SelectTrigger><SelectValue placeholder="Seleccionar empleado…" /></SelectTrigger>
                                <SelectContent>
                                    {employees.map((e) => (
                                        <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label>Importe (€) *</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    value={form.amount}
                                    onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                                    placeholder="0.00"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label>Fecha *</Label>
                                <Input
                                    type="date"
                                    value={form.date}
                                    onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                                />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Categoría *</Label>
                            <Select value={form.category} onValueChange={(v) => setForm((f) => ({ ...f, category: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {CATEGORIES.map((c) => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Descripción *</Label>
                            <Input
                                value={form.description}
                                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                                placeholder="Ej: Viaje Madrid-Barcelona AVE"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Notas</Label>
                            <textarea
                                value={form.notes}
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setForm((f) => ({ ...f, notes: e.target.value }))}
                                placeholder="Opcional…"
                                rows={2}
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                            />
                        </div>
                        {formError && <p className="text-xs text-destructive">{formError}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowCreate(false)} disabled={saving}>Cancelar</Button>
                        <Button onClick={handleCreate} disabled={saving}>
                            {saving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Guardando…</> : "Crear gasto"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </PageContainer>
    );
}
