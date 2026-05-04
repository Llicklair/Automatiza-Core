"use client";

import { useState } from "react";

import { Loader2, Plus, Trash2, ShieldCheck, ShieldOff, X } from "lucide-react";

import type { User, UserCreate } from "@/lib/api";

import { useUsuarios } from "./_hooks/useUsuarios";

const ROLES = ["admin", "user"] as const;

export default function UsuariosConfigPage() {
    const { users, me, loading, error, busyId, create, update, remove } = useUsuarios();
    const [showCreate, setShowCreate] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);

    const isSelf = (u: User) => me?.id === u.id;

    async function handleCreate(data: UserCreate) {
        setActionError(null);
        try {
            await create(data);
            setShowCreate(false);
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo crear el usuario");
        }
    }

    async function handleToggleActive(u: User) {
        setActionError(null);
        try {
            await update(u.id, { is_active: !u.is_active });
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo actualizar el usuario");
        }
    }

    async function handleChangeRole(u: User, role: string) {
        setActionError(null);
        try {
            await update(u.id, { role });
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo cambiar el rol");
        }
    }

    async function handleDelete(u: User) {
        if (!confirm(`¿Eliminar al usuario ${u.email}? Esta acción es irreversible.`)) return;
        setActionError(null);
        try {
            await remove(u.id);
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo eliminar");
        }
    }

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-1">Usuarios del tenant</h1>
                    <p className="text-muted-foreground text-sm mt-2">
                        Gestiona el acceso de tu equipo a esta organización. Solo administradores pueden eliminar cuentas.
                    </p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm font-medium hover:opacity-90 shrink-0"
                >
                    <Plus className="w-4 h-4" />
                    Nuevo usuario
                </button>
            </div>

            {(error || actionError) && (
                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-sm text-destructive">
                    {error || actionError}
                </div>
            )}

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
                                            onChange={(e) => handleChangeRole(u, e.target.value)}
                                            disabled={busyId === u.id || isSelf(u)}
                                            className="bg-muted border border-border rounded-lg px-2 py-1 text-xs text-foreground disabled:opacity-50"
                                        >
                                            {ROLES.map((r) => (
                                                <option key={r} value={r}>{r}</option>
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
                                                onClick={() => handleToggleActive(u)}
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
                                                onClick={() => handleDelete(u)}
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

            {showCreate && (
                <NewUserModal
                    onCancel={() => setShowCreate(false)}
                    onSubmit={handleCreate}
                />
            )}
        </div>
    );
}

function NewUserModal({
    onCancel,
    onSubmit,
}: {
    onCancel: () => void;
    onSubmit: (data: UserCreate) => Promise<void>;
}) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [role, setRole] = useState<string>("user");
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await onSubmit({
                email: email.trim(),
                password,
                first_name: firstName.trim() || undefined,
                last_name: lastName.trim() || undefined,
                role,
            });
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6 space-y-5">
                <div className="flex items-start justify-between">
                    <h2 className="text-xl font-bold text-foreground">Nuevo usuario</h2>
                    <button onClick={onCancel} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <Field label="Email" required>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        />
                    </Field>

                    <Field label="Contraseña" required>
                        <input
                            type="password"
                            required
                            minLength={8}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        />
                    </Field>

                    <div className="grid grid-cols-2 gap-3">
                        <Field label="Nombre">
                            <input
                                type="text"
                                value={firstName}
                                onChange={(e) => setFirstName(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                            />
                        </Field>
                        <Field label="Apellidos">
                            <input
                                type="text"
                                value={lastName}
                                onChange={(e) => setLastName(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                            />
                        </Field>
                    </div>

                    <Field label="Rol">
                        <select
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        >
                            {ROLES.map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </Field>

                    <div className="flex items-center justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="px-4 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={submitting}
                            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm font-medium hover:opacity-90 disabled:opacity-50"
                        >
                            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                            Crear usuario
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

function Field({
    label,
    required,
    children,
}: {
    label: string;
    required?: boolean;
    children: React.ReactNode;
}) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {label} {required && <span className="text-destructive">*</span>}
            </label>
            {children}
        </div>
    );
}
