"use client";

import {
    ScanLine, QrCode, Loader2, Smartphone, Copy, CheckCircle2,
    AlertTriangle, Wifi, RefreshCw, Timer,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { QRCodeSVG } from "qrcode.react";
import { useWarehouseScanner } from "./_hooks/useWarehouseScanner";

export default function WarehouseScannerPage() {
    const t = useTranslations("inventario");
    const { token, loading, copied, timeLeft, scannerUrl, generateToken, copyToken, publicBase, setPublicBase } = useWarehouseScanner();

    return (
        <div className="p-6 max-w-3xl mx-auto space-y-6">
            <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                    <ScanLine className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-foreground">{t("scanner.title")}</h1>
                    <p className="text-xs text-muted-foreground">{t("scanner.subtitle")}</p>
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-cyan-400" />
                    {t("scanner.howItWorks")}
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-background">
                        <span className="text-lg font-bold text-cyan-500/50">1</span>
                        <div>
                            <p className="text-xs font-medium text-foreground">{t("scanner.step1Title")}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">{t("scanner.step1Desc")}</p>
                        </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-background">
                        <span className="text-lg font-bold text-cyan-500/50">2</span>
                        <div>
                            <p className="text-xs font-medium text-foreground">{t("scanner.step2Title")}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">{t("scanner.step2Desc")}</p>
                        </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-background">
                        <span className="text-lg font-bold text-cyan-500/50">3</span>
                        <div>
                            <p className="text-xs font-medium text-foreground">{t("scanner.step3Title")}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">{t("scanner.step3Desc")}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/10 rounded-xl p-4">
                <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-300/80 space-y-1">
                    <p className="font-medium">{t("scanner.securityTitle")}</p>
                    <p className="text-amber-400/60">
                        {t("scanner.securityDesc")}
                    </p>
                </div>
            </div>

            {/* URL pública (túnel) — cert de confianza real → la cámara del móvil va sin instalar nada */}
            <div className="bg-card border border-border rounded-xl p-4 space-y-2">
                <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                    <Wifi className="w-3.5 h-3.5" /> URL pública / túnel (opcional)
                </label>
                <input
                    type="text"
                    value={publicBase}
                    onChange={(e) => setPublicBase(e.target.value)}
                    placeholder="https://xxxx.trycloudflare.com"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                />
                <p className="text-[10px] text-muted-foreground">
                    Si la pegas, el QR apunta ahí (certificado de confianza → la cámara del móvil funciona sin instalar nada). Vacío = usa la IP local.
                </p>
            </div>

            <div className="bg-card border border-border rounded-xl p-6">
                {!token ? (
                    <div className="flex flex-col items-center py-8 space-y-4">
                        <div className="p-4 rounded-2xl bg-cyan-500/5 border border-cyan-500/10">
                            <QrCode className="w-12 h-12 text-cyan-500/30" />
                        </div>
                        <p className="text-sm text-muted-foreground">{t("scanner.generatePrompt")}</p>
                        <button
                            onClick={generateToken}
                            disabled={loading}
                            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-foreground text-sm font-medium transition-colors"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <QrCode className="w-4 h-4" />}
                            {loading ? t("scanner.generating") : t("scanner.generateQr")}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Wifi className="w-4 h-4 text-emerald-400" />
                                <span className="text-sm font-medium text-emerald-400">{t("scanner.tokenActive")}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Timer className="w-3.5 h-3.5 text-muted-foreground" />
                                <span className={`text-sm font-mono font-bold ${timeLeft <= 30 ? "text-red-400" : "text-foreground"}`}>
                                    {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, "0")}
                                </span>
                            </div>
                        </div>

                        <div className="flex flex-col items-center py-6 space-y-3">
                            <div className="w-48 h-48 bg-white rounded-2xl flex items-center justify-center p-3">
                                {scannerUrl ? (
                                    <QRCodeSVG value={scannerUrl} size={168} />
                                ) : (
                                    <QrCode className="w-16 h-16 text-muted-foreground" />
                                )}
                            </div>
                            <p className="text-[10px] text-muted-foreground">
                                {t("scanner.scanHint")}
                            </p>
                            <p className="text-[10px] text-amber-400/70 max-w-xs text-center">
                                {t("scanner.certNote")}
                            </p>
                        </div>

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
                                    {copied ? t("scanner.copied") : t("scanner.copy")}
                                </button>
                            </div>
                        )}

                        <div className="flex flex-wrap gap-1.5">
                            {token.scope.split(",").map((s) => (
                                <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                                    {s}
                                </span>
                            ))}
                        </div>

                        <button
                            onClick={generateToken}
                            disabled={loading}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-accent text-foreground text-xs font-medium transition-colors"
                        >
                            <RefreshCw className="w-3.5 h-3.5" /> {t("scanner.generateNewToken")}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
