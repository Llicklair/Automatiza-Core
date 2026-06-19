"use client";

import { ProjectTask } from "@/lib/api";
import {
    MoreHorizontal, Calendar, CheckCircle2, Clock, PlayCircle,
    Pencil, Trash2,
} from "lucide-react";
import { format } from "date-fns";
import { useTranslations } from "next-intl";
import type { TaskStatus } from "../_hooks/useTasksKanban";

interface KanbanColumnProps {
    colTitle: string;
    status: TaskStatus;
    tasks: ProjectTask[];
    openMenuId: string | null;
    setOpenMenuId: (id: string | null) => void;
    onDragStart: (e: React.DragEvent, task: ProjectTask) => void;
    onDragEnd: (e: React.DragEvent) => void;
    onDragOver: (e: React.DragEvent) => void;
    onDrop: (e: React.DragEvent, status: TaskStatus) => void;
    onEditOpen: (task: ProjectTask) => void;
    onDelete: (task: ProjectTask) => void;
}

export function KanbanColumn({
    colTitle, status, tasks: columnTasks, openMenuId, setOpenMenuId,
    onDragStart, onDragEnd, onDragOver, onDrop, onEditOpen, onDelete,
}: KanbanColumnProps) {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
    let headerColor = "bg-muted text-foreground";
    if (status === 'in_progress') headerColor = "bg-blue-500/10 text-blue-400 border-blue-500/20";
    if (status === 'done') headerColor = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";

    return (
        <div
            className="flex flex-col bg-card border border-border rounded-xl h-[70vh] min-w-[320px] max-w-sm flex-1 overflow-hidden transition-colors"
            onDragOver={onDragOver}
            onDrop={(e) => onDrop(e, status)}
        >
            <div className={`px-4 py-3 border-b border-border font-medium text-sm flex items-center justify-between ${headerColor} border`}>
                <div className="flex items-center gap-2">
                    {status === 'todo' && <Clock className="w-4 h-4" />}
                    {status === 'in_progress' && <PlayCircle className="w-4 h-4" />}
                    {status === 'done' && <CheckCircle2 className="w-4 h-4" />}
                    {colTitle}
                </div>
                <span className="bg-muted/50 text-xs px-2 py-0.5 rounded-full">{columnTasks.length}</span>
            </div>

            <div className="flex-1 p-3 overflow-y-auto custom-scrollbar space-y-3">
                {columnTasks.map(task => (
                    <div
                        key={task.id}
                        draggable
                        onDragStart={(e) => onDragStart(e, task)}
                        onDragEnd={onDragEnd}
                        className="bg-muted border border-border p-3.5 rounded-xl cursor-grab shadow-sm shadow-black/20 hover:border-border hover:bg-muted transition-all group"
                    >
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-[10px] font-mono text-muted-foreground uppercase px-1.5 py-0.5 bg-muted rounded">
                                {task.id.slice(0, 6)}
                            </span>
                            <div className="relative" onClick={e => e.stopPropagation()}>
                                <button
                                    onClick={() => setOpenMenuId(openMenuId === task.id ? null : task.id)}
                                    className="text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-accent"
                                >
                                    <MoreHorizontal className="w-4 h-4" />
                                </button>
                                {openMenuId === task.id && (
                                    <div className="absolute right-0 top-6 w-36 bg-muted border border-border rounded-xl shadow-xl overflow-hidden z-20">
                                        <button
                                            onClick={() => onEditOpen(task)}
                                            className="flex items-center gap-2 w-full px-3 py-2 text-xs text-foreground hover:bg-accent/50 transition-colors"
                                        >
                                            <Pencil className="w-3 h-3 text-muted-foreground" /> {tc("edit")}
                                        </button>
                                        <button
                                            onClick={() => onDelete(task)}
                                            className="flex items-center gap-2 w-full px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                                        >
                                            <Trash2 className="w-3 h-3" /> {tc("delete")}
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>

                        <h4 className="text-sm font-medium text-foreground mb-1 leading-snug">{task.title}</h4>

                        {task.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2 mb-3 leading-relaxed">
                                {task.description}
                            </p>
                        )}

                        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                            <div className="flex -space-x-1.5">
                                <div className="w-6 h-6 rounded-full bg-primary/20 border border-border flex items-center justify-center text-[10px] text-primary font-bold" title={t("kanbanColumn.aiAssigneeTitle")}>
                                    IA
                                </div>
                                {task.assignee_id && (
                                    <div className="w-6 h-6 rounded-full bg-accent border border-border flex items-center justify-center text-[10px] text-foreground font-bold" title={t("kanbanColumn.humanAssigneeTitle")}>
                                        HM
                                    </div>
                                )}
                            </div>
                            {task.due_date && (
                                <div className="flex items-center gap-1 text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                    <Calendar className="w-3 h-3" />
                                    {format(new Date(task.due_date), "MMM d")}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {columnTasks.length === 0 && (
                    <div className="h-full w-full border-2 border-dashed border-border rounded-xl flex items-center justify-center text-muted-foreground text-xs font-medium">
                        {t("kanbanColumn.dropHint")}
                    </div>
                )}
            </div>
        </div>
    );
}
