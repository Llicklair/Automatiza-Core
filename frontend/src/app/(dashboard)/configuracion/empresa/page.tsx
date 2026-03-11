"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Loader2, Save } from "lucide-react";

export default function EmpresaConfigPage() {
    const [name, setName] = useState("");
    const [nif, setNif] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        let mounted = true;
        api.tenant.me()
            .then((t) => {
                if (!mounted) return;
                setName(t.name);
                setNif(t.nif);
            })
            .catch((e: any) => {
                if (!mounted) return;
                setError(e?.message || "Error cargando datos de la empresa");
            })
            .finally(() => {
                if (mounted) setLoading(false);
            });
        return () => { mounted = false; };
    }, []);

    async function handleSave(e: React.FormEvent) {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        try {
            setSaving(true);
            const updated = await api.tenant.updateMe({ name, nif });
            setName(updated.name);
            setNif(updated.nif);
            setSuccess("Datos de empresa guardados correctamente.");
        } catch (e: any) {
            setError(e?.message || "No se pudo guardar la empresa");
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white mb-1">Datos de mi empresa</h1>
                <p className="text-zinc-400 text-sm">
                    Esta información se usa como emisor en las facturas y PDFs generados.
                </p>
            </div>

            <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6">
                {loading ? (
                    <div className="flex items-center justify-center gap-2 text-zinc-400 py-10">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Cargando datos de empresa…
                    </div>
                ) : (
                    <form onSubmit={handleSave} className="space-y-5">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                                Nombre / Razón social
                            </label>
                            <input
                                type="text"
                                required
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none"
                                placeholder="Mi Empresa S.L."
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                                NIF / CIF
                            </label>
                            <input
                                type="text"
                                required
                                value={nif}
                                onChange={(e) => setNif(e.target.value.toUpperCase())}
                                className="w-full bg-black/40 border border-[#27272a] rounded-xl px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 outline-none uppercase"
                                placeholder="B12345678"
                            />
                        </div>

                        {error && (
                            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">
                                {error}
                            </p>
                        )}
                        {success && (
                            <p className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2">
                                {success}
                            </p>
                        )}

                        <div className="pt-3 border-t border-[#27272a] flex justify-end">
                            <button
                                type="submit"
                                disabled={saving}
                                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition shadow-lg shadow-indigo-500/20"
                            >
                                {saving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Guardando…
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4" />
                                        Guardar cambios
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

