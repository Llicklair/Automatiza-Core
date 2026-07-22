"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { X, Search, UserPlus, Printer, Loader2, Minus, Plus, ShoppingBag, UserCheck } from "lucide-react";
import { api, type Product, type Client } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { printTicket } from "@/lib/print/ticket";
import { getPrinterSettings } from "@/lib/print/printerSettings";
import { useToastStore } from "@/stores/toast";

/** Modo mostrador (tintorería T3): crear el albarán-resguardo casi sin teclear.
 * Catálogo táctil con iconos, buscador único de cliente (NIF/teléfono/nombre)
 * con alta exprés, notas, y "Generar" → crea en estado `recibido` + imprime. */

interface Linea {
    product_id: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
}

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export function MostradorModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
    const t = useTranslations("albaranes");
    const toast = useToastStore();
    const [products, setProducts] = useState<Product[]>([]);
    const [cat, setCat] = useState("");
    const [clienteQ, setClienteQ] = useState("");
    const [resultados, setResultados] = useState<Client[]>([]);
    const [cliente, setCliente] = useState<Client | null>(null);
    const [showAlta, setShowAlta] = useState(false);
    const [altaNombre, setAltaNombre] = useState("");
    const [altaTel, setAltaTel] = useState("");
    const [lineas, setLineas] = useState<Linea[]>([]);
    const [notas, setNotas] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        api.erp.products
            .list({ limit: 200, is_active: true })
            .then(setProducts)
            .catch(() => {});
    }, []);

    // Buscador único con debounce: nombre / NIF / teléfono / email.
    useEffect(() => {
        if (!clienteQ.trim() || cliente) {
            setResultados([]);
            return;
        }
        const id = setTimeout(() => {
            api.erp.clients
                .list({ q: clienteQ.trim(), limit: 8 })
                .then(setResultados)
                .catch(() => {});
        }, 250);
        return () => clearTimeout(id);
    }, [clienteQ, cliente]);

    const categorias = useMemo(
        () => Array.from(new Set(products.map((p) => p.category).filter(Boolean))) as string[],
        [products],
    );
    const visibles = useMemo(() => (cat ? products.filter((p) => p.category === cat) : products), [products, cat]);

    const addProducto = (p: Product) => {
        setLineas((prev) => {
            const i = prev.findIndex((l) => l.product_id === p.id);
            if (i >= 0) {
                const c = [...prev];
                c[i] = { ...c[i], quantity: c[i].quantity + 1 };
                return c;
            }
            return [
                ...prev,
                {
                    product_id: p.id,
                    description: p.name,
                    quantity: 1,
                    unit_price: Number(p.price) || 0,
                    tax_percentage: Number(p.tax_percentage ?? 21),
                },
            ];
        });
    };

    const cambiarQty = (idx: number, delta: number) =>
        setLineas((prev) =>
            prev.flatMap((l, i) =>
                i !== idx ? [l] : l.quantity + delta <= 0 ? [] : [{ ...l, quantity: l.quantity + delta }],
            ),
        );

    const total = lineas.reduce((s, l) => s + l.quantity * l.unit_price * (1 + l.tax_percentage / 100), 0);

    const crearClienteExpres = async () => {
        if (!altaNombre.trim()) return;
        try {
            const nuevo = await api.erp.clients.create({ name: altaNombre.trim(), phone: altaTel.trim() || null });
            setCliente(nuevo);
            setShowAlta(false);
            setClienteQ("");
        } catch (e: any) {
            toast.error(e?.message || t("mostrador.altaError"));
        }
    };

    const generar = async () => {
        if (lineas.length === 0 || saving) return;
        setSaving(true);
        try {
            const albaran = await api.albaranes.create({
                client_id: cliente?.id,
                notes: notas || undefined,
                lines: lineas.map((l) => ({
                    product_id: l.product_id ?? undefined,
                    description: l.description,
                    quantity: l.quantity,
                    unit_price: l.unit_price,
                    tax_percentage: l.tax_percentage,
                })),
            });
            // El mostrador recibe prendas: el albarán nace "recibido", no borrador.
            await api.albaranes.updateStatus(albaran.id, "recibido");
            try {
                const html = await api.albaranes.ticketHtml(albaran.id);
                const settings = getPrinterSettings();
                await printTicket(html, { silent: settings.autoPrint, deviceName: settings.deviceName });
            } catch {
                toast.error(t("mostrador.printError"));
            }
            toast.success(t("mostrador.creado", { number: albaran.albaran_number }));
            onCreated();
            onClose();
        } catch (e: any) {
            toast.error(e?.message || t("mostrador.error"));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-5xl h-[92vh] flex flex-col overflow-hidden">
                <div className="px-5 py-3 flex items-center justify-between border-b border-border shrink-0">
                    <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                        <ShoppingBag className="w-4 h-4 text-cyan-400" aria-hidden="true" /> {t("mostrador.title")}
                    </h2>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose} aria-label={t("mostrador.close")}>
                        <X className="w-4 h-4" aria-hidden="true" />
                    </Button>
                </div>

                <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-[1fr_340px]">
                    {/* Izquierda: cliente + catálogo táctil */}
                    <div className="p-4 overflow-y-auto space-y-4">
                        {/* Cliente */}
                        {cliente ? (
                            <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-2.5">
                                <div className="flex items-center gap-2 text-sm text-foreground">
                                    <UserCheck className="w-4 h-4 text-emerald-400" aria-hidden="true" />
                                    <span className="font-medium">{cliente.name}</span>
                                    {cliente.phone && <span className="text-muted-foreground">· {cliente.phone}</span>}
                                </div>
                                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setCliente(null)}>
                                    {t("mostrador.cambiar")}
                                </Button>
                            </div>
                        ) : (
                            <div className="relative">
                                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                                <Input
                                    value={clienteQ}
                                    onChange={(e) => setClienteQ(e.target.value)}
                                    placeholder={t("mostrador.buscarCliente")}
                                    className="pl-9 h-11 text-base"
                                    autoFocus
                                />
                                {clienteQ.trim() && (
                                    <div className="absolute z-10 mt-1 w-full bg-card border border-border rounded-xl shadow-xl overflow-hidden">
                                        {resultados.map((c) => (
                                            <button
                                                key={c.id}
                                                onClick={() => { setCliente(c); setClienteQ(""); }}
                                                className="w-full text-left px-4 py-2.5 hover:bg-muted text-sm text-foreground flex justify-between"
                                            >
                                                <span>{c.name}</span>
                                                <span className="text-muted-foreground text-xs">{c.phone || c.nif || ""}</span>
                                            </button>
                                        ))}
                                        <button
                                            onClick={() => { setShowAlta(true); setAltaNombre(clienteQ.trim()); }}
                                            className="w-full text-left px-4 py-2.5 hover:bg-muted text-sm text-cyan-400 flex items-center gap-2"
                                        >
                                            <UserPlus className="w-3.5 h-3.5" aria-hidden="true" /> {t("mostrador.altaExpres")}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}

                        {showAlta && (
                            <div className="flex flex-wrap items-end gap-2 bg-muted/40 border border-border rounded-xl p-3">
                                <div className="flex-1 min-w-[140px]">
                                    <label className="text-xs text-muted-foreground block mb-1">{t("mostrador.nombre")}</label>
                                    <Input value={altaNombre} onChange={(e) => setAltaNombre(e.target.value)} className="h-9" />
                                </div>
                                <div className="flex-1 min-w-[120px]">
                                    <label className="text-xs text-muted-foreground block mb-1">{t("mostrador.telefono")}</label>
                                    <Input value={altaTel} onChange={(e) => setAltaTel(e.target.value)} className="h-9" />
                                </div>
                                <Button size="sm" onClick={crearClienteExpres} disabled={!altaNombre.trim()}>
                                    <UserPlus className="w-3.5 h-3.5 mr-1" aria-hidden="true" /> {t("mostrador.crear")}
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => setShowAlta(false)}>{t("mostrador.close")}</Button>
                            </div>
                        )}

                        {/* Categorías */}
                        {categorias.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                <button
                                    onClick={() => setCat("")}
                                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${!cat ? "bg-primary/15 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
                                >
                                    {t("mostrador.todas")}
                                </button>
                                {categorias.map((c) => (
                                    <button
                                        key={c}
                                        onClick={() => setCat(c === cat ? "" : c)}
                                        className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${cat === c ? "bg-primary/15 border-primary/40 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
                                    >
                                        {c}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Grid táctil */}
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                            {visibles.map((p) => (
                                <button
                                    key={p.id}
                                    onClick={() => addProducto(p)}
                                    className="bg-background border border-border rounded-xl p-3 text-center hover:border-cyan-500/50 hover:bg-muted active:scale-95 transition-all"
                                >
                                    <div className="text-3xl leading-none mb-1.5">
                                        {p.icon || (
                                            <span className="inline-flex w-9 h-9 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 text-sm font-bold">
                                                {p.name.substring(0, 2).toUpperCase()}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs font-medium text-foreground truncate">{p.name}</p>
                                    <p className="text-[11px] text-muted-foreground tabular-nums">{fmt(Number(p.price) || 0)}</p>
                                </button>
                            ))}
                            {visibles.length === 0 && (
                                <p className="col-span-full text-sm text-muted-foreground text-center py-8">{t("mostrador.sinProductos")}</p>
                            )}
                        </div>
                    </div>

                    {/* Derecha: resguardo en construcción */}
                    <div className="border-t md:border-t-0 md:border-l border-border flex flex-col min-h-0 bg-muted/20">
                        <div className="flex-1 overflow-y-auto p-4 space-y-1.5">
                            {lineas.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-10">{t("mostrador.vacio")}</p>
                            ) : (
                                lineas.map((l, i) => (
                                    <div key={i} className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm text-foreground truncate">{l.description}</p>
                                            <p className="text-[11px] text-muted-foreground tabular-nums">
                                                {fmt(l.unit_price * (1 + l.tax_percentage / 100))} / ud
                                            </p>
                                        </div>
                                        <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => cambiarQty(i, -1)} aria-label="-1">
                                            <Minus className="w-3 h-3" aria-hidden="true" />
                                        </Button>
                                        <span className="w-6 text-center text-sm font-mono tabular-nums">{l.quantity}</span>
                                        <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => cambiarQty(i, 1)} aria-label="+1">
                                            <Plus className="w-3 h-3" aria-hidden="true" />
                                        </Button>
                                    </div>
                                ))
                            )}
                        </div>
                        <div className="p-4 border-t border-border space-y-3 shrink-0">
                            <textarea
                                value={notas}
                                onChange={(e) => setNotas(e.target.value)}
                                placeholder={t("mostrador.notas")}
                                rows={2}
                                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50 resize-none"
                            />
                            <div className="flex justify-between text-base font-bold text-foreground">
                                <span>{t("mostrador.total")}</span>
                                <span className="tabular-nums">{fmt(total)}</span>
                            </div>
                            <Button className="w-full h-12 text-base" disabled={lineas.length === 0 || saving} onClick={generar}>
                                {saving ? (
                                    <Loader2 className="mr-2 w-4 h-4 animate-spin" aria-hidden="true" />
                                ) : (
                                    <Printer className="mr-2 w-4 h-4" aria-hidden="true" />
                                )}
                                {t("mostrador.generar")}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
