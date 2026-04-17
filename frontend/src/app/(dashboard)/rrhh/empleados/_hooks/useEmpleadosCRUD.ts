"use client";

import { useEffect, useMemo, useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { api, Employee, Payroll } from "@/lib/api";
import { useNotificationStore } from "@/stores/notifications";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import {
    Building2, WalletCards, GraduationCap,
    Pencil, Trash2, Loader2, Paperclip,
} from "lucide-react";
import { DataTableColumnHeader } from "@/components/data-table";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { EmployeeForm, EMPTY_FORM } from "./useEmpleadosTypes";

export const currencyFmt = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });

export function useEmpleadosCRUD(
    setDocsEmp: (emp: Employee | null) => void,
) {
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
    const [form, setForm] = useState<EmployeeForm>(EMPTY_FORM);

    const refreshKey = useNotificationStore((s) => s.refreshKey);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadData(); }, [refreshKey]);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.hr.employees.list();
            setEmployees(data);
        } catch (err) {
            logError("rrhh/empleados/page", err);
        } finally {
            setIsLoading(false);
        }
    };

    const openModal = () => {
        setEditingId(null);
        setForm(EMPTY_FORM);
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
        if (!await showConfirm({ message: `¿Eliminar a "${emp.name}"? Esta acción no se puede deshacer.`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
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

    const departmentOptions = useMemo(() => {
        const depts = new Set(employees.map((e) => e.department || "General"));
        return Array.from(depts).sort().map((d) => ({ label: d, value: d }));
    }, [employees]);

    const activeCount = employees.filter((e) => e.status === "active").length;
    const totalSalary = employees.reduce((acc, emp) => acc + (emp.base_salary || 0), 0);

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
                        <Button variant="ghost" size="icon" className="h-8 w-8"
                            onClick={() => openPayrolls(emp)} title="Ver nóminas">
                            <WalletCards className="h-4 w-4" />
                            <span className="sr-only">Ver nóminas</span>
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8"
                            onClick={() => setDocsEmp(emp)} title="Documentos del empleado">
                            <Paperclip className="h-4 w-4" />
                            <span className="sr-only">Documentos</span>
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8"
                            onClick={() => openEdit(emp)} title="Editar">
                            <Pencil className="h-4 w-4" />
                            <span className="sr-only">Editar</span>
                        </Button>
                        <Button variant="ghost" size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDelete(emp)}
                            disabled={deletingId === emp.id} title="Eliminar">
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

    return {
        employees, isLoading, columns, departmentOptions, activeCount, totalSalary,
        form, setForm, showModal, setShowModal, editingId, saving, error, openModal, handleSubmit,
        selectedEmp, setSelectedEmp, empPayrolls, loadingPayrolls, openPayrolls,
    };
}
