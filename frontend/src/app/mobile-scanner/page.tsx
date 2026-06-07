"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
    ScanLine, Package, ArrowDown, ArrowUp, Truck, Loader2,
    CheckCircle2, XCircle, AlertTriangle,
} from "lucide-react";
import { mobileScanner, type ScannedProduct } from "@/lib/api/scanner";

type ActionResult = { success: boolean; message: string; data?: any };

function MobileScannerInner() {
    const params = useSearchParams();
    const token = params.get("token") || "";
    const [authenticated, setAuthenticated] = useState<boolean | null>(null);
    const [deviceInfo, setDeviceInfo] = useState<{ tenant_id: string; device: string } | null>(null);

    const [code, setCode] = useState("");
    const [product, setProduct] = useState<ScannedProduct | null>(null);
    const [loading, setLoading] = useState(false);
    const [quantity, setQuantity] = useState(1);
    const [lotNumber, setLotNumber] = useState("");
    const [lotExpiry, setLotExpiry] = useState("");
    const [result, setResult] = useState<ActionResult | null>(null);
    const [albaranNum, setAlbaranNum] = useState("");

    // Verify token on mount
    useEffect(() => {
        if (!token) { setAuthenticated(false); return; }
        mobileScanner.whoami(token)
            .then((data) => { setAuthenticated(true); setDeviceInfo(data); })
            .catch(() => setAuthenticated(false));
    }, [token]);

    const productCode = () => product?.barcode || product?.sku || code.trim();

    const scanProduct = async () => {
        if (!code.trim()) return;
        setLoading(true); setProduct(null); setResult(null);
        try {
            const data = await mobileScanner.scanProduct(token, code.trim());
            setProduct(data);
        } catch (e: any) {
            setResult({ success: false, message: e.message });
        }
        setLoading(false);
    };

    const stockEntry = async () => {
        if (!product) return;
        setLoading(true); setResult(null);
        try {
            const data = await mobileScanner.stockEntry(token, productCode(), quantity, {
                lot_number: lotNumber.trim() || null,
                expiry_date: lotExpiry || null,
            });
            const lotMsg = lotNumber.trim() ? ` · lote ${lotNumber.trim()}` : "";
            setResult({ success: true, message: `+${quantity} → Stock: ${data.stock_after}${lotMsg}`, data });
            setProduct({ ...product, stock_quantity: data.stock_after, low_stock: data.low_stock });
            setLotNumber(""); setLotExpiry("");
        } catch (e: any) { setResult({ success: false, message: e.message }); }
        setLoading(false);
    };

    const stockExit = async () => {
        if (!product) return;
        setLoading(true); setResult(null);
        try {
            const data = await mobileScanner.stockExit(token, productCode(), quantity);
            setResult({ success: true, message: `-${quantity} → Stock: ${data.stock_after}`, data });
            setProduct({ ...product, stock_quantity: data.stock_after, low_stock: data.low_stock });
        } catch (e: any) { setResult({ success: false, message: e.message }); }
        setLoading(false);
    };

    const confirmDelivery = async () => {
        if (!albaranNum.trim()) return;
        setLoading(true); setResult(null);
        try {
            const data = await mobileScanner.confirmDelivery(token, albaranNum.trim());
            setResult({ success: true, message: `Albarán ${data.albaran_number}: ${data.status}` });
            setAlbaranNum("");
        } catch (e: any) { setResult({ success: false, message: e.message }); }
        setLoading(false);
    };

    // -- Not authenticated --
    if (authenticated === false) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-6">
                <div className="text-center space-y-3">
                    <XCircle className="w-12 h-12 text-red-400 mx-auto" />
                    <h1 className="text-lg font-bold text-foreground">Token expirado o inválido</h1>
                    <p className="text-sm text-muted-foreground">Genera un nuevo código QR desde el escritorio</p>
                </div>
            </div>
        );
    }

    if (authenticated === null) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background p-4 max-w-md mx-auto space-y-4">
            {/* Header */}
            <div className="flex items-center gap-2 py-2">
                <ScanLine className="w-5 h-5 text-cyan-400" />
                <h1 className="text-base font-bold text-foreground">Escáner Almacén</h1>
                <span className="ml-auto text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">Conectado</span>
            </div>

            {/* Product scan */}
            <div className="bg-card rounded-xl p-4 space-y-3">
                <label className="text-xs font-medium text-muted-foreground">Buscar producto por código</label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && scanProduct()}
                        placeholder="Escanea código de barras o SKU..."
                        className="flex-1 bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                        autoFocus
                    />
                    <button
                        onClick={scanProduct}
                        disabled={loading || !code.trim()}
                        className="px-3 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-foreground"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanLine className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {/* Product info */}
            {product && (
                <div className="bg-card rounded-xl p-4 space-y-3">
                    <div className="flex items-start justify-between">
                        <div>
                            <h3 className="text-sm font-semibold text-foreground">{product.name}</h3>
                            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5">
                                {product.sku && (
                                    <p className="text-[10px] text-muted-foreground font-mono">SKU: {product.sku}</p>
                                )}
                                {product.barcode && (
                                    <p className="text-[10px] text-muted-foreground font-mono">EAN: {product.barcode}</p>
                                )}
                            </div>
                        </div>
                        <Package className="w-5 h-5 text-muted-foreground" />
                    </div>
                    {product.description && <p className="text-xs text-muted-foreground">{product.description}</p>}
                    <div className="flex items-center gap-4">
                        <div>
                            <span className="text-xs text-muted-foreground">Stock:</span>
                            <span className={`ml-1 text-sm font-bold ${product.low_stock ? "text-red-400" : "text-foreground"}`}>
                                {product.stock_quantity}
                            </span>
                        </div>
                        {product.price != null && (
                            <div>
                                <span className="text-xs text-muted-foreground">Precio:</span>
                                <span className="ml-1 text-sm text-foreground">{product.price.toFixed(2)}€</span>
                            </div>
                        )}
                        {product.low_stock && (
                            <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">
                                <AlertTriangle className="w-3 h-3" /> Stock bajo
                            </span>
                        )}
                    </div>

                    {/* Quantity + actions */}
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground">Cantidad:</label>
                        <input
                            type="number"
                            min={1}
                            value={quantity}
                            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                            className="w-20 bg-muted border border-border rounded-lg px-2 py-1.5 text-sm text-foreground text-center focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                        />
                    </div>

                    {/* Lote (opcional) — solo aplica a Entrada (gestión de caducidad/FEFO) */}
                    <div className="space-y-1.5">
                        <p className="text-xs text-muted-foreground">Lote (opcional, solo entrada):</p>
                        <div className="grid grid-cols-2 gap-2">
                            <input
                                type="text"
                                value={lotNumber}
                                onChange={(e) => setLotNumber(e.target.value)}
                                placeholder="Nº de lote"
                                className="bg-muted border border-border rounded-lg px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                            />
                            <input
                                type="date"
                                value={lotExpiry}
                                onChange={(e) => setLotExpiry(e.target.value)}
                                aria-label="Caducidad del lote"
                                className="bg-muted border border-border rounded-lg px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            onClick={stockEntry}
                            disabled={loading}
                            className="flex items-center justify-center gap-1.5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground text-sm font-medium transition-colors"
                        >
                            <ArrowDown className="w-4 h-4" /> Entrada
                        </button>
                        <button
                            onClick={stockExit}
                            disabled={loading}
                            className="flex items-center justify-center gap-1.5 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-foreground text-sm font-medium transition-colors"
                        >
                            <ArrowUp className="w-4 h-4" /> Salida
                        </button>
                    </div>
                </div>
            )}

            {/* Delivery confirmation */}
            <div className="bg-card rounded-xl p-4 space-y-3">
                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Truck className="w-3.5 h-3.5" /> Confirmar albarán
                </label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={albaranNum}
                        onChange={(e) => setAlbaranNum(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && confirmDelivery()}
                        placeholder="Nº albarán (ej: ALB-2026-0015)"
                        className="flex-1 bg-muted border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                    />
                    <button
                        onClick={confirmDelivery}
                        disabled={loading || !albaranNum.trim()}
                        className="px-3 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-foreground"
                    >
                        <CheckCircle2 className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Result */}
            {result && (
                <div className={`rounded-xl p-3 text-sm flex items-center gap-2 ${
                    result.success
                        ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-300"
                        : "bg-red-500/10 border border-red-500/20 text-red-300"
                }`}>
                    {result.success ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : <XCircle className="w-4 h-4 flex-shrink-0" />}
                    {result.message}
                </div>
            )}
        </div>
    );
}

export default function MobileScannerPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen bg-background flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
                </div>
            }
        >
            <MobileScannerInner />
        </Suspense>
    );
}
