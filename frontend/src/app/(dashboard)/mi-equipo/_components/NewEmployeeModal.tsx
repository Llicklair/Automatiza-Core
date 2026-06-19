"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { surfaceIfConnectivity } from "@/lib/api/errors";
import { X, Loader2, Sparkles } from "lucide-react";

export function NewEmployeeModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void; }) {
    const t = useTranslations("miEquipo");
    const tc = useTranslations("common");
    const [nombre, setNombre] = useState("");
    const [apellidos, setApellidos] = useState("");
    const [rol, setRol] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleCreate = async () => {
        if (!rol.trim()) { setError(t("newEmployeeModal.errorRoleRequired")); return; }
        const fullName = [nombre.trim(), apellidos.trim()].filter(Boolean).join(" ")
            || t("newEmployeeModal.defaultAgentName", { role: rol.trim() });
        setLoading(true); setError(null);
        try {
            await api.aiEmployees.create({
                name: fullName,
                role_description: rol.trim(),
            });
            onCreated(); onClose();
        } catch (e: any) {
            if (surfaceIfConnectivity(e)) return;
            setError(e?.message ?? t("newEmployeeModal.errorCreate"));
        }
        finally { setLoading(false); }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 overflow-y-auto">
            <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4 my-8">
                <div className="flex items-center justify-between">
                    <h2 className="font-semibold text-foreground text-sm">{t("newEmployeeModal.title")}</h2>
                    <button onClick={onClose} className="p-1 hover:bg-muted rounded-lg" aria-label={tc("close")}><X className="w-4 h-4 text-muted-foreground" aria-hidden="true" /></button>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">{t("newEmployeeModal.firstNameLabel")}</label>
                        <input value={nombre} onChange={e => setNombre(e.target.value)} placeholder={t("newEmployeeModal.firstNamePlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">{t("newEmployeeModal.lastNameLabel")}</label>
                        <input value={apellidos} onChange={e => setApellidos(e.target.value)} placeholder={t("newEmployeeModal.lastNamePlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
                    </div>
                </div>
                <p className="text-xs text-muted-foreground -mt-2">{t("newEmployeeModal.nameHint")}</p>

                <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">{t("newEmployeeModal.roleLabel")}</label>
                    <input
                        value={rol}
                        onChange={e => setRol(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleCreate()}
                        placeholder={t("newEmployeeModal.rolePlaceholder")}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                    />
                </div>

                <div className="flex items-start gap-2.5 p-3 bg-violet-500/5 border border-violet-500/20 rounded-xl">
                    <Sparkles className="w-3.5 h-3.5 text-violet-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        {t("newEmployeeModal.coordinatorHint")}
                    </p>
                </div>

                {error && <p className="text-xs text-red-400">{error}</p>}
                <div className="flex justify-end gap-2 pt-1">
                    <button onClick={onClose} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg">{tc("cancel")}</button>
                    <button onClick={handleCreate} disabled={loading || !rol.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        {loading ? t("newEmployeeModal.creating") : t("newEmployeeModal.createButton")}
                    </button>
                </div>
            </div>
        </div>
    );
}
