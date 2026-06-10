"use client";

import { useState } from "react";

import { Plus, Mail } from "lucide-react";

import type { Invitation, InvitationCreated, User, UserCreate } from "@/lib/api";
import { showConfirm } from "@/stores/confirm";

import { useUsuarios } from "./_hooks/useUsuarios";
import { useLanAccess } from "./_hooks/useLanAccess";
import PortalAccessCard from "./_components/PortalAccessCard";
import PendingInvitationsTable from "./_components/PendingInvitationsTable";
import UsersTable from "./_components/UsersTable";
import NewUserModal from "./_components/NewUserModal";
import NewInvitationModal from "./_components/NewInvitationModal";
import ShareInvitationModal from "./_components/ShareInvitationModal";

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
                <PendingInvitationsTable
                    invitations={pendingInvitations}
                    busyId={busyId}
                    onRevoke={handleRevoke}
                />
            )}

            {/* Usuarios */}
            <UsersTable
                users={users}
                loading={loading}
                busyId={busyId}
                isSelf={isSelf}
                onChangeRole={handleChangeRole}
                onToggleActive={handleToggleActive}
                onDelete={handleDelete}
            />

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
