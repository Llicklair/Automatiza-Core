"use client";

import { useEffect, useState } from "react";
import { api, Project } from "@/lib/api";
import {
    LayoutDashboard, Plus, Search, Clock,
    CheckCircle2, PlayCircle, FolderKanban, CalendarDays, X, Loader2
} from "lucide-react";
import { format, differenceInDays, isAfter, isBefore, addDays } from "date-fns";
import { logError } from "@/lib/logger";

export default function ProjectsPage() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [search, setSearch] = useState("");

    const [form, setForm] = useState({
        name: "", description: "", budget: "",
        start_date: "", due_date: "", status: "active"
    });

    const viewStart = addDays(new Date(), -10);
    const viewEnd = addDays(new Date(), 40);
    const totalDays = differenceInDays(viewEnd, viewStart);

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.projects.list();
            setProjects(data);
        } catch (error) { logError("proyectos/page", error); }
        finally { setIsLoading(false); }
    };

    const openModal = () => {
        setForm({ name: "", description: "", budget: "", start_date: "", due_date: "", status: "active" });
        setError("");
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setSaving(true);
        setError("");
        try {
            await api.projects.create({
                name: form.name,
                description: form.description || undefined,
                budget: form.budget ? parseFloat(form.budget) : 0,
                status: form.status,
                start_date: form.start_date || undefined,
                due_date: form.due_date || undefined,
            });
            setShowModal(false);
            await loadData();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Error al crear proyecto");
        } finally {
            setSaving(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'active': return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"><PlayCircle className="w-3 h-3" />En curso</span>;
            case 'completed': return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" />Completado</span>;
            case 'on_hold': return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20"><Clock className="w-3 h-3" />Pausado</span>;
            default: return <span className="text-xs text-zinc-500">{status}</span>;
        }
    };

    const getGanttBarStyle = (start: string | null, due: string | null, status: string) => {
        if (!start || !due) return { display: 'none' as const };
        const dStart = new Date(start);
        const dEnd = new Date(due);
        const visualStart = isBefore(dStart, viewStart) ? viewStart : dStart;
        const visualEnd = isAfter(dEnd, viewEnd) ? viewEnd : dEnd;
        if (isAfter(dStart, viewEnd) || isBefore(dEnd, viewStart)) return { display: 'none' as const };
        const leftPct = (differenceInDays(visualStart, viewStart) / totalDays) * 100;
        const widthPct = (differenceInDays(visualEnd, visualStart) / totalDays) * 100;
        let bg = "linear-gradient(90deg, #3b82f6, #60a5fa)";
        if (status === 'completed') bg = "linear-gradient(90deg, #10b981, #34d399)";
        if (status === 'on_hold') bg = "linear-gradient(90deg, #f59e0b, #fbbf24)";
        return { left: `${Math.max(0, leftPct)}%`, width: `${Math.max(2, widthPct)}%`, background: bg };
    };

    const filtered = projects.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-purple-500/10 rounded-xl">
                            <FolderKanban className="w-8 h-8 text-purple-400" />
                        </div>
                        Portfolio de Proyectos
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm max-w-2xl">
                        Monitoriza los tiempos de entrega. La IA puede convertir reuniones en tareas dentro de estos proyectos.
                    </p>
                </div>
                <button
                    onClick={openModal}
                    className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                >
                    <Plus className="w-4 h-4" /> Nuevo Proyecto
                </button>
            </div>

            {/* Tabla Gantt */}
            <div className="bg-[#111113] border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl mb-8">
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar proyecto..." value={search} onChange={e => setSearch(e.target.value)}
                            className="bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-purple-500 transition-colors w-72" />
                    </div>
                    <div className="flex items-center gap-2 text-sm text-zinc-400 bg-[#09090b] px-3 py-1.5 rounded-lg border border-zinc-800">
                        <CalendarDays className="w-4 h-4 text-zinc-500" />
                        <span>Vista: {format(viewStart, 'd MMM')} – {format(viewEnd, 'd MMM')}</span>
                    </div>
                </div>
                <table className="w-full text-left text-sm">
                    <thead className="bg-[#161618]/50 text-zinc-400 border-b border-zinc-800">
                        <tr>
                            <th className="px-6 py-4 font-medium w-64">Proyecto</th>
                            <th className="py-4 font-medium px-4 border-l border-zinc-800/50">Cronograma (Gantt)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/50">
                        {isLoading ? (
                            <tr><td colSpan={2} className="py-12 text-center"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500 mx-auto"></div></td></tr>
                        ) : filtered.length === 0 ? (
                            <tr>
                                <td colSpan={2} className="px-6 py-16 text-center">
                                    <LayoutDashboard className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                                    <p className="text-zinc-400 font-medium">Aún no hay proyectos activos</p>
                                    <button onClick={openModal} className="mt-3 text-sm text-purple-400 hover:text-purple-300 transition">+ Crear el primero</button>
                                </td>
                            </tr>
                        ) : filtered.map((proj) => (
                            <tr key={proj.id} className="hover:bg-purple-500/[0.02] transition-colors">
                                <td className="px-6 py-4">
                                    <div className="font-medium text-white mb-1">{proj.name}</div>
                                    <div className="flex items-center gap-3">
                                        {getStatusBadge(proj.status)}
                                        {proj.due_date && <span className="text-xs text-zinc-500">Vence: {format(new Date(proj.due_date), 'dd/MM/yyyy')}</span>}
                                    </div>
                                </td>
                                <td className="px-4 py-4 border-l border-zinc-800/50 relative">
                                    <div className="relative w-full h-[32px] bg-[#09090b]/50 rounded-lg border border-zinc-800/50 overflow-hidden">
                                        {proj.start_date && proj.due_date ? (
                                            <div className="absolute h-full rounded-md flex items-center px-3 text-xs font-semibold text-white/90"
                                                style={getGanttBarStyle(proj.start_date, proj.due_date, proj.status)}>
                                                {differenceInDays(new Date(proj.due_date), new Date(proj.start_date))} d
                                            </div>
                                        ) : (
                                            <div className="flex items-center justify-center h-full text-xs text-zinc-600 italic">Fechas no definidas</div>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Modal Nuevo Proyecto */}
            {showModal && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
                    <div className="w-full max-w-md rounded-2xl border border-[#27272a] bg-[#111113] overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272a]">
                            <h2 className="font-semibold text-white">Nuevo Proyecto</h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5 font-medium">Nombre del proyecto *</label>
                                <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                    placeholder="Ej: Reforma web corporativa"
                                    className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-purple-500" />
                            </div>
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5">Descripción</label>
                                <textarea rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                    placeholder="Objetivos del proyecto..."
                                    className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500" />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Fecha inicio</label>
                                    <input type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Fecha límite</label>
                                    <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Presupuesto (€)</label>
                                    <input type="number" value={form.budget} onChange={e => setForm(f => ({ ...f, budget: e.target.value }))}
                                        placeholder="5000"
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-purple-500" />
                                </div>
                                <div>
                                    <label className="text-sm text-zinc-300 block mb-1.5">Estado</label>
                                    <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
                                        className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
                                        <option value="active">En curso</option>
                                        <option value="on_hold">Pausado</option>
                                        <option value="completed">Completado</option>
                                    </select>
                                </div>
                            </div>
                            {error && <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">{error}</p>}
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)}
                                    className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 text-sm hover:text-white transition">Cancelar</button>
                                <button type="submit" disabled={saving}
                                    className="flex-1 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-sm font-medium transition flex items-center justify-center gap-2">
                                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                    {saving ? "Creando…" : "Crear proyecto"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
