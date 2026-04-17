"use client";

import {
    LayoutDashboard, Plus, Search,
    FolderKanban, CalendarDays
} from "lucide-react";
import { format, differenceInDays } from "date-fns";
import { useProjectsPage } from "./_hooks/useProjectsPage";
import { NewProjectModal } from "./_components/NewProjectModal";

export default function ProjectsPage() {
    const {
        isLoading,
        showModal, setShowModal,
        saving, error,
        search, setSearch,
        form, setForm,
        viewStart, viewEnd,
        filtered,
        openModal, handleSubmit, getStatusBadge, getGanttBarStyle,
    } = useProjectsPage();

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-purple-500/10 rounded-xl">
                            <FolderKanban className="w-8 h-8 text-purple-400" />
                        </div>
                        Portfolio de Proyectos
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        Monitoriza los tiempos de entrega. La IA puede convertir reuniones en tareas dentro de estos proyectos.
                    </p>
                </div>
                <button
                    onClick={openModal}
                    className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-foreground shadow-lg shadow-purple-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                >
                    <Plus className="w-4 h-4" /> Nuevo Proyecto
                </button>
            </div>

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl mb-8">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="Buscar proyecto..." value={search} onChange={e => setSearch(e.target.value)}
                            className="bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-purple-500 transition-colors w-72" />
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground bg-background px-3 py-1.5 rounded-lg border border-border">
                        <CalendarDays className="w-4 h-4 text-muted-foreground" />
                        <span>Vista: {format(viewStart, 'd MMM')} – {format(viewEnd, 'd MMM')}</span>
                    </div>
                </div>
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                        <tr>
                            <th className="px-6 py-4 font-medium w-64">Proyecto</th>
                            <th className="py-4 font-medium px-4 border-l border-border">Cronograma (Gantt)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/50">
                        {isLoading ? (
                            <tr><td colSpan={2} className="py-12 text-center"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500 mx-auto"></div></td></tr>
                        ) : filtered.length === 0 ? (
                            <tr>
                                <td colSpan={2} className="px-6 py-16 text-center">
                                    <LayoutDashboard className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                    <p className="text-muted-foreground font-medium">Aún no hay proyectos activos</p>
                                    <button onClick={openModal} className="mt-3 text-sm text-purple-400 hover:text-purple-300 transition">+ Crear el primero</button>
                                </td>
                            </tr>
                        ) : filtered.map((proj) => {
                            const badge = getStatusBadge(proj.status);
                            return (
                                <tr key={proj.id} className="hover:bg-purple-500/[0.02] transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-foreground mb-1">{proj.name}</div>
                                        <div className="flex items-center gap-3">
                                            {badge ? (
                                                <span className={badge.className}>
                                                    <badge.icon className="w-3 h-3" />{badge.label}
                                                </span>
                                            ) : (
                                                <span className="text-xs text-muted-foreground">{proj.status}</span>
                                            )}
                                            {proj.due_date && <span className="text-xs text-muted-foreground">Vence: {format(new Date(proj.due_date), 'dd/MM/yyyy')}</span>}
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 border-l border-border relative">
                                        <div className="relative w-full h-[32px] bg-background/50 rounded-lg border border-border overflow-hidden">
                                            {proj.start_date && proj.due_date ? (
                                                <div className="absolute h-full rounded-md flex items-center px-3 text-xs font-semibold text-foreground/90"
                                                    style={getGanttBarStyle(proj.start_date, proj.due_date, proj.status)}>
                                                    {differenceInDays(new Date(proj.due_date), new Date(proj.start_date))} d
                                                </div>
                                            ) : (
                                                <div className="flex items-center justify-center h-full text-xs text-muted-foreground italic">Fechas no definidas</div>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {showModal && (
                <NewProjectModal
                    form={form}
                    onChange={setForm}
                    onSubmit={handleSubmit}
                    onClose={() => setShowModal(false)}
                    saving={saving}
                    error={error}
                />
            )}
        </div>
    );
}
