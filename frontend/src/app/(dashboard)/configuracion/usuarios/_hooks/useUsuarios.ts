import { useCallback, useEffect, useState } from "react";

import {
    api,
    type Invitation,
    type InvitationCreate,
    type InvitationCreated,
    type User,
    type UserCreate,
    type UserUpdate,
} from "@/lib/api";

export function useUsuarios() {
    const [users, setUsers] = useState<User[]>([]);
    const [invitations, setInvitations] = useState<Invitation[]>([]);
    const [me, setMe] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [list, current, invs] = await Promise.all([
                api.users.list(),
                api.users.me(),
                api.users.invitations.list(),
            ]);
            setUsers(list);
            setMe(current);
            setInvitations(invs);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Error cargando usuarios");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void load();
    }, [load]);

    const create = useCallback(async (data: UserCreate) => {
        const created = await api.users.create(data);
        setUsers((prev) => [...prev, created]);
        return created;
    }, []);

    const update = useCallback(async (id: string, data: UserUpdate) => {
        setBusyId(id);
        try {
            const updated = await api.users.update(id, data);
            setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
            return updated;
        } finally {
            setBusyId(null);
        }
    }, []);

    const remove = useCallback(async (id: string) => {
        setBusyId(id);
        try {
            await api.users.delete(id);
            setUsers((prev) => prev.filter((u) => u.id !== id));
        } finally {
            setBusyId(null);
        }
    }, []);

    const invite = useCallback(async (data: InvitationCreate): Promise<InvitationCreated> => {
        const created = await api.users.invitations.create(data);
        // The list response doesn't include the raw token; strip it for the local list.
        const { token: _t, ...listEntry } = created;
        setInvitations((prev) => [listEntry as Invitation, ...prev]);
        return created;
    }, []);

    const revokeInvitation = useCallback(async (id: string) => {
        setBusyId(id);
        try {
            await api.users.invitations.revoke(id);
            setInvitations((prev) =>
                prev.map((i) =>
                    i.id === id
                        ? { ...i, used_at: new Date().toISOString(), status: "used" as const }
                        : i
                )
            );
        } finally {
            setBusyId(null);
        }
    }, []);

    return {
        users,
        invitations,
        me,
        loading,
        error,
        busyId,
        reload: load,
        create,
        update,
        remove,
        invite,
        revokeInvitation,
    };
}
