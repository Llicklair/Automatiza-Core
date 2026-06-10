"use client";

import { useState } from "react";

import {
    Loader2, Plus, Trash2, ShieldCheck, ShieldOff, X,
    Mail, Copy, Check,
} from "lucide-react";

import type { Invitation, InvitationCreated, User, UserCreate } from "@/lib/api";
import { showConfirm } from "@/stores/confirm";

import { useUsuarios } from "./_hooks/useUsuarios";
import { useLanAccess } from "./_hooks/useLanAccess";
import PortalAccessCard from "./_components/PortalAccessCard";

const USER_ROLES = ["admin", "user"] as const;
const INVITE_ROLES = ["employee", "user", "admin"] as const;

const ROLE_LABEL: Record<string, string> = {
    admin: "Admin",
    user: "Usuario",
    viewer: "Solo lectura",
    employee: "Empleado (solo Mi portal)",
};

function buildShareUrl(token: string, base?: string | null): string {
    // En la app de escritorio, window.location.origin es localhost (no sirve en
    // el móvil del empleado). Si tenemos la base de LAN, se usa esa.
    const origin = base || (typeof window === "undefined" ? "" : window.location.origin);
    return `${origin}/aceptar-invitacion/${token}`;
}

export default function UsuariosConfigPage() {
    const {
        users, invitations, me, loading, error, busyId,
        create, update, remove, invite, revokeInvitation,
    } = useUsuarios();
    const [showCreate, setShowCreate] = useState(false);
    const [showInvite, setShowInvite] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);
    const [shareInvitation, setShareInvitation] = useState<InvitationCreated | null>(null);
    const lan = useLanAccess();

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

    async function handleInvite(email: string, role: string, ttl_days: number) {
        setActionError(null);
        try {
            const created = await invite({ email, role, ttl_days });
            setShowInvite(false);
            setShareInvitation(created);
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo crear la invitación");
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
        if (!(await showConfirm({
            message: `¿Eliminar al usuario ${u.email}? Esta acción es irreversible.`,
            confirmLabel: "Eliminar",
            confirmVariant: "danger",
        }))) return;
        setActionError(null);
        try {
            await remove(u.id);
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo eliminar");
        }
    }

    async function handleRevoke(inv: Invitation) {
        if (!(await showConfirm({
            message: `¿Revocar la invitación a ${inv.email}?`,
            confirmLabel: "Revocar",
            confirmVariant: "danger",
        }))) return;
        setActionError(null);
        try {
            await revokeInvitation(inv.id);
        } catch (e) {
            setActionError(e instanceof Error ? e.message : "No se pudo revocar");
        }
    }

    const pendingInvitations = invitations.filter((i) => i.status === "pending");

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-1">Usuarios del tenant</h1>
                    <p className="text-muted-foreground text-sm mt-2">
                        Invita por email para que cada persona ponga su propia contraseña, o crea cuentas con contraseña directa. Los empleados con rol &quot;Empleado&quot; solo verán Mi portal.
                    </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <button
                        onClick={() => setShowInvite(true)}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm font-medium hover:opacity-90"
                    >
                        <Mail className="w-4 h-4" />
                        Invitar por email
                    </button>
                    <button
                        onClick={() => setShowCreate(true)}
                        className="flex items-center gap-2 bg-muted border border-border text-foreground px-4 py-2 rounded-xl text-sm font-medium hover:bg-muted/70"
                    >
                        <Plus className="w-4 h-4" />
                        Crear con contraseña
                    </button>
                </div>
            </div>

            {(error || actionError) && (
                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-sm text-destructive">
                    {error || actionError}
                </div>
            )}

            {/* Invitaciones pendientes */}
            {pendingInvitations.length > 0 && (
                <section className="space-y-2">
                    <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Invitaciones pendientes ({pendingInvitations.length})
                    </h2>
                    <div className="bg-card border border-border rounded-2xl overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                                    <th className="text-left font-medium px-5 py-3">Email</th>
                                    <th className="text-left font-medium px-5 py-3">Rol</th>
                                    <th className="text-left font-medium px-5 py-3">Caduca</th>
                                    <th className="text-right font-medium px-5 py-3">Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pendingInvitations.map((inv) => (
                                    <tr key={inv.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                                        <td className="px-5 py-3 text-foreground">{inv.email}</td>
                                        <td className="px-5 py-3 text-muted-foreground">{ROLE_LABEL[inv.role] ?? inv.role}</td>
                                        <td className="px-5 py-3 text-muted-foreground text-xs">
                                            {new Date(inv.expires_at).toLocaleString()}
                                        </td>
                                        <td className="px-5 py-3">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => handleRevoke(inv)}
                                                    disabled={busyId === inv.id}
                                                    title="Revocar"
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
                    </div>
                </section>
            )}

            {/* Usuarios */}
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
                                                onChange={(e) => handleChangeRole(u, e.target.value)}
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
            </section>

            <PortalAccessCard lan={lan} />

            {showCreate && (
                <NewUserModal
                    onCancel={() => setShowCreate(false)}
                    onSubmit={handleCreate}
                />
            )}

            {showInvite && (
                <NewInvitationModal
                    onCancel={() => setShowInvite(false)}
                    onSubmit={handleInvite}
                />
            )}

            {shareInvitation && (
                <ShareInvitationModal
                    invitation={shareInvitation}
                    lanBase={lan.lanBase}
                    onClose={() => setShareInvitation(null)}
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
        <Modal title="Crear usuario con contraseña" onClose={onCancel}>
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
                        {USER_ROLES.map((r) => (
                            <option key={r} value={r}>{ROLE_LABEL[r] ?? r}</option>
                        ))}
                    </select>
                </Field>

                <ModalActions onCancel={onCancel} submitting={submitting} submitLabel="Crear usuario" />
            </form>
        </Modal>
    );
}

function NewInvitationModal({
    onCancel,
    onSubmit,
}: {
    onCancel: () => void;
    onSubmit: (email: string, role: string, ttl_days: number) => Promise<void>;
}) {
    const [email, setEmail] = useState("");
    const [role, setRole] = useState<string>("employee");
    const [ttlDays, setTtlDays] = useState<number>(7);
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await onSubmit(email.trim(), role, ttlDays);
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <Modal title="Invitar por email" onClose={onCancel}>
            <p className="text-xs text-muted-foreground -mt-1">
                Genera un enlace de invitación. Tras crearlo te lo mostraremos para que lo copies y lo envíes a la persona como prefieras.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
                <Field label="Email del invitado" required>
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        placeholder="empleado@empresa.com"
                    />
                </Field>

                <Field label="Rol al aceptar">
                    <select
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        {INVITE_ROLES.map((r) => (
                            <option key={r} value={r}>{ROLE_LABEL[r] ?? r}</option>
                        ))}
                    </select>
                </Field>

                <Field label="Caducidad">
                    <select
                        value={ttlDays}
                        onChange={(e) => setTtlDays(Number(e.target.value))}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                    >
                        <option value={1}>1 día</option>
                        <option value={3}>3 días</option>
                        <option value={7}>7 días (recomendado)</option>
                        <option value={14}>14 días</option>
                        <option value={30}>30 días</option>
                    </select>
                </Field>

                <ModalActions onCancel={onCancel} submitting={submitting} submitLabel="Generar enlace" />
            </form>
        </Modal>
    );
}

function ShareInvitationModal({
    invitation,
    lanBase,
    onClose,
}: {
    invitation: InvitationCreated;
    lanBase?: string | null;
    onClose: () => void;
}) {
    const [copied, setCopied] = useState(false);
    // Si hay red local, el enlace usa la IP de LAN para que funcione en el móvil
    // del empleado (no localhost, que solo vale en este ordenador).
    const url = buildShareUrl(invitation.token, lanBase);

    async function copy() {
        try {
            await navigator.clipboard.writeText(url);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback: select the input
        }
    }

    return (
        <Modal title="Enlace de invitación generado" onClose={onClose}>
            <div className="space-y-4">
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
                    <strong>Importante:</strong> este enlace solo se muestra una vez. Cópialo ahora y envíalo a {invitation.email} por el medio que prefieras.
                </div>

                <Field label="Enlace para compartir">
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            readOnly
                            value={url}
                            onClick={(e) => e.currentTarget.select()}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 font-mono text-xs text-foreground focus:border-primary/20 outline-none"
                        />
                        <button
                            type="button"
                            onClick={copy}
                            className="flex items-center gap-1 bg-primary text-primary-foreground px-3 py-2.5 rounded-xl text-sm font-medium hover:opacity-90 shrink-0"
                        >
                            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                            {copied ? "Copiado" : "Copiar"}
                        </button>
                    </div>
                </Field>

                <div className="flex items-center justify-end pt-1">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 rounded-xl text-sm bg-muted border border-border text-foreground hover:bg-muted/70"
                    >
                        Hecho
                    </button>
                </div>
            </div>
        </Modal>
    );
}

function Modal({
    title,
    children,
    onClose,
}: {
    title: string;
    children: React.ReactNode;
    onClose: () => void;
}) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6 space-y-5">
                <div className="flex items-start justify-between">
                    <h2 className="text-xl font-bold text-foreground">{title}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                {children}
            </div>
        </div>
    );
}

function ModalActions({
    onCancel,
    submitting,
    submitLabel,
}: {
    onCancel: () => void;
    submitting: boolean;
    submitLabel: string;
}) {
    return (
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
                {submitLabel}
            </button>
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
