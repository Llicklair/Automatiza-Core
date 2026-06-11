"use client";

import { Archive, X, Loader2 } from "lucide-react";
import { type FormState, emptyForm } from "../_hooks/useActivos";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const CATEGORIES = [
    { value: "equipment", label: "Equipos informáticos" },
    { value: "furniture", label: "Mobiliario e instalaciones" },
    { value: "vehicle", label: "Vehículos" },
    { value: "intangible", label: "Inmovilizado intangible" },
    { value: "other", label: "Otros activos" },
];

const ACCOUNT_CODES = [
    { code: "210", label: "210 — Terrenos y bienes naturales" },
    { code: "211", label: "211 — Construcciones" },
    { code: "212", label: "212 — Instalaciones técnicas" },
    { code: "213", label: "213 — Maquinaria" },
    { code: "214", label: "214 — Utillaje" },
    { code: "215", label: "215 — Otras instalaciones" },
    { code: "216", label: "216 — Mobiliario" },
    { code: "217", label: "217 — Equipos para procesos de información" },
    { code: "218", label: "218 — Elementos de transporte" },
    { code: "219", label: "219 — Otro inmovilizado material" },
    { code: "200", label: "200 — Investigación" },
    { code: "201", label: "201 — Desarrollo" },
    { code: "203", label: "203 — Propiedad industrial" },
    { code: "205", label: "205 — Derechos de traspaso" },
    { code: "206", label: "206 — Aplicaciones informáticas" },
];

interface Props {
    editingId: string | null;
    form: FormState;
    saving: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
    setField: (field: keyof FormState, val: string) => void;
}

export function AssetModal({ editingId, form, saving, onClose, onSubmit, setField }: Props) {
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted flex-shrink-0">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <Archive className="w-4 h-4 text-primary" />
                        {editingId ? "Editar Activo" : "Nuevo Activo Fijo"}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Cerrar formulario de activo">
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4 overflow-y-auto">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <label className="block text-sm text-muted-foreground mb-1.5">Nombre del activo *</label>
                            <input required type="text" value={form.name} onChange={e => setField("name", e.target.value)}
                                placeholder="Ej: MacBook Pro M3, Furgoneta de reparto"
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Categoría</label>
                            <select value={form.category} onChange={e => setField("category", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary">
                                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Cuenta PGC</label>
                            <select value={form.account_code} onChange={e => setField("account_code", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary">
                                {ACCOUNT_CODES.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Fecha de compra *</label>
                            <input required type="date" value={form.purchase_date} onChange={e => setField("purchase_date", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Valor de adquisición (€) *</label>
                            <input required type="number" min="0" step="0.01" value={form.purchase_value} onChange={e => setField("purchase_value", e.target.value)}
                                placeholder="0.00"
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Vida útil (años) *</label>
                            <input required type="number" min="1" max="100" step="0.5" value={form.useful_life_years} onChange={e => setField("useful_life_years", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Valor residual (€)</label>
                            <input type="number" min="0" step="0.01" value={form.residual_value} onChange={e => setField("residual_value", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Nº Factura / Referencia</label>
                            <input type="text" value={form.reference_invoice} onChange={e => setField("reference_invoice", e.target.value)}
                                placeholder="Opcional"
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary" />
                        </div>
                        <div className="col-span-2">
                            <label className="block text-sm text-muted-foreground mb-1.5">Descripción / Notas</label>
                            <textarea value={form.notes} onChange={e => setField("notes", e.target.value)}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary resize-none h-16" />
                        </div>
                    </div>

                    {form.purchase_value && form.useful_life_years && (
                        <div className="bg-primary/5 border border-primary/20 rounded-xl p-3 text-xs text-muted-foreground">
                            <span className="text-primary font-medium">Cuota mensual estimada: </span>
                            {fmt((parseFloat(form.purchase_value) - (parseFloat(form.residual_value) || 0)) / (parseFloat(form.useful_life_years) * 12))}
                            {" · "}Vida útil: {form.useful_life_years} años
                        </div>
                    )}

                    <div className="pt-2 flex justify-end gap-3">
                        <button type="button" onClick={onClose}
                            className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-border rounded-lg">
                            Cancelar
                        </button>
                        <button type="submit" disabled={saving || !form.name || !form.purchase_value}
                            className="inline-flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-primary/20 disabled:opacity-50">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                            {editingId ? "Guardar cambios" : "Añadir activo"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
