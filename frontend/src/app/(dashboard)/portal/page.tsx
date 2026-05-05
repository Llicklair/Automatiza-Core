"use client";
import { useState, useEffect } from "react";
import {
    User, Briefcase, FileText, Umbrella, Plus, Download,
    Check, Clock, X, Banknote, Receipt, Loader2, Upload, Eye,
    Play, StopCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { PortalData, LeaveRequest, Payroll, Expense, Employee } from "@/lib/api";
import { useUserRole } from "@/hooks/useUserRole";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Tab = "ficha" | "nominas" | "vacaciones" | "gastos";

const STATUS_BADGE: Record<string, string> = {
    pending:  "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    draft:    "bg-muted text-muted-foreground border-border",
    paid:     "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

const PAYROLL_LABEL: Record<string, string> = { draft: "Borrador", approved: "Aprobada", paid: "Pagada" };
const LEAVE_LABEL:   Record<string, string> = { pending: "Pendiente", approved: "Aprobada", rejected: "Rechazada" };
const LEAVE_TYPES = [
    { value: "vacaciones", label: "Vacaciones" },
    { value: "baja_medica", label: "Baja médica" },
    { value: "excedencia", label: "Excedencia" },
    { value: "otros", label: "Otros" },
];

const EXPENSE_CATEGORIES = [
    { value: "viaje", label: "Viaje / Transporte" },
    { value: "dieta", label: "Dieta / Manutención" },
    { value: "alojamiento", label: "Alojamiento" },
    { value: "material", label: "Material de oficina" },
    { value: "formacion", label: "Formación" },
    { value: "otro", label: "Otro" },
];

const EXPENSE_STATUS_LABEL: Record<string, string> = {
    pending: "Pendiente", approved: "Aprobado", rejected: "Rechazado", reimbursed: "Reembolsado",
};
const EXPENSE_STATUS_STYLE: Record<string, string> = {
    pending:    "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved:   "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected:   "bg-red-500/10 text-red-400 border-red-500/20",
    reimbursed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

function fmt(d: string) {
    return new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}
function currency(n: number) {
    return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
}

export default function PortalPage() {
    const role = useUserRole();
    const isAdmin = role === "admin";

    const [tab, setTab] = useState<Tab>("ficha");
    const [data, setData] = useState<PortalData | null>(null);
    const [loading, setLoading] = useState(true);

    // Admin "view as employee" mode
    const [employeesList, setEmployeesList] = useState<Employee[]>([]);
    const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>("");
    const readOnly = !!data?.read_only;

    // Clock in/out
    const [clockBusy, setClockBusy] = useState(false);
    const [clockError, setClockError] = useState<string | null>(null);

    // Leave request modal
    const [showLeave, setShowLeave] = useState(false);
    const [leaveForm, setLeaveForm] = useState({ leave_type: "vacaciones", start_date: "", end_date: "", notes: "" });
    const [saving, setSaving] = useState(false);
    const [leaveError, setLeaveError] = useState<string | null>(null);

    // Gastos
    const [myExpenses, setMyExpenses] = useState<Expense[]>([]);
    const [showExpense, setShowExpense] = useState(false);
    const [expenseForm, setExpenseForm] = useState({ amount: "", category: "viaje", description: "", date: new Date().toISOString().slice(0, 10), notes: "" });
    const [expenseSaving, setExpenseSaving] = useState(false);
    const [expenseError, setExpenseError] = useState<string | null>(null);
    const [uploadingReceiptId, setUploadingReceiptId] = useState<string | null>(null);

    const load = async (asEmployeeId?: string) => {
        setLoading(true);
        try {
            const portalData = asEmployeeId
                ? await api.portal.meAs(asEmployeeId)
                : await api.portal.me();
            setData(portalData);
            if (portalData.employee) {
                try {
                    const exps = await api.hr.expenses.list(undefined, portalData.employee.id);
                    setMyExpenses(exps);
                } catch { /* noop */ }
            } else {
                setMyExpenses([]);
            }
        } catch { /* noop */ }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    // Admin: load employees list for the "view as" selector
    useEffect(() => {
        if (!isAdmin) return;
        (async () => {
            try {
                const list = await api.hr.employees.list();
                setEmployeesList(list);
            } catch { /* noop */ }
        })();
    }, [isAdmin]);

    const handleSelectEmployee = (empId: string) => {
        setSelectedEmployeeId(empId);
        load(empId || undefined);
    };

    const handleClockIn = async () => {
        setClockBusy(true);
        setClockError(null);
        try {
            await api.portal.clockIn();
            await load();
        } catch (e) {
            setClockError(e instanceof Error ? e.message : "No se pudo fichar la entrada");
        } finally {
            setClockBusy(false);
        }
    };

    const handleClockOut = async () => {
        setClockBusy(true);
        setClockError(null);
        try {
            await api.portal.clockOut();
            await load();
        } catch (e) {
            setClockError(e instanceof Error ? e.message : "No se pudo fichar la salida");
        } finally {
            setClockBusy(false);
        }
    };

    const formatClockTime = (iso: string | null | undefined) => {
        if (!iso) return "—";
        return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
    };

    const DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

    const handleSubmitExpense = async () => {
        if (!expenseForm.amount || !expenseForm.description || !expenseForm.date) {
            setExpenseError("Completa los campos obligatorios."); return;
        }
        if (!emp) return;
        setExpenseSaving(true); setExpenseError(null);
        try {
            await api.hr.expenses.create({
                employee_id: emp.id,
                amount: parseFloat(expenseForm.amount),
                category: expenseForm.category,
                description: expenseForm.description,
                date: expenseForm.date,
                notes: expenseForm.notes || undefined,
            });
            setShowExpense(false);
            setExpenseForm({ amount: "", category: "viaje", description: "", date: new Date().toISOString().slice(0, 10), notes: "" });
            await load();
        } catch { setExpenseError("Error al enviar el gasto."); }
        finally { setExpenseSaving(false); }
    };

    const handleUploadReceipt = async (expId: string, file: File) => {
        setUploadingReceiptId(expId);
        try {
            await api.hr.expenses.uploadReceipt(expId, file);
            await load();
        } catch { /* noop */ }
        finally { setUploadingReceiptId(null); }
    };

    const handleSubmitLeave = async () => {
        if (!leaveForm.start_date || !leaveForm.end_date) { setLeaveError("Rellena las fechas."); return; }
        setSaving(true); setLeaveError(null);
        try {
            await api.portal.submitLeave(leaveForm);
            setShowLeave(false);
            setLeaveForm({ leave_type: "vacaciones", start_date: "", end_date: "", notes: "" });
            await load();
        } catch { setLeaveError("Error al enviar."); }
        finally { setSaving(false); }
    };

    const emp = data?.employee;

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div className="space-y-3">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                        <User className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-foreground">{emp?.name ?? "Mi portal"}</h1>
                        <p className="text-xs text-muted-foreground">
                            {emp ? [emp.role, emp.department].filter(Boolean).join(" · ") : "Autoservicio del empleado"}
                        </p>
                    </div>
                </div>
                <p className="text-sm text-muted-foreground max-w-2xl">
                    Tu zona personal. Aquí consultas tu ficha, descargas tus nóminas,
                    solicitas vacaciones y reportas gastos para reembolso. Todo lo que envías
                    queda registrado y pasa por la aprobación de RRHH.
                </p>

                {isAdmin && (
                    <div className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl">
                        <Eye className="w-4 h-4 text-muted-foreground shrink-0" />
                        <div className="flex-1">
                            <p className="text-xs font-medium text-foreground mb-1">Vista de admin</p>
                            <p className="text-xs text-muted-foreground">
                                Como admin no tienes ficha aquí. Selecciona un empleado para previsualizar Mi portal en modo lectura.
                            </p>
                        </div>
                        <select
                            value={selectedEmployeeId}
                            onChange={(e) => handleSelectEmployee(e.target.value)}
                            className="bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:border-primary/20 outline-none min-w-[220px]"
                        >
                            <option value="">— Mi propio portal —</option>
                            {employeesList.map((e) => (
                                <option key={e.id} value={e.id}>
                                    {e.name}{e.email ? ` · ${e.email}` : ""}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {readOnly && (
                    <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
                        <Eye className="w-4 h-4 shrink-0" />
                        <span>Estás viendo Mi portal de otro empleado en <strong>modo lectura</strong>. No puedes solicitar vacaciones ni gastos en su nombre.</span>
                    </div>
                )}

                {emp && (
                    <div className="flex items-center gap-3 p-3 bg-card border border-border rounded-xl">
                        <Clock className={`w-5 h-5 shrink-0 ${data?.active_attendance ? "text-emerald-400" : "text-muted-foreground"}`} />
                        <div className="flex-1">
                            <p className="text-xs font-medium text-foreground">
                                {data?.active_attendance
                                    ? `Trabajando desde las ${formatClockTime(data.active_attendance.clock_in)}`
                                    : "No tienes ningún fichaje activo"}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {data?.active_attendance
                                    ? "Recuerda fichar la salida al terminar tu jornada."
                                    : "Pulsa para registrar tu entrada cuando empieces a trabajar."}
                            </p>
                        </div>
                        {data?.active_attendance ? (
                            <button
                                onClick={handleClockOut}
                                disabled={readOnly || clockBusy}
                                className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
                            >
                                {clockBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <StopCircle className="w-4 h-4" />}
                                Fichar salida
                            </button>
                        ) : (
                            <button
                                onClick={handleClockIn}
                                disabled={readOnly || clockBusy}
                                className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
                            >
                                {clockBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                                Fichar entrada
                            </button>
                        )}
                    </div>
                )}

                {clockError && (
                    <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-xl text-xs text-destructive">
                        {clockError}
                    </div>
                )}
            </div>

            {loading && (
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">Cargando…</div>
            )}

            {!loading && !emp && !isAdmin && (
                <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
                    <Briefcase className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm text-foreground font-medium">Tu cuenta no está vinculada a ningún empleado</p>
                    <p className="text-xs text-muted-foreground">
                        Pide al administrador que añada tu email ({" "}
                        <span className="font-mono text-xs">{typeof window !== "undefined" ? (() => { try { const t = localStorage.getItem("access_token"); if (!t) return ""; return JSON.parse(atob(t.split(".")[1])).email; } catch { return ""; } })() : ""}</span>
                        {" "}) a tu ficha de empleado.
                    </p>
                </div>
            )}

            {!loading && !emp && isAdmin && !selectedEmployeeId && (
                <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
                    <Briefcase className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm text-foreground font-medium">Selecciona un empleado para previsualizar</p>
                    <p className="text-xs text-muted-foreground">
                        Usa el selector de arriba para ver Mi portal de cualquier persona de tu plantilla.
                    </p>
                </div>
            )}

            {!loading && emp && (
                <>
                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-border">
                        {([
                            { id: "ficha", label: "Mi ficha", icon: User },
                            { id: "nominas", label: "Mis nóminas", icon: FileText },
                            { id: "vacaciones", label: "Mis ausencias", icon: Umbrella },
                            { id: "gastos", label: "Mis gastos", icon: Receipt },
                        ] as const).map(({ id, label, icon: Icon }) => (
                            <button
                                key={id}
                                onClick={() => setTab(id)}
                                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                    tab === id
                                        ? "border-primary text-foreground"
                                        : "border-transparent text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                <Icon className="w-4 h-4" /> {label}
                            </button>
                        ))}
                    </div>

                    {/* ── Ficha ── */}
                    {tab === "ficha" && (
                        <div className="space-y-3">
                            <p className="text-xs text-muted-foreground">
                                Datos personales y laborales según tu ficha en RRHH. Si algo es incorrecto, avisa al administrador.
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {[
                                { label: "Nombre completo", value: emp.name },
                                { label: "NIF", value: emp.nif ?? "—" },
                                { label: "Email", value: emp.email ?? "—" },
                                { label: "Departamento", value: emp.department ?? "—" },
                                { label: "Rol", value: emp.role ?? "—" },
                                { label: "Salario base", value: emp.base_salary ? currency(emp.base_salary) : "—" },
                                { label: "Fecha de alta", value: emp.join_date ? fmt(emp.join_date) : "—" },
                                { label: "IRPF", value: emp.irpf_rate != null ? `${emp.irpf_rate}%` : "—" },
                            ].map(({ label, value }) => (
                                <div key={label} className="rounded-xl border border-border bg-card p-4 space-y-1">
                                    <p className="text-xs text-muted-foreground">{label}</p>
                                    <p className="text-sm font-medium text-foreground">{value}</p>
                                </div>
                            ))}
                            {/* Status */}
                            <div className="rounded-xl border border-border bg-card p-4 space-y-1">
                                <p className="text-xs text-muted-foreground">Estado</p>
                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                                    emp.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                                    emp.status === "leave"  ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                                    "bg-muted text-muted-foreground border-border"
                                }`}>
                                    {emp.status === "active" ? "Activo" : emp.status === "leave" ? "De baja" : "Inactivo"}
                                </span>
                            </div>
                            </div>

                            {/* Horario semanal estipulado */}
                            <div className="rounded-xl border border-border bg-card overflow-hidden">
                                <div className="px-4 py-3 border-b border-border">
                                    <p className="text-sm font-medium text-foreground">Horario estipulado</p>
                                    <p className="text-xs text-muted-foreground">
                                        Tu jornada semanal según la ficha que configuró RRHH.
                                    </p>
                                </div>
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                                            <th className="text-left font-medium px-4 py-2">Día</th>
                                            <th className="text-left font-medium px-4 py-2">Entrada</th>
                                            <th className="text-left font-medium px-4 py-2">Salida</th>
                                            <th className="text-right font-medium px-4 py-2">Estado</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {DAY_LABELS.map((label, dayIdx) => {
                                            const slots = (data?.schedule ?? []).filter(s => s.day_of_week === dayIdx);
                                            if (slots.length === 0) {
                                                return (
                                                    <tr key={dayIdx} className="border-b border-border last:border-0">
                                                        <td className="px-4 py-2 text-foreground">{label}</td>
                                                        <td className="px-4 py-2 text-muted-foreground" colSpan={2}>Día libre</td>
                                                        <td className="px-4 py-2 text-right text-muted-foreground text-xs">—</td>
                                                    </tr>
                                                );
                                            }
                                            return slots.map((s, idx) => (
                                                <tr key={s.id ?? `${dayIdx}-${idx}`} className="border-b border-border last:border-0">
                                                    <td className="px-4 py-2 text-foreground">{idx === 0 ? label : ""}</td>
                                                    <td className="px-4 py-2 text-muted-foreground font-mono">{s.start_time}</td>
                                                    <td className="px-4 py-2 text-muted-foreground font-mono">{s.end_time}</td>
                                                    <td className="px-4 py-2 text-right">
                                                        {s.active ? (
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span>
                                                        ) : (
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-muted text-muted-foreground border border-border">Inactivo</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ));
                                        })}
                                    </tbody>
                                </table>
                                {(!data?.schedule || data.schedule.length === 0) && (
                                    <div className="px-4 py-3 text-xs text-muted-foreground border-t border-border">
                                        Tu ficha aún no tiene horario configurado. Avisa a RRHH para que lo añada.
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ── Nóminas ── */}
                    {tab === "nominas" && (
                        <div className="space-y-3">
                            <p className="text-xs text-muted-foreground">
                                Histórico de nóminas emitidas a tu nombre. Pulsa el icono de descarga para guardar el PDF.
                            </p>
                            {data!.payrolls.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                                    <FileText className="w-8 h-8 opacity-30" />
                                    <p className="text-sm">Aún no tienes nóminas generadas</p>
                                    <p className="text-xs max-w-xs text-center">
                                        Tu nómina aparecerá aquí cuando RRHH la emita y apruebe el cálculo del mes.
                                    </p>
                                </div>
                            ) : (
                                data!.payrolls.map((p: Payroll) => (
                                    <div key={p.id} className="flex items-center justify-between rounded-xl border border-border bg-card px-5 py-4">
                                        <div className="flex items-center gap-4">
                                            <Banknote className="w-5 h-5 text-emerald-400 shrink-0" />
                                            <div>
                                                <p className="text-sm font-medium text-foreground">
                                                    {fmt(p.period_start)} — {fmt(p.period_end)}
                                                </p>
                                                <p className="text-xs text-muted-foreground">Emitida: {fmt(p.issue_date)}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="text-right">
                                                <p className="text-sm font-semibold text-foreground">{currency(p.net_salary)}</p>
                                                <p className="text-xs text-muted-foreground">neto</p>
                                            </div>
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[p.status] ?? ""}`}>
                                                {PAYROLL_LABEL[p.status] ?? p.status}
                                            </span>
                                            <button
                                                onClick={() => api.hr.payrolls.downloadPdf(p.id, `nomina-${p.period_start.slice(0, 7)}.pdf`)}
                                                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                                                title="Descargar PDF"
                                            >
                                                <Download className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* ── Vacaciones ── */}
                    {tab === "vacaciones" && (
                        <div className="space-y-4">
                            <div className="flex items-start justify-between gap-4">
                                <p className="text-xs text-muted-foreground max-w-xl">
                                    Solicita vacaciones, bajas u otras ausencias. Cada petición pasa por aprobación
                                    y verás aquí su estado en cualquier momento.
                                </p>
                                <Button size="sm" className="gap-2 shrink-0" disabled={readOnly} onClick={() => { setShowLeave(true); setLeaveError(null); }}>
                                    <Plus className="w-4 h-4" /> Nueva solicitud
                                </Button>
                            </div>
                            {data!.leave_requests.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                                    <Umbrella className="w-8 h-8 opacity-30" />
                                    <p className="text-sm">No tienes solicitudes de ausencia</p>
                                    <p className="text-xs max-w-xs text-center">
                                        Pulsa <strong>Nueva solicitud</strong> arriba para pedir vacaciones, baja médica o excedencia.
                                    </p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-border overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-muted/30 text-muted-foreground">
                                            <tr>
                                                <th className="text-left px-4 py-3 font-medium">Tipo</th>
                                                <th className="text-left px-4 py-3 font-medium">Desde</th>
                                                <th className="text-left px-4 py-3 font-medium">Hasta</th>
                                                <th className="text-left px-4 py-3 font-medium">Días</th>
                                                <th className="text-left px-4 py-3 font-medium">Estado</th>
                                                <th className="text-left px-4 py-3 font-medium">Notas</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border">
                                            {data!.leave_requests.map((lr: LeaveRequest) => {
                                                const days = Math.round((new Date(lr.end_date).getTime() - new Date(lr.start_date).getTime()) / 86400000) + 1;
                                                return (
                                                    <tr key={lr.id} className="bg-card hover:bg-muted/20 transition-colors">
                                                        <td className="px-4 py-3 font-medium text-foreground capitalize">
                                                            {lr.leave_type.replace("_", " ")}
                                                        </td>
                                                        <td className="px-4 py-3 text-muted-foreground">{fmt(lr.start_date)}</td>
                                                        <td className="px-4 py-3 text-muted-foreground">{fmt(lr.end_date)}</td>
                                                        <td className="px-4 py-3 text-muted-foreground">{days}d</td>
                                                        <td className="px-4 py-3">
                                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BADGE[lr.status] ?? ""}`}>
                                                                {lr.status === "approved" && <Check className="w-3 h-3" />}
                                                                {lr.status === "rejected" && <X className="w-3 h-3" />}
                                                                {lr.status === "pending" && <Clock className="w-3 h-3" />}
                                                                {LEAVE_LABEL[lr.status] ?? lr.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 text-xs text-muted-foreground max-w-[140px] truncate">{lr.notes ?? "—"}</td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}
                    {/* ── Gastos ── */}
                    {tab === "gastos" && (
                        <div className="space-y-4">
                            <div className="flex items-start justify-between gap-4">
                                <p className="text-xs text-muted-foreground max-w-xl">
                                    Registra gastos profesionales para reembolso (viajes, dietas, material…).
                                    Adjunta el recibo y RRHH lo aprobará para incluirlo en tu próxima nómina.
                                </p>
                                <Button size="sm" className="gap-2 shrink-0" disabled={readOnly} onClick={() => { setShowExpense(true); setExpenseError(null); }}>
                                    <Plus className="w-4 h-4" /> Nuevo gasto
                                </Button>
                            </div>
                            {myExpenses.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                                    <Receipt className="w-8 h-8 opacity-30" />
                                    <p className="text-sm">No tienes gastos registrados</p>
                                    <p className="text-xs max-w-xs text-center">
                                        Pulsa <strong>Nuevo gasto</strong> arriba para reportar un gasto profesional y subir el recibo.
                                    </p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-border overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-muted/30 text-muted-foreground">
                                            <tr>
                                                <th className="text-left px-4 py-3 font-medium">Categoría</th>
                                                <th className="text-left px-4 py-3 font-medium">Descripción</th>
                                                <th className="text-left px-4 py-3 font-medium">Fecha</th>
                                                <th className="text-right px-4 py-3 font-medium">Importe</th>
                                                <th className="text-left px-4 py-3 font-medium">Estado</th>
                                                <th className="text-left px-4 py-3 font-medium">Recibo</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border">
                                            {myExpenses.map((exp) => (
                                                <tr key={exp.id} className="bg-card hover:bg-muted/20 transition-colors">
                                                    <td className="px-4 py-3 text-muted-foreground capitalize">
                                                        {EXPENSE_CATEGORIES.find((c) => c.value === exp.category)?.label ?? exp.category}
                                                    </td>
                                                    <td className="px-4 py-3 text-foreground max-w-[180px] truncate" title={exp.description}>
                                                        {exp.description}
                                                    </td>
                                                    <td className="px-4 py-3 text-muted-foreground">{fmt(exp.date)}</td>
                                                    <td className="px-4 py-3 text-right font-semibold text-foreground tabular-nums">
                                                        {new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(exp.amount)}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${EXPENSE_STATUS_STYLE[exp.status] ?? ""}`}>
                                                            {EXPENSE_STATUS_LABEL[exp.status] ?? exp.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        {exp.receipt_filename ? (
                                                            <button
                                                                onClick={() => api.hr.expenses.downloadReceipt(exp.id, exp.receipt_filename!)}
                                                                className="flex items-center gap-1 text-xs text-primary hover:underline"
                                                            >
                                                                <Download className="w-3 h-3" /> Ver
                                                            </button>
                                                        ) : exp.status === "pending" && !readOnly ? (
                                                            <label className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
                                                                {uploadingReceiptId === exp.id
                                                                    ? <Loader2 className="w-3 h-3 animate-spin" />
                                                                    : <Upload className="w-3 h-3" />}
                                                                <span>Adjuntar</span>
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
                                                        ) : <span className="text-xs text-muted-foreground">—</span>}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}

            {/* New leave request modal */}
            <Dialog open={showLeave} onOpenChange={setShowLeave}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>Solicitud de ausencia</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1.5">
                            <Label>Tipo *</Label>
                            <Select value={leaveForm.leave_type} onValueChange={(v) => setLeaveForm((f) => ({ ...f, leave_type: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {LEAVE_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label>Fecha inicio *</Label>
                                <Input type="date" value={leaveForm.start_date} onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))} />
                            </div>
                            <div className="space-y-1.5">
                                <Label>Fecha fin *</Label>
                                <Input type="date" value={leaveForm.end_date} onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))} />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Notas</Label>
                            <Input value={leaveForm.notes} onChange={(e) => setLeaveForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Opcional…" />
                        </div>
                        {leaveError && <p className="text-xs text-destructive">{leaveError}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowLeave(false)} disabled={saving}>Cancelar</Button>
                        <Button onClick={handleSubmitLeave} disabled={saving}>{saving ? "Enviando…" : "Enviar"}</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
            {/* New expense modal */}
            <Dialog open={showExpense} onOpenChange={setShowExpense}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>Nuevo gasto</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label>Importe (€) *</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    value={expenseForm.amount}
                                    onChange={(e) => setExpenseForm((f) => ({ ...f, amount: e.target.value }))}
                                    placeholder="0.00"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <Label>Fecha *</Label>
                                <Input
                                    type="date"
                                    value={expenseForm.date}
                                    onChange={(e) => setExpenseForm((f) => ({ ...f, date: e.target.value }))}
                                />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Categoría *</Label>
                            <Select value={expenseForm.category} onValueChange={(v) => setExpenseForm((f) => ({ ...f, category: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {EXPENSE_CATEGORIES.map((c) => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Descripción *</Label>
                            <Input
                                value={expenseForm.description}
                                onChange={(e) => setExpenseForm((f) => ({ ...f, description: e.target.value }))}
                                placeholder="Ej: Desplazamiento a cliente"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Notas</Label>
                            <Input
                                value={expenseForm.notes}
                                onChange={(e) => setExpenseForm((f) => ({ ...f, notes: e.target.value }))}
                                placeholder="Opcional…"
                            />
                        </div>
                        {expenseError && <p className="text-xs text-destructive">{expenseError}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowExpense(false)} disabled={expenseSaving}>Cancelar</Button>
                        <Button onClick={handleSubmitExpense} disabled={expenseSaving}>
                            {expenseSaving ? "Enviando…" : "Enviar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
