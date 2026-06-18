"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";
import { KanbanSquare, Plus, Search } from "lucide-react";
import { useTasksKanban } from "./_hooks/useTasksKanban";
import { KanbanColumn } from "./_components/KanbanColumn";
import { CreateTaskModal } from "./_components/CreateTaskModal";
import { EditTaskModal } from "./_components/EditTaskModal";
import { PageContainer } from "@/components/shared/PageContainer";

function TasksKanbanContent() {
    const k = useTasksKanban();
    const t = useTranslations("proyectos");

    return (
        <PageContainer width="full" className="min-h-screen bg-background text-foreground">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-pink-500/10 rounded-xl">
                            <KanbanSquare className="w-8 h-8 text-pink-400" />
                        </div>
                        {t("tareas.title")}
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        {t("tareas.description")}
                    </p>
                </div>
                <div className="flex gap-3">
                    <button className="flex items-center gap-2 bg-card border border-border hover:border-border hover:bg-muted text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Search className="w-4 h-4" /> {t("tareas.filter")}
                    </button>
                    <button
                        onClick={() => k.setShowModal(true)}
                        className="flex items-center gap-2 bg-pink-600 hover:bg-pink-500 text-foreground shadow-lg shadow-pink-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" /> {t("tareas.addTask")}
                    </button>
                </div>
            </div>

            {k.isLoading ? (
                <div className="flex justify-center p-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
                </div>
            ) : (
                <div className="flex gap-6 overflow-x-auto pb-6 custom-scrollbar px-1">
                    {(["todo", "in_progress", "done"] as const).map(status => (
                        <KanbanColumn
                            key={status}
                            colTitle={status === "todo" ? t("tareas.columnTodo") : status === "in_progress" ? t("tareas.columnInProgress") : t("tareas.columnDone")}
                            status={status}
                            tasks={k.getTasksByStatus(status)}
                            openMenuId={k.openMenuId}
                            setOpenMenuId={k.setOpenMenuId}
                            onDragStart={k.handleDragStart}
                            onDragEnd={k.handleDragEnd}
                            onDragOver={k.handleDragOver}
                            onDrop={k.handleDrop}
                            onEditOpen={k.handleEditOpen}
                            onDelete={k.handleDelete}
                        />
                    ))}
                </div>
            )}

            {k.showModal && (
                <CreateTaskModal
                    title={k.title} setTitle={k.setTitle}
                    description={k.description} setDescription={k.setDescription}
                    dueDate={k.dueDate} setDueDate={k.setDueDate}
                    saving={k.saving}
                    onClose={() => k.setShowModal(false)}
                    onSubmit={k.handleCreate}
                />
            )}

            {k.editTask && (
                <EditTaskModal
                    editTask={k.editTask}
                    editTitle={k.editTitle} setEditTitle={k.setEditTitle}
                    editDescription={k.editDescription} setEditDescription={k.setEditDescription}
                    editDueDate={k.editDueDate} setEditDueDate={k.setEditDueDate}
                    editSaving={k.editSaving}
                    onClose={() => k.setEditTask(null)}
                    onSubmit={k.handleEditSave}
                />
            )}
        </PageContainer>
    );
}

export default function TasksKanbanPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-background flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div></div>}>
            <TasksKanbanContent />
        </Suspense>
    );
}
