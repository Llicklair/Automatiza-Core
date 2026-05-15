"use client";

import { useState, useRef } from "react";
import {
    ShoppingCart, Search, Camera, Plus, Minus, X, Loader2, Power, AlertTriangle,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePos } from "./_hooks/usePos";
import { BarcodeScanner } from "./_components/BarcodeScanner";
import { PaymentModal } from "./_components/PaymentModal";
import { showConfirm } from "@/stores/confirm";

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);

export default function TpvPage() {
    const {
        session, loading, busy, checkoutOpen, setCheckoutOpen,
        subtotal, taxAmount, totalWithTax,
        openSession, addProductByCode, updateLineQuantity, removeLine,
        checkout, cancelSession,
    } = usePos();

    const [code, setCode] = useState("");
    const [scannerOpen, setScannerOpen] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleSubmitCode = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!code.trim()) return;
        await addProductByCode(code.trim());
        setCode("");
        inputRef.current?.focus();
    };

    const handleCancel = async () => {
        if (!session) return;
        const ok = await showConfirm({
            title: "Cancelar sesión",
            message: "Se descartarán todas las líneas del carrito. Esta acción no se puede deshacer.",
            confirmLabel: "Cancelar sesión",
            cancelLabel: "Volver",
            confirmVariant: "danger",
        });
        if (ok) await cancelSession();
    };

    // -- Sin sesión abierta --
    if (!loading && !session) {
        return (
            <div className="p-6 space-y-6 max-w-3xl mx-auto">
                <PageHeader
                    title="TPV"
                    description="Punto de venta — escanea productos, ajusta cantidades y cobra."
                    icon={ShoppingCart}
                />
                <div className="bg-card border border-border rounded-2xl p-10 text-center space-y-4">
                    <div className="w-12 h-12 mx-auto rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                        <ShoppingCart className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div>
                        <h2 className="text-base font-semibold text-foreground">Sin sesión abierta</h2>
                        <p className="text-sm text-muted-foreground mt-1">
                            Inicia una nueva sesión para empezar a vender.
                        </p>
                    </div>
                    <Button onClick={openSession} disabled={busy}>
                        {busy ? <Loader2 className="mr-2 w-4 h-4 animate-spin" /> : <Power className="mr-2 w-4 h-4" />}
                        Abrir sesión TPV
                    </Button>
                </div>
            </div>
        );
    }

    if (loading || !session) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[60vh]">
                <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-3rem)] p-6 gap-4">
            <PageHeader
                title="TPV"
                description={`Sesión #${session.id.slice(0, 8)} · abierta ${new Date(session.opened_at).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`}
                icon={ShoppingCart}
                actions={
                    <Button variant="outline" size="sm" onClick={handleCancel} disabled={busy}>
                        <X className="mr-1 w-3.5 h-3.5" /> Cancelar sesión
                    </Button>
                }
            />

            <div className="grid grid-cols-1 md:grid-cols-[1fr_400px] gap-4 flex-1 min-h-0">
                {/* Panel izquierdo: input + scan */}
                <div className="bg-card border border-border rounded-2xl p-5 space-y-4 overflow-auto">
                    <form onSubmit={handleSubmitCode} className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                            <Input
                                ref={inputRef}
                                type="text"
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                placeholder="Escanea con lector o escribe código de barras / SKU..."
                                className="pl-9"
                                autoFocus
                            />
                        </div>
                        <Button type="submit" disabled={busy || !code.trim()}>
                            <Plus className="w-4 h-4" />
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => setScannerOpen(true)}
                            disabled={busy}
                            title="Escanear con cámara"
                        >
                            <Camera className="w-4 h-4" />
                        </Button>
                    </form>

                    <div className="text-xs text-muted-foreground space-y-1">
                        <p>· Usa un lector USB/Bluetooth: dispara automáticamente al escanear.</p>
                        <p>· O pulsa la cámara para leer con el móvil.</p>
                        <p>· Si añades un producto que ya está en el carrito, suma 1 a la cantidad.</p>
                    </div>
                </div>

                {/* Panel derecho: carrito + totales */}
                <div className="bg-card border border-border rounded-2xl flex flex-col overflow-hidden">
                    <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <ShoppingCart className="w-4 h-4 text-muted-foreground" />
                            <h3 className="text-sm font-medium text-foreground">
                                Carrito
                                <span className="ml-2 text-xs text-muted-foreground">
                                    ({session.lines.length} {session.lines.length === 1 ? "línea" : "líneas"})
                                </span>
                            </h3>
                        </div>
                    </div>

                    <div className="flex-1 overflow-auto">
                        {session.lines.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">
                                <ShoppingCart className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                Carrito vacío. Escanea o introduce un código para empezar.
                            </div>
                        ) : (
                            <ul className="divide-y divide-border">
                                {session.lines.map((line) => (
                                    <li key={line.id} className="p-3 space-y-1.5">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-foreground truncate">
                                                    {line.description}
                                                </p>
                                                <p className="text-xs text-muted-foreground tabular-nums">
                                                    {fmt(Number(line.unit_price))} · IVA {Number(line.tax_percentage)}%
                                                </p>
                                            </div>
                                            <p className="text-sm font-semibold text-foreground tabular-nums whitespace-nowrap">
                                                {fmt(Number(line.total))}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <Button
                                                variant="outline"
                                                size="icon"
                                                className="h-6 w-6"
                                                onClick={() => updateLineQuantity(line.id, line.quantity - 1)}
                                                disabled={busy || line.quantity <= 1}
                                            >
                                                <Minus className="w-3 h-3" />
                                            </Button>
                                            <span className="text-sm font-mono tabular-nums w-8 text-center">
                                                {line.quantity}
                                            </span>
                                            <Button
                                                variant="outline"
                                                size="icon"
                                                className="h-6 w-6"
                                                onClick={() => updateLineQuantity(line.id, line.quantity + 1)}
                                                disabled={busy}
                                            >
                                                <Plus className="w-3 h-3" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-6 w-6 ml-auto text-destructive hover:text-destructive"
                                                onClick={() => removeLine(line.id)}
                                                disabled={busy}
                                            >
                                                <X className="w-3.5 h-3.5" />
                                            </Button>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    <div className="border-t border-border p-4 space-y-2 bg-muted/30">
                        <div className="flex justify-between text-xs text-muted-foreground">
                            <span>Subtotal</span>
                            <span className="tabular-nums">{fmt(subtotal)}</span>
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground">
                            <span>IVA</span>
                            <span className="tabular-nums">{fmt(taxAmount)}</span>
                        </div>
                        <div className="flex justify-between text-base font-bold text-foreground pt-1 border-t border-border">
                            <span>Total</span>
                            <span className="tabular-nums">{fmt(totalWithTax)}</span>
                        </div>
                        <Button
                            className="w-full mt-2"
                            size="lg"
                            disabled={busy || session.lines.length === 0}
                            onClick={() => setCheckoutOpen(true)}
                        >
                            {busy ? (
                                <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                            ) : null}
                            Cobrar {fmt(totalWithTax)}
                        </Button>
                    </div>
                </div>
            </div>

            <BarcodeScanner
                open={scannerOpen}
                onClose={() => setScannerOpen(false)}
                onScan={async (scanned) => {
                    setScannerOpen(false);
                    await addProductByCode(scanned);
                }}
            />

            <PaymentModal
                open={checkoutOpen}
                onClose={() => setCheckoutOpen(false)}
                total={totalWithTax}
                busy={busy}
                onPay={checkout}
            />
        </div>
    );
}
