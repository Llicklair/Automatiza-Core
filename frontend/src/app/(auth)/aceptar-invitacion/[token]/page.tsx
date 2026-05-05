"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { Loader2, Check, AlertTriangle } from "lucide-react";

import { api, type InvitationPublic } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
    admin: "Administrador",
    user: "Usuario",
    viewer: "Solo lectura",
    employee: "Empleado (acceso a Mi portal)",
};

type State =
    | { kind: "loading" }
    | { kind: "ready"; invitation: InvitationPublic }
    | { kind: "error"; message: string };

export default function AceptarInvitacionPage() {
    const params = useParams<{ token: string }>();
    const router = useRouter();
    const token = params?.token ?? "";

    const [state, setState] = useState<State>({ kind: "loading" });
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);

    useEffect(() => {
        if (!token) {
            setState({ kind: "error", message: "Enlace inválido" });
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const inv = await api.users.invitations.getByToken(token);
                if (!cancelled) setState({ kind: "ready", invitation: inv });
            } catch (e) {
                if (!cancelled) {
                    setState({
                        kind: "error",
                        message:
                            e instanceof Error ? e.message : "No se pudo validar la invitación",
                    });
                }
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [token]);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (password.length < 8) {
            setSubmitError("La contraseña debe tener al menos 8 caracteres");
            return;
        }
        if (password !== confirmPassword) {
            setSubmitError("Las contraseñas no coinciden");
            return;
        }
        setSubmitError(null);
        setSubmitting(true);
        try {
            const res = await api.users.invitations.accept(token, {
                password,
                first_name: firstName.trim() || undefined,
                last_name: lastName.trim() || undefined,
            });
            localStorage.setItem("access_token", res.access_token);
            localStorage.setItem("refresh_token", res.refresh_token);
            document.cookie = "auth_flag=1; path=/; SameSite=Lax";
            const dest = res.user.role === "employee" ? "/portal" : "/";
            router.push(dest);
        } catch (e) {
            setSubmitError(e instanceof Error ? e.message : "No se pudo aceptar la invitación");
            setSubmitting(false);
        }
    }

    if (state.kind === "loading") {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Validando invitación…
                </div>
            </div>
        );
    }

    if (state.kind === "error") {
        return (
            <div className="min-h-screen flex items-center justify-center p-6">
                <div className="bg-card border border-border rounded-2xl p-8 max-w-md w-full text-center space-y-4">
                    <div className="w-12 h-12 rounded-xl bg-destructive/10 border border-destructive/20 flex items-center justify-center mx-auto">
                        <AlertTriangle className="w-6 h-6 text-destructive" />
                    </div>
                    <h1 className="text-xl font-bold text-foreground">Invitación no válida</h1>
                    <p className="text-sm text-muted-foreground">{state.message}</p>
                    <p className="text-xs text-muted-foreground">
                        Pide a tu administrador que te genere un nuevo enlace.
                    </p>
                </div>
            </div>
        );
    }

    const inv = state.invitation;

    return (
        <div className="min-h-screen flex items-center justify-center p-6">
            <div className="bg-card border border-border rounded-2xl p-8 max-w-md w-full space-y-6">
                <div className="space-y-1">
                    <h1 className="text-2xl font-bold text-foreground">Activa tu cuenta</h1>
                    <p className="text-sm text-muted-foreground">
                        Estás aceptando la invitación para <strong className="text-foreground">{inv.email}</strong>.
                    </p>
                    <p className="text-xs text-muted-foreground">
                        Rol: {ROLE_LABEL[inv.role] ?? inv.role} · Caduca el {new Date(inv.expires_at).toLocaleString()}
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
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

                    <Field label="Repite la contraseña" required>
                        <input
                            type="password"
                            required
                            minLength={8}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                        />
                    </Field>

                    {submitError && (
                        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-xl text-xs text-destructive">
                            {submitError}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting}
                        className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground px-4 py-2.5 rounded-xl text-sm font-medium hover:opacity-90 disabled:opacity-50"
                    >
                        {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                        Activar cuenta y entrar
                    </button>
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
