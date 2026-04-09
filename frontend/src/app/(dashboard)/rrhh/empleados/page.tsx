"use client";

import { useEffect, useMemo, useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { api, Employee, Payroll } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
    Users, Plus, Building2, Wallet, WalletCards, FileText,
    GraduationCap, ShieldCheck, Pencil, Trash2, Loader2, X, Download, Paperclip,
} from "lucide-react";
import { EmployeeDocsModal } from "./_components/EmployeeDocsModal";

import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { KpiCard } from "@/components/shared/KpiCard";
import { FormModal, FormField } from "@/components/shared";
import { EmptyState } from "@/components/shared/EmptyState";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
} from "@/components/ui/select";

const STATUS_OPTIONS = [
    { label: "Activo", value: "active" },
    { label: "Inactivo", value: "inactive" },
    { label: "De baja", value: "leave" },
];

const currencyFmt = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });

export default function EmployeesPage() {
    const toast = useToastStore();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    const [editingId, setEditingId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [selectedEmp, setSelectedEmp] = useState<Employee | null>(null);
    const [empPayrolls, setEmpPayrolls] = useState<Payroll[]>([]);
    const [loadingPayrolls, setLoadingPayrolls] = useState(false);
    const [docsEmp, setDocsEmp] = useState<Employee | null>(null);

    // Form state
    const [form, setForm] = useState({
        name: "", nif: "", email: "", department: "", role: "",
        base_salary: "", status: "active",
        join_date: "", contract_end_date: "",
    });

    const refreshKey = useNotificationStore((s) => s.refreshKey);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadData(); }, [refreshKey]);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.hr.employees.list();
            setEmployees(data);
        } catch (error) {
            logError("rrhh/empleados/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const openModal = () => {
        setEditingId(null);
        setForm({ name: "", nif: "", email: "", department: "", role: "", base_salary: "", status: "active", join_date: "", contract_end_date: "" });
        setError("");
        setShowModal(true);
    };

    const openEdit = (emp: Employee) => {
        setEditingId(emp.id);
        setForm({
            name: emp.name, nif: emp.nif || "", email: emp.email || "",
            department: emp.department || "", role: emp.role || "",
            base_salary: emp.base_salary ? String(emp.base_salary) : "", status: emp.status,
            join_date: emp.join_date ? emp.join_date.slice(0, 10) : "",
            contract_end_date: emp.contract_end_date ? emp.contract_end_date.slice(0, 10) : "",
        });
        setError("");
        setShowModal(true);
    };

    const handleDelete = async (emp: Employee) => {
        if (!await showConfirm({ message: `\u00bfEliminar a "${emp.name}"? Esta acci\u00f3n no se puede deshacer.`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        setDeletingId(emp.id);
        try {
            await api.hr.employees.delete(emp.id);
            await loadData();
        } catch (err: unknown) {
            toast.error(err instanceof Error ? err.message : "Error al eliminar");
        } finally {
            setDeletingId(null);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setSaving(true);
        setError("");
        try {
            const payload = {
                name: form.name,
                nif: form.nif || undefined,
                email: form.email || undefined,
                department: form.department || undefined,
                role: form.role || undefined,
                base_salary: form.base_salary ? parseFloat(form.base_salary) : undefined,
                status: form.status,
                join_date: form.join_date || undefined,
                contract_end_date: form.contract_end_date || undefined,
            };
            if (editingId) {
                await api.hr.employees.update(editingId, payload);
            } else {
                await api.hr.employees.create(payload);
            }
            setShowModal(false);
            await loadData();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Error al crear empleado");
        } finally {
            setSaving(false);
        }
    };

    const openPayrolls = async (emp: Employee) => {
        setSelectedEmp(emp);
        setEmpPayrolls([]);
        setLoadingPayrolls(true);
        try {
            const all = await api.hr.payrolls.list();
            setEmpPayrolls(all.filter(p => p.employee_id === emp.id));
        } catch (err) {
            logError("rrhh/empleados/payrolls", err);
        } finally {
            setLoadingPayrolls(false);
        }
    };

    // ---------- Unique departments for faceted filter ----------
    const departmentOptions = useMemo(() => {
        const depts = new Set(employees.map((e) => e.department || "General"));
        return Array.from(depts).sort().map((d) => ({ label: d, value: d }));
    }, [employees]);

    // ---------- Column definitions ----------
    const columns = useMemo<ColumnDef<Employee>[]>(() => [
        {
            accessorKey: "name",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Empleado" />,
            cell: ({ row }) => {
                const emp = row.original;
                return (
                    <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-foreground border border-border">
                            {emp.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <div className="font-medium text-foreground">{emp.name}</div>
                            <div className="text-xs text-muted-foreground">{emp.nif || "S/NIF"}</div>
                            {emp.email && <div className="text-xs text-muted-foreground">{emp.email}</div>}
                        </div>
                    </div>
                );
            },
            filterFn: (row, _id, filterValue: string) => {
                const emp = row.original;
                const q = filterValue.toLowerCase();
                return emp.name.toLowerCase().includes(q) || (emp.nif ?? "").toLowerCase().includes(q);
            },
        },
        {
            accessorKey: "department",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Departamento" />,
            cell: ({ row }) => {
                const emp = row.original;
                return (
                    <div>
                        <div className="flex items-center gap-2 text-foreground">
                            <Building2 className="h-4 w-4 text-muted-foreground" />
                            {emp.department || "General"}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                            <GraduationCap className="h-3.5 w-3.5" />
                            {emp.role || "Staff"}
                        </div>
                        {emp.join_date && (
                            <div className="text-xs text-muted-foreground/60 mt-1">
                                Alta: {new Date(emp.join_date).toLocaleDateString("es-ES")}
                            </div>
                        )}
                    </div>
                );
            },
            filterFn: (row, _id, filterValue: string[]) => {
                const dept = row.original.department || "General";
                return filterValue.includes(dept);
            },
        },
        {
            accessorKey: "base_salary",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Salario Base" />,
            cell: ({ row }) => {
                const salary = row.original.base_salary;
                return (
                    <span className="font-medium text-foreground">
                        {salary ? currencyFmt.format(salary) : "---"}
                    </span>
                );
            },
        },
        {
            accessorKey: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Estado" />,
            cell: ({ row }) => <StatusBadge status={row.original.status} />,
            filterFn: (row, _id, filterValue: string[]) => {
                return filterValue.includes(row.original.status);
            },
        },
        {
            id: "actions",
            header: () => <div className="text-right">Acciones</div>,
            cell: ({ row }) => {
                const emp = row.original;
                return (
                    <div className="flex items-center justify-end gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openPayrolls(emp)}
                            title="Ver nóminas"
                        >
                            <WalletCards className="h-4 w-4" />
                            <span className="sr-only">Ver nóminas</span>
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => setDocsEmp(emp)}
                            title="Documentos del empleado"
                        >
                            <Paperclip className="h-4 w-4" />
                            <span className="sr-only">Documentos</span>
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openEdit(emp)}
                            title="Editar"
                        >
                            <Pencil className="h-4 w-4" />
                            <span className="sr-only">Editar</span>
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDelete(emp)}
                            disabled={deletingId === emp.id}
                            title="Eliminar"
                        >
                            {deletingId === emp.id
                                ? <Loader2 className="h-4 w-4 animate-spin" />
                                : <Trash2 className="h-4 w-4" />}
                            <span className="sr-only">Eliminar</span>
                        </Button>
                    </div>
                );
            },
            enableSorting: false,
            enableHiding: false,
        },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    ], [deletingId]);

    // ---------- KPI values ----------
    const activeCount = employees.filter((e) => e.status === "active").length;
    const totalSalary = employees.reduce((acc, emp) => acc + (emp.base_salary || 0), 0);

    return (
        <div className="space-y-6 p-6">
            {docsEmp && <EmployeeDocsModal employee={docsEmp} onClose={() => setDocsEmp(null)} />}
            <PageHeader
                title="Directorio de Empleados"
                description="Gestiona las altas, roles y salarios. El Agente RRHH usar\u00e1 esta tabla para pre-calcular n\u00f3minas."
                icon={Users}
                actions={
                    <Button onClick={openModal}>
                        <Plus className="mr-2 h-4 w-4" /> A\u00f1adir Empleado
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <KpiCard
                    title="Plantilla Activa"
                    value={activeCount}
                    icon={Users}
                />
                <KpiCard
                    title="Gasto Salarial (Mensual)"
                    value={currencyFmt.format(totalSalary)}
                    icon={Wallet}
                />
                <KpiCard
                    title="Status Legal"
                    value="En regla"
                    icon={ShieldCheck}
                    description="Contratos en regla. El sistema generar\u00e1 borradores el d\u00eda 26."
                />
            </div>

            {/* Table */}
            {employees.length === 0 && !isLoading ? (
                <EmptyState
                    icon={Users}
                    title="No hay empleados registrados"
                    description="A\u00f1ade tu primer empleado para empezar a gestionar la plantilla."
                    action={
                        <Button onClick={openModal} size="sm">
                            <Plus className="mr-2 h-4 w-4" /> A\u00f1adir el primero
                        </Button>
                    }
                />
            ) : (
                <DataTable
                    columns={columns}
                    data={employees}
                    searchKey="name"
                    searchPlaceholder="Buscar por nombre o NIF..."
                    isLoading={isLoading}
                    emptyMessage="No se encontraron empleados."
                    facetedFilters={[
                        {
                            column: "status",
                            title: "Estado",
                            options: STATUS_OPTIONS,
                        },
                        {
                            column: "department",
                            title: "Departamento",
                            options: departmentOptions,
                        },
                    ]}
                />
            )}

            {/* Modal */}
            <FormModal
                open={showModal}
                onClose={() => setShowModal(false)}
                title={editingId ? "Editar Empleado" : "Nuevo Empleado"}
                onSubmit={handleSubmit}
                isSubmitting={saving}
                submitLabel={saving ? "Guardando\u2026" : editingId ? "Guardar cambios" : "Crear empleado"}
            >
                <div className="space-y-4">
                    <FormField label="Nombre completo" required>
                        <Input
                            required
                            value={form.name}
                            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                            placeholder="Ej: Mar\u00eda Garc\u00eda L\u00f3pez"
                        />
                    </FormField>

                    <div className="grid grid-cols-2 gap-3">
                        <FormField label="NIF">
                            <Input
                                value={form.nif}
                                onChange={(e) => setForm((f) => ({ ...f, nif: e.target.value }))}
                                placeholder="12345678A"
                            />
                        </FormField>
                        <FormField label="Salario base (\u20ac/mes)">
                            <Input
                                type="number"
                                value={form.base_salary}
                                onChange={(e) => setForm((f) => ({ ...f, base_salary: e.target.value }))}
                                placeholder="2000"
                            />
                        </FormField>
                    </div>

                    <FormField label="Email">
                        <Input
                            type="email"
                            value={form.email}
                            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                            placeholder="empleado@empresa.com"
                        />
                    </FormField>

                    <div className="grid grid-cols-2 gap-3">
                        <FormField label="Departamento">
                            <Input
                                value={form.department}
                                onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}
                                placeholder="Administraci\u00f3n"
                            />
                        </FormField>
                        <FormField label="Cargo">
                            <Input
                                value={form.role}
                                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                                placeholder="Contable"
                            />
                        </FormField>
                    </div>

                    <FormField label="Estado">
                        <Select
                            value={form.status}
                            onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Seleccionar estado" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="active">Activo</SelectItem>
                                <SelectItem value="inactive">Inactivo</SelectItem>
                                <SelectItem value="leave">De baja</SelectItem>
                            </SelectContent>
                        </Select>
                    </FormField>

                    <div className="grid grid-cols-2 gap-3">
                        <FormField label="Fecha de alta">
                            <Input
                                type="date"
                                value={form.join_date}
                                onChange={(e) => setForm((f) => ({ ...f, join_date: e.target.value }))}
                            />
                        </FormField>
                        <FormField label="Fin de contrato">
                            <Input
                                type="date"
                                value={form.contract_end_date}
                                onChange={(e) => setForm((f) => ({ ...f, contract_end_date: e.target.value }))}
                            />
                        </FormField>
                    </div>

                    {error && (
                        <p className="text-sm text-destructive bg-destructive/10 p-3 rounded-lg">{error}</p>
                    )}
                </div>
            </FormModal>

            {/* Drawer: historial de nóminas del empleado */}
            {selectedEmp && (
                <div
                    className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
                    role="dialog"
                    aria-modal="true"
                    onClick={(e) => e.target === e.currentTarget && setSelectedEmp(null)}
                >
                    <div className="w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
                        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                            <div>
                                <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                                    <WalletCards className="w-5 h-5 text-emerald-400" />
                                    Nóminas de {selectedEmp.name}
                                </h2>
                                {selectedEmp.department && (
                                    <p className="text-xs text-muted-foreground mt-0.5">{selectedEmp.department} · {selectedEmp.role || "Staff"}</p>
                                )}
                            </div>
                            <button
                                type="button"
                                onClick={() => setSelectedEmp(null)}
                                className="p-2 rounded-lg text-muted-foreground hover:bg-muted"
                                aria-label="Cerrar"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                        <div className="p-5 space-y-3 max-h-[60vh] overflow-y-auto">
                            {loadingPayrolls ? (
                                <div className="flex justify-center py-8">
                                    <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                                </div>
                            ) : empPayrolls.length === 0 ? (
                                <div className="text-center py-8">
                                    <WalletCards className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                                    <p className="text-sm text-muted-foreground">Este empleado no tiene nóminas generadas.</p>
                                    <Link href="/rrhh/nominas" className="text-xs text-primary hover:underline mt-2 inline-block">
                                        Ir a Nóminas para generar
                                    </Link>
                                </div>
                            ) : (
                                empPayrolls.map((p) => (
                                    <div key={p.id} className="flex items-center justify-between gap-3 bg-muted/50 border border-border rounded-xl px-4 py-3">
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium text-foreground">
                                                {format(new Date(p.period_start), "d MMM", { locale: es })} – {format(new Date(p.period_end), "d MMM yyyy", { locale: es })}
                                            </div>
                                            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                                                <span>Bruto: {currencyFmt.format(p.base_salary)}</span>
                                                <span className="text-emerald-400 font-medium">Neto: {currencyFmt.format(p.net_salary)}</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                                                p.status === "paid" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                                : p.status === "draft" ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                                                : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                            }`}>
                                                {p.status === "paid" ? "Pagada" : p.status === "draft" ? "Borrador" : "Emitida"}
                                            </span>
                                            <button
                                                onClick={() => api.hr.payrolls.downloadPdf(p.id, `Nomina_${selectedEmp.name.replace(/\s+/g, "_")}_${format(new Date(p.period_start), "yyyy-MM")}.pdf`)}
                                                className="p-1.5 text-muted-foreground hover:text-primary bg-background hover:bg-primary/10 rounded-lg transition-colors"
                                                title="Descargar PDF"
                                            >
                                                <Download className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                        <div className="flex justify-between items-center px-5 py-3 border-t border-border bg-background">
                            <Link href="/rrhh/nominas" className="text-xs text-primary hover:underline">
                                Ver todas las nóminas →
                            </Link>
                            <button
                                type="button"
                                onClick={() => setSelectedEmp(null)}
                                className="px-4 py-2 text-sm rounded-lg text-muted-foreground hover:bg-muted"
                            >
                                Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
