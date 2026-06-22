"use client";

import { useCallback, useEffect, useState } from "react";
import { Warehouse as WarehouseIcon, Plus, Loader2, Star, Pencil, Check, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { warehouses as whApi, type Warehouse } from "@/lib/api/warehouses";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const emptyForm = { name: "", code: "", address: "", is_default: false };

export default function WarehousesPage() {
    const t = useTranslations("inventario");
    const tc = useTranslations("common");
    const [items, setItems] = useState<Warehouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState(emptyForm);
    const [editId, setEditId] = useState<string | null>(null);
    const [editName, setEditName] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setItems(await whApi.list());
            setError(null);
        } catch (e: any) {
            setError(e?.message || t("warehouses.loadError"));
        }
        setLoading(false);
    }, [t]);

    useEffect(() => { load(); }, [load]);

    const create = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setSaving(true);
        try {
            await whApi.create({
                name: form.name.trim(),
                code: form.code.trim() || null,
                address: form.address.trim() || null,
                is_default: form.is_default,
            });
            setForm(emptyForm); setShowForm(false);
            await load();
        } catch (e: any) { setError(e?.message || t("warehouses.createError")); }
        setSaving(false);
    };

    const setDefault = async (id: string) => {
        try { await whApi.update(id, { is_default: true }); await load(); }
        catch (e: any) { setError(e?.message || tc("error")); }
    };

    const saveName = async (id: string) => {
        try { await whApi.update(id, { name: editName.trim() }); setEditId(null); await load(); }
        catch (e: any) { setError(e?.message || tc("error")); }
    };

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={t("warehouses.title")}
                description={t("warehouses.description")}
                icon={WarehouseIcon}
                actions={
                    <Button onClick={() => setShowForm(s => !s)}>
                        <Plus className="mr-2 h-4 w-4" /> {t("warehouses.newWarehouse")}
                    </Button>
                }
            />

            {error && <p className="text-sm text-rose-400">{error}</p>}

            {showForm && (
                <form onSubmit={create} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end rounded-lg border border-border bg-card p-4">
                    <div className="sm:col-span-2">
                        <Label className="text-xs">{t("warehouses.name")}</Label>
                        <Input className="mt-1" value={form.name} required
                            onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder={t("warehouses.namePlaceholder")} />
                    </div>
                    <div>
                        <Label className="text-xs">{t("warehouses.code")}</Label>
                        <Input className="mt-1" value={form.code}
                            onChange={e => setForm(f => ({ ...f, code: e.target.value }))} placeholder={t("warehouses.optional")} />
                    </div>
                    <div className="flex items-center gap-2 pb-2">
                        <input id="wh-def" type="checkbox" checked={form.is_default}
                            onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))} />
                        <Label htmlFor="wh-def" className="text-xs">{t("warehouses.default")}</Label>
                    </div>
                    <div className="sm:col-span-4 flex justify-end gap-2">
                        <Button type="button" variant="ghost" onClick={() => { setShowForm(false); setForm(emptyForm); }}>{tc("cancel")}</Button>
                        <Button type="submit" disabled={saving}>
                            {saving && <Loader2 className="mr-2 w-4 h-4 animate-spin" />} {tc("create")}
                        </Button>
                    </div>
                </form>
            )}

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> {tc("loading")}</div>
            ) : (
                <div className="rounded-lg border border-border bg-card overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium p-3">{t("warehouses.name")}</th>
                                <th className="text-left font-medium p-3">{t("warehouses.code")}</th>
                                <th className="text-left font-medium p-3">{t("warehouses.default")}</th>
                                <th className="text-right font-medium p-3"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map(w => (
                                <tr key={w.id} className="border-b border-border/40">
                                    <td className="p-3 text-foreground">
                                        {editId === w.id ? (
                                            <span className="flex items-center gap-1">
                                                <Input className="h-7" value={editName} onChange={e => setEditName(e.target.value)} />
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => saveName(w.id)} aria-label={t("warehouses.saveName")}><Check className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" /></Button>
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setEditId(null)} aria-label={t("warehouses.cancelEdit")}><X className="w-3.5 h-3.5" aria-hidden="true" /></Button>
                                            </span>
                                        ) : w.name}
                                    </td>
                                    <td className="p-3 font-mono text-muted-foreground">{w.code || "—"}</td>
                                    <td className="p-3">
                                        {w.is_default
                                            ? <span className="flex items-center gap-1 text-amber-400 text-xs"><Star className="w-3.5 h-3.5 fill-amber-400" /> {tc("yes")}</span>
                                            : <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setDefault(w.id)}>{t("warehouses.markDefault")}</Button>}
                                    </td>
                                    <td className="p-3 text-right">
                                        {editId !== w.id && (
                                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setEditId(w.id); setEditName(w.name); }} aria-label={t("warehouses.editName")}>
                                                <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                                            </Button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
