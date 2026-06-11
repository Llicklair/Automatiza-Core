"use client";

import {
    LayoutDashboard, Plus, FolderKanban, CalendarDays
} from "lucide-react";
import { format, differenceInDays } from "date-fns";
import { useProjectsPage } from "./_hooks/useProjectsPage";
import { NewProjectModal } from "./_components/NewProjectModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageContainer } from "@/components/shared/PageContainer";

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
        <PageContainer>
            <PageHeader
                title="Portfolio de Proyectos"
                description="Monitoriza los tiempos de entrega. La IA puede convertir reuniones en tareas dentro de estos proyectos."
                icon={FolderKanban}
                actions={
                    <Button onClick={openModal}>
                        <Plus className="w-4 h-4 mr-2" /> Nuevo Proyecto
                    </Button>
                }
            />

            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg">
                {/* Toolbar */}
                <div className="p-4 border-b border-border flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-muted/30">
                    <Input
                        placeholder="Buscar proyecto…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-72"
                    />
                    <div className="flex items-center gap-2 text-sm text-muted-foreground bg-card px-3 py-1.5 rounded-lg border border-border">
                        <CalendarDays className="w-4 h-4" />
                        <span>Vista: {format(viewStart, "d MMM")} – {format(viewEnd, "d MMM")}</span>
                    </div>
                </div>

                {/* Gantt table */}
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                        <tr>
                            <th className="px-6 py-4 font-medium w-64">Proyecto</th>
                            <th className="py-4 font-medium px-4 border-l border-border">Cronograma (Gantt)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {isLoading ? (
                            <tr>
                                <td colSpan={2} className="py-12 text-center">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto" />
                                </td>
                            </tr>
                        ) : filtered.length === 0 ? (
                            <tr>
                                <td colSpan={2} className="px-6 py-16 text-center">
                                    <LayoutDashboard className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                                    <p className="text-muted-foreground font-medium">Aún no hay proyectos activos</p>
                                    <Button variant="ghost" size="sm" onClick={openModal} className="mt-3 text-primary">
                                        + Crear el primero
                                    </Button>
                                </td>
                            </tr>
                        ) : filtered.map((proj) => {
                            const badge = getStatusBadge(proj.status);
                            return (
                                <tr key={proj.id} className="hover:bg-muted/30 transition-colors">
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
                                            {proj.due_date && (
                                                <span className="text-xs text-muted-foreground">
                                                    Vence: {format(new Date(proj.due_date), "dd/MM/yyyy")}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 border-l border-border">
                                        <div className="relative w-full h-[32px] bg-muted/50 rounded-lg border border-border overflow-hidden">
                                            {proj.start_date && proj.due_date ? (
                                                <div
                                                    className="absolute h-full rounded-md flex items-center px-3 text-xs font-semibold text-foreground/90"
                                                    style={getGanttBarStyle(proj.start_date, proj.due_date, proj.status)}
                                                >
                                                    {differenceInDays(new Date(proj.due_date), new Date(proj.start_date))} d
                                                </div>
                                            ) : (
                                                <div className="flex items-center justify-center h-full text-xs text-muted-foreground italic">
                                                    Fechas no definidas
                                                </div>
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
        </PageContainer>
    );
}
