"use client";

import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import {
    ScanLine, QrCode, Loader2, Smartphone, Copy, CheckCircle2,
    AlertTriangle, Wifi, WifiOff, RefreshCw, Timer,
} from "lucide-react";

export default function WarehouseScannerPage() {
    const [token, setToken] = useState<{ token: string; expires_at: string; scope: string } | null>(null);
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState(false);
    const [timeLeft, setTimeLeft] = useState(0);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const generateToken = async () => {
        setLoading(true);
        try {
            const data = await api.scanner.generateQR();
            setToken(data);
        } catch (e: any) {
            alert(e?.message || "Error generando token");
        }
        setLoading(false);
    };

    // Countdown timer
    useEffect(() => {
        if (!token) return;
        const updateTimer = () => {
            const exp = new Date(token.expires_at).getTime();
            const now = Date.now();
            const remaining = Math.max(0, Math.floor((exp - now) / 1000));
            setTimeLeft(remaining);
            if (remaining <= 0 && intervalRef.current) {
                clearInterval(intervalRef.current);
                setToken(null);
            }
        };
        updateTimer();
        intervalRef.current = setInterval(updateTimer, 1000);
        return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
    }, [token]);

    const copyToken = () => {
        if (!token) return;
        navigator.clipboard.writeText(token.token);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const scannerUrl = token
        ? `${window.location.origin}/mobile-scanner?token=${token.token}`
        : null;

    return (
        <div className="p-6 max-w-3xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                    <ScanLine className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">Escáner de Almacén</h1>
                    <p className="text-xs text-muted-foreground">Conecta un móvil para escanear productos y gestionar stock</p>
                </div>
            </div>

            {/* How it works */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-cyan-400" />
                    Cómo funciona
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-background">
                        <span className="text-lg font-bold text-cyan-500/50">1</span>
                        <div>
                            <p className="text-xs font-medium text-foreground">Genera código QR</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Token temporal de 2 min con acceso solo a inventario</p>
                        </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-background">
                        <span className="text-lg font-bold text-cyan-500/50">2</span>
                        <div>
                            <p className="text-xs font-medium text-foreground">Escanea con el móvil</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Abre la cámara del móvil y escanea el QR</p>
                        </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-background">
                        <span className="text-lg font-bold text-cyan-500/50">3</span>
                        <div>
                            <p className="text-xs font-medium text-foreground">Escanea productos</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Entradas, salidas y confirmación de albaranes</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Security info */}
            <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/10 rounded-xl p-4">
                <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-300/80 space-y-1">
                    <p className="font-medium">Seguridad Zero-Key</p>
                    <p className="text-amber-400/60">
                        El token expira en 2 minutos y solo permite acceso a inventario y albaranes.
                        No puede acceder a datos financieros, RRHH ni configuración.
                    </p>
                </div>
            </div>

            {/* Generate QR / Token display */}
            <div className="bg-card border border-border rounded-xl p-6">
                {!token ? (
                    <div className="flex flex-col items-center py-8 space-y-4">
                        <div className="p-4 rounded-2xl bg-cyan-500/5 border border-cyan-500/10">
                            <QrCode className="w-12 h-12 text-cyan-500/30" />
                        </div>
                        <p className="text-sm text-muted-foreground">Genera un código para conectar un escáner móvil</p>
                        <button
                            onClick={generateToken}
                            disabled={loading}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-foreground text-sm font-medium transition-colors"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <QrCode className="w-4 h-4" />}
                            {loading ? "Generando..." : "Generar código QR"}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {/* Timer */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Wifi className="w-4 h-4 text-emerald-400" />
                                <span className="text-sm font-medium text-emerald-400">Token activo</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Timer className="w-3.5 h-3.5 text-muted-foreground" />
                                <span className={`text-sm font-mono font-bold ${timeLeft <= 30 ? "text-red-400" : "text-foreground"}`}>
                                    {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, "0")}
                                </span>
                            </div>
                        </div>

                        {/* QR Placeholder — in production use a QR library */}
                        <div className="flex flex-col items-center py-6 space-y-3">
                            <div className="w-48 h-48 bg-white rounded-2xl flex items-center justify-center p-4">
                                <div className="text-center">
                                    <QrCode className="w-16 h-16 text-muted-foreground mx-auto mb-2" />
                                    <p className="text-[10px] text-muted-foreground font-mono break-all">
                                        {token.token.slice(0, 20)}...
                                    </p>
                                </div>
                            </div>
                            <p className="text-[10px] text-muted-foreground">
                                Escanea este QR con la cámara del móvil o copia la URL
                            </p>
                        </div>

                        {/* URL + Copy */}
                        {scannerUrl && (
                            <div className="flex items-center gap-2 bg-background rounded-lg p-3">
                                <input
                                    type="text"
                                    readOnly
                                    value={scannerUrl}
                                    className="flex-1 bg-transparent text-xs text-muted-foreground font-mono truncate outline-none"
                                />
                                <button
                                    onClick={copyToken}
                                    className="flex items-center gap-1 px-2 py-1 rounded-md bg-muted hover:bg-accent text-foreground text-[10px] font-medium transition-colors"
                                >
                                    {copied ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                    {copied ? "Copiado" : "Copiar"}
                                </button>
                            </div>
                        )}

                        {/* Scope info */}
                        <div className="flex flex-wrap gap-1.5">
                            {token.scope.split(",").map((s) => (
                                <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                                    {s}
                                </span>
                            ))}
                        </div>

                        {/* Regenerate */}
                        <button
                            onClick={generateToken}
                            disabled={loading}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-accent text-foreground text-xs font-medium transition-colors"
                        >
                            <RefreshCw className="w-3.5 h-3.5" /> Generar nuevo token
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
