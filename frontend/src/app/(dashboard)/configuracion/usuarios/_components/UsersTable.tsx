"use client";

import { Loader2, Trash2, ShieldCheck, ShieldOff } from "lucide-react";

import type { User } from "@/lib/api";

import { INVITE_ROLES, ROLE_LABEL } from "../roles";

export default function UsersTable({
    users,
    loading,
    busyId,
    isSelf,
    onChangeRole,
    onToggleActive,
    onDelete,
}: {
    users: User[];
    loading: boolean;
    busyId: string | null;
    isSelf: (u: User) => boolean;
    onChangeRole: (u: User, role: string) => void;
    onToggleActive: (u: User) => void;
    onDelete: (u: User) => void;
}) {
    return (
        <section className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Usuarios activos ({users.length})
            </h2>
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center gap-2 text-muted-foreground py-12">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Cargando usuarios…
                    </div>
                ) : users.length === 0 ? (
                    <div className="text-center text-muted-foreground py-12 text-sm">
                        No hay usuarios todavía.
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                                <th className="text-left font-medium px-5 py-3">Email</th>
                                <th className="text-left font-medium px-5 py-3">Nombre</th>
                                <th className="text-left font-medium px-5 py-3">Rol</th>
                                <th className="text-left font-medium px-5 py-3">Estado</th>
                                <th className="text-right font-medium px-5 py-3">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => (
                                <tr key={u.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                                    <td className="px-5 py-3 text-foreground">
                                        {u.email}
                                        {isSelf(u) && (
                                            <span className="ml-2 text-xs text-primary">(tú)</span>
                                        )}
                                    </td>
                                    <td className="px-5 py-3 text-muted-foreground">{u.full_name || "—"}</td>
                                    <td className="px-5 py-3">
                                        <select
                                            value={u.role}
                                            onChange={(e) => onChangeRole(u, e.target.value)}
                                            disabled={busyId === u.id || isSelf(u)}
                                            className="bg-muted border border-border rounded-lg px-2 py-1 text-xs text-foreground disabled:opacity-50"
                                        >
                                            {INVITE_ROLES.map((r) => (
                                                <option key={r} value={r}>{ROLE_LABEL[r] ?? r}</option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="px-5 py-3">
                                        <span
                                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs ${
                                                u.is_active
                                                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                                    : "bg-muted text-muted-foreground border border-border"
                                            }`}
                                        >
                                            {u.is_active ? "Activo" : "Inactivo"}
                                        </span>
                                    </td>
                                    <td className="px-5 py-3">
                                        <div className="flex items-center justify-end gap-2">
                                            <button
                                                onClick={() => onToggleActive(u)}
                                                disabled={busyId === u.id || isSelf(u)}
                                                title={u.is_active ? "Desactivar" : "Activar"}
                                                className="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-40"
                                            >
                                                {u.is_active ? (
                                                    <ShieldOff className="w-4 h-4" />
                                                ) : (
                                                    <ShieldCheck className="w-4 h-4" />
                                                )}
                                            </button>
                                            <button
                                                onClick={() => onDelete(u)}
                                                disabled={busyId === u.id || isSelf(u)}
                                                title="Eliminar"
                                                className="p-1.5 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 disabled:opacity-40"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </section>
    );
}
