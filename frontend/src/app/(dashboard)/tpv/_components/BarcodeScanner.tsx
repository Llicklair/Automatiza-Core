"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, X, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
    open: boolean;
    onClose: () => void;
    onScan: (code: string) => void;
}

// Tipado mínimo del Web API BarcodeDetector (no está en lib.dom default).
type BarcodeDetectorCtor = new (opts?: { formats?: string[] }) => {
    detect: (source: CanvasImageSource) => Promise<{ rawValue: string }[]>;
};

const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "qr_code"];

export function BarcodeScanner({ open, onClose, onScan }: Props) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const rafRef = useRef<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [supported, setSupported] = useState<boolean | null>(null);
    const [starting, setStarting] = useState(false);

    useEffect(() => {
        if (!open) return;

        const Ctor = (globalThis as unknown as { BarcodeDetector?: BarcodeDetectorCtor })
            .BarcodeDetector;
        if (!Ctor) {
            setSupported(false);
            return;
        }
        setSupported(true);
        setStarting(true);
        let cancelled = false;

        const detector = new Ctor({ formats: FORMATS });

        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: "environment" }, audio: false })
            .then((stream) => {
                if (cancelled) {
                    stream.getTracks().forEach((t) => t.stop());
                    return;
                }
                streamRef.current = stream;
                const video = videoRef.current;
                if (!video) return;
                video.srcObject = stream;
                video.play().catch(() => {});
                setStarting(false);

                const tick = async () => {
                    if (!videoRef.current || cancelled) return;
                    try {
                        const results = await detector.detect(videoRef.current);
                        if (results.length > 0) {
                            const code = results[0].rawValue;
                            if (code) {
                                onScan(code);
                                return;
                            }
                        }
                    } catch {
                        // ignore one-off frame errors
                    }
                    rafRef.current = requestAnimationFrame(tick);
                };
                rafRef.current = requestAnimationFrame(tick);
            })
            .catch((e: Error) => {
                if (cancelled) return;
                setError(e.message || "No se pudo abrir la cámara");
                setStarting(false);
            });

        return () => {
            cancelled = true;
            if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
            rafRef.current = null;
            if (streamRef.current) {
                streamRef.current.getTracks().forEach((t) => t.stop());
                streamRef.current = null;
            }
        };
    }, [open, onScan]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/90 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md bg-card border border-border rounded-2xl overflow-hidden">
                <div className="p-4 flex items-center justify-between border-b border-border">
                    <div className="flex items-center gap-2">
                        <Camera className="w-4 h-4 text-cyan-400" />
                        <h3 className="text-sm font-medium text-foreground">Escanear código</h3>
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose} aria-label="Cerrar">
                        <X className="w-4 h-4" aria-hidden="true" />
                    </Button>
                </div>

                <div className="relative aspect-square bg-black flex items-center justify-center">
                    {supported === false && (
                        <div className="text-center px-6 space-y-3 text-foreground">
                            <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
                            <p className="text-sm font-medium">Lectura por cámara no soportada</p>
                            <p className="text-xs text-muted-foreground">
                                Tu navegador no implementa BarcodeDetector. Usa un lector USB/Bluetooth
                                o introduce el código manualmente.
                            </p>
                        </div>
                    )}
                    {supported && error && (
                        <div className="text-center px-6 space-y-3 text-foreground">
                            <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
                            <p className="text-sm font-medium">{error}</p>
                            <p className="text-xs text-muted-foreground">
                                Asegúrate de dar permiso de cámara al navegador.
                            </p>
                        </div>
                    )}
                    {supported && !error && (
                        <>
                            <video
                                ref={videoRef}
                                className="w-full h-full object-cover"
                                playsInline
                                muted
                            />
                            {/* Overlay de "viseur" */}
                            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                                <div className="w-3/4 h-1/3 border-2 border-cyan-400/70 rounded-xl"></div>
                            </div>
                            {starting && (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                                    <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                                </div>
                            )}
                        </>
                    )}
                </div>

                <div className="p-3 text-[11px] text-center text-muted-foreground">
                    Apunta al código de barras o QR del producto
                </div>
            </div>
        </div>
    );
}
