"use client";

import { useEffect, useState } from "react";
import { api, Employee } from "@/lib/api";
import {
    Users, Plus, Search, Building2, Wallet,
    MoreHorizontal, GraduationCap, ShieldCheck, X, Loader2, Pencil, Trash2
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export default function EmployeesPage() {
    const toast = useToastStore();
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [search, setSearch] = useState("");

    const [editingId, setEditingId] = useState<string | null>(null);
    const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    // Form state
    const [form, setForm] = useState({
        name: "", nif: "", email: "", department: "", role: "",
        base_salary: "", status: "active",
        join_date: "", contract_end_date: "",
    });

    useEffect(() => { loadData(); }, []);

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
        setMenuOpenId(null);
        setError("");
        setShowModal(true);
    };

    const handleDelete = async (emp: Employee) => {
        setMenuOpenId(null);
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

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'active': return <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Activo</span>;
            case 'inactive': return <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">Inactivo</span>;
            case 'leave': return <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">De baja</span>;
            default: return <span className="text-xs text-zinc-500 capitalize">{status}</span>;
        }
    };

    const filtered = employees.filter(e =>
        e.name.toLowerCase().includes(search.toLowerCase()) ||
        (e.nif ?? "").toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-xl">
                            <Users className="w-8 h-8 text-indigo-400" />
                        </div>
                        Directorio de Empleados
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm max-w-2xl">
                        Gestiona las altas, roles y salarios. El Agente RRHH usará esta tabla para pre-calcular nóminas.
                    </p>
                </div>
                <button
                    onClick={openModal}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                >
                    <Plus className="w-4 h-4" /> Añadir Empleado
                </button>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-[#111113] p-5 rounded-2xl border border-zinc-800 shadow-xl flex items-center gap-4">
                    <div className="p-3 bg-zinc-800/50 rounded-xl">
                        <Users className="w-6 h-6 text-zinc-400" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-zinc-400">Plantilla Activa</p>
                        <p className="text-2xl font-semibold text-white">{employees.filter(e => e.status === 'active').length}</p>
                    </div>
                </div>
                <div className="bg-[#111113] p-5 rounded-2xl border border-zinc-800 shadow-xl flex items-center gap-4">
                    <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
                        <Wallet className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-zinc-400">Gasto Salarial (Mensual)</p>
                        <p className="text-2xl font-semibold text-indigo-400">
                            {new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' })
                                .format(employees.reduce((acc, emp) => acc + (emp.base_salary || 0), 0))}
                        </p>
                    </div>
                </div>
                <div className="bg-[#111113] p-5 rounded-2xl border border-zinc-800 shadow-xl flex gap-4">
                    <div className="p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20 h-fit">
                        <ShieldCheck className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-zinc-400 mb-1">Status Legal</p>
                        <p className="text-xs text-zinc-500">Contratos en regla. El sistema generará borradores el día 26.</p>
                    </div>
                </div>
            </div>

            {/* Tabla */}
            <div className="bg-[#111113] border border-zinc-800 rounded-2xl shadow-2xl">
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar por nombre o NIF..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-indigo-500 transition-colors w-72"
                        />
                    </div>
                </div>
                <table className="w-full text-left text-sm">
                    <thead className="bg-[#161618]/50 text-zinc-400 border-b border-zinc-800">
                        <tr>
                            <th className="px-6 py-4 font-medium">Empleado</th>
                            <th className="px-6 py-4 font-medium">Departamento</th>
                            <th className="px-6 py-4 font-medium">Salario Base</th>
                            <th className="px-6 py-4 font-medium">Estado</th>
                            <th className="px-6 py-4 font-medium text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/50">
                        {isLoading ? (
                            <tr><td colSpan={5} className="py-12 text-center"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500 mx-auto"></div></td></tr>
                        ) : filtered.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-16 text-center">
                                    <Users className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                                    <p className="text-zinc-400 font-medium">No hay empleados registrados</p>
                                    <button onClick={openModal} className="mt-3 text-sm text-indigo-400 hover:text-indigo-300 transition">+ Añadir el primero</button>
                                </td>
                            </tr>
                        ) : filtered.map((emp) => (
                            <tr key={emp.id} className="hover:bg-indigo-500/[0.02] transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs text-white font-medium border border-zinc-700">
                                            {emp.name.substring(0, 2).toUpperCase()}
                                        </div>
                                        <div>
                                            <div className="font-medium text-white">{emp.name}</div>
                                            <div className="text-xs text-zinc-500">{emp.nif || "S/NIF"}</div>
                                            {emp.email && <div className="text-xs text-zinc-500">{emp.email}</div>}
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2 text-zinc-300"><Building2 className="w-4 h-4 text-zinc-500" />{emp.department || "General"}</div>
                                    <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1"><GraduationCap className="w-3.5 h-3.5" />{emp.role || "Staff"}</div>
                                    {emp.join_date && <div className="text-xs text-zinc-600 mt-1">Alta: {new Date(emp.join_date).toLocaleDateString("es-ES")}</div>}
                                </td>
                                <td className="px-6 py-4 text-zinc-300 font-medium">
                                    {emp.base_salary ? new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(emp.base_salary) : '---'}
                                </td>
                                <td className="px-6 py-4">{getStatusBadge(emp.status)}</td>
                                <td className="px-6 py-4 text-right">
                                    <div className="relative inline-block">
                                        <button
                                            onClick={() => setMenuOpenId(menuOpenId === emp.id ? null : emp.id)}
                                            className="text-zinc-500 hover:text-white transition-colors p-2 rounded-lg hover:bg-zinc-800"
                                        >
                                            {deletingId === emp.id ? <Loader2 className="w-5 h-5 animate-spin" /> : <MoreHorizontal className="w-5 h-5" />}
                                        </button>
                                        {menuOpenId === emp.id && (
                                            <>
                                                <div className="fixed inset-0 z-40" onClick={() => setMenuOpenId(null)} />
                                                <div className="absolute right-0 top-full mt-1 z-50 bg-[#18181b] border border-zinc-700 rounded-xl shadow-2xl overflow-hidden min-w-[160px]">
                                                    <button
                                                        onClick={() => openEdit(emp)}
                                                        className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-zinc-300 hover:text-white hover:bg-white/5 transition"
                                                    >
                                                        <Pencil className="w-4 h-4" /> Editar
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(emp)}
                                                        className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition"
                                                    >
                                                        <Trash2 className="w-4 h-4" /> Eliminar
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Modal Añadir Empleado */}
            {showModal && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
                    <div className="w-full max-w-md rounded-2xl border border-[#27272a] bg-[#111113] overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272a]">
                            <h2 className="font-semibold text-white">{editingId ? "Editar Empleado" : "Nuevo Empleado"}</h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5 font-medium">Nombre completo *</label>
                                <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                    placeholder="Ej: María García López"
                                    className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">NIF</label>
                                    <input value={form.nif} onChange={e => setForm(f => ({ ...f, nif: e.target.value }))}
                                        placeholder="12345678A"
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Salario base (€/mes)</label>
                                    <input type="number" value={form.base_salary} onChange={e => setForm(f => ({ ...f, base_salary: e.target.value }))}
                                        placeholder="2000"
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                                </div>
                            </div>
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5">Email</label>
                                <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                                    placeholder="empleado@empresa.com"
                                    className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Departamento</label>
                                    <input value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))}
                                        placeholder="Administración"
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Cargo</label>
                                    <input value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                                        placeholder="Contable"
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                                </div>
                            </div>
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5">Estado</label>
                                <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
                                    className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                                    <option value="active">Activo</option>
                                    <option value="inactive">Inactivo</option>
                                    <option value="leave">De baja</option>
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Fecha de alta</label>
                                    <input type="date" value={form.join_date} onChange={e => setForm(f => ({ ...f, join_date: e.target.value }))}
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Fin de contrato</label>
                                    <input type="date" value={form.contract_end_date} onChange={e => setForm(f => ({ ...f, contract_end_date: e.target.value }))}
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                                </div>
                            </div>
                            {error && <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">{error}</p>}
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)}
                                    className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 text-sm hover:text-white transition">Cancelar</button>
                                <button type="submit" disabled={saving}
                                    className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition flex items-center justify-center gap-2">
                                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                    {saving ? "Guardando…" : editingId ? "Guardar cambios" : "Crear empleado"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
