import { useCallback, useEffect, useState } from "react";

import { api, type User, type UserCreate, type UserUpdate } from "@/lib/api";

export function useUsuarios() {
    const [users, setUsers] = useState<User[]>([]);
    const [me, setMe] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [list, current] = await Promise.all([api.users.list(), api.users.me()]);
            setUsers(list);
            setMe(current);
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

    return { users, me, loading, error, busyId, reload: load, create, update, remove };
}
