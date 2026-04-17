"use client";

import { X, Loader2 } from "lucide-react";

type FormState = { name: string; nif: string; email: string; address: string; city: string; postal_code: string };

interface Props {
    editingId: string | null;
    form: FormState;
    setForm: React.Dispatch<React.SetStateAction<FormState>>;
    saving: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
}

export function ProveedorModal({ editingId, form, setForm, saving, onClose, onSubmit }: Props) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-lg shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-bold text-foreground">{editingId ? "Editar proveedor" : "Nuevo proveedor"}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Nombre / Razón social *</label>
                            <input
                                type="text" required value={form.name}
                                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder="Proveedor S.L."
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">NIF / CIF</label>
                            <input
                                type="text" value={form.nif}
                                onChange={e => setForm(f => ({ ...f, nif: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder="B12345678"
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Email</label>
                            <input
                                type="email" value={form.email}
                                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder="proveedor@empresa.com"
                            />
                        </div>
                        <div className="col-span-2">
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Dirección</label>
                            <input
                                type="text" value={form.address}
                                onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder="Calle Mayor, 1"
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Ciudad</label>
                            <input
                                type="text" value={form.city}
                                onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder="Madrid"
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Código postal</label>
                            <input
                                type="text" value={form.postal_code}
                                onChange={e => setForm(f => ({ ...f, postal_code: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                placeholder="28001"
                            />
                        </div>
                    </div>
                    <div className="flex gap-3 pt-2">
                        <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">
                            Cancelar
                        </button>
                        <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                            {editingId ? "Guardar cambios" : "Crear proveedor"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
