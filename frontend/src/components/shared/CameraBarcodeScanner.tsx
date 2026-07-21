"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, X, AlertTriangle, Loader2 } from "lucide-react";
import { BrowserMultiFormatReader, type IScannerControls } from "@zxing/browser";
import { Button } from "@/components/ui/button";

/**
 * Escáner de códigos (barras + QR) por cámara con ZXing.
 *
 * Reemplaza a la API nativa `BarcodeDetector`, que Chromium/Electron en Windows
 * NO implementa (por eso el escáner "no funcionaba"). ZXing decodifica en JS y
 * funciona en cualquier navegador/Electron con cámara y contexto seguro
 * (HTTPS o localhost).
 *
 * Sin dependencia de i18n (usa `labels` con textos por defecto en español) para
 * poder usarse también fuera del provider de traducciones (p.ej. /mobile-scanner).
 */

interface Labels {
    title?: string;
    aimHint?: string;
    insecureContext?: string;
    noCamera?: string;
    permissionDenied?: string;
    cameraError?: string;
    permissionHint?: string;
    close?: string;
}

interface Props {
    open: boolean;
    onClose: () => void;
    onScan: (code: string) => void;
    labels?: Labels;
}

const DEFAULTS: Required<Labels> = {
    title: "Escanear código",
    aimHint: "Apunta la cámara al código de barras o QR",
    insecureContext:
        "La cámara necesita HTTPS o localhost. Usa un lector USB/Bluetooth o introduce el código manualmente.",
    noCamera: "Este equipo no tiene cámara disponible. Usa un lector USB o escanea con el móvil.",
    permissionDenied: "Permiso de cámara denegado.",
    cameraError: "No se pudo acceder a la cámara",
    permissionHint: "Actívalo en los permisos de cámara del navegador o del sistema y recarga.",
    close: "Cerrar",
};

interface ErrorInfo {
    msg: string;
    hint?: string;
}

export function CameraBarcodeScanner({ open, onClose, onScan, labels }: Props) {
    const L = { ...DEFAULTS, ...labels };
    const videoRef = useRef<HTMLVideoElement>(null);
    const controlsRef = useRef<IScannerControls | null>(null);
    const [errorInfo, setErrorInfo] = useState<ErrorInfo | null>(null);
    const [starting, setStarting] = useState(false);

    useEffect(() => {
        if (!open) return;
        setErrorInfo(null);

        // getUserMedia solo existe en contexto seguro (HTTPS/localhost). Por
        // http:// con IP de LAN el navegador no lo expone — aviso claro.
        if (!navigator.mediaDevices?.getUserMedia) {
            setErrorInfo({ msg: L.insecureContext });
            return;
        }

        let cancelled = false;
        setStarting(true);
        const reader = new BrowserMultiFormatReader();
        const video = videoRef.current;
        if (!video) return;

        reader
            .decodeFromConstraints(
                { video: { facingMode: "environment" }, audio: false },
                video,
                (result, _err, controls) => {
                    if (cancelled) return;
                    if (controls && !controlsRef.current) controlsRef.current = controls;
                    setStarting(false);
                    const text = result?.getText();
                    if (text) {
                        controls?.stop();
                        controlsRef.current = null;
                        onScan(text);
                    }
                },
            )
            .then((controls) => {
                if (cancelled) {
                    controls.stop();
                    return;
                }
                controlsRef.current = controls;
                setStarting(false);
            })
            .catch((e: { name?: string; message?: string }) => {
                if (cancelled) return;
                const name = e?.name || "";
                // Distinguir "no hay cámara" de "permiso denegado": en un equipo sin
                // webcam el error es NotFound, no un permiso que se pueda conceder.
                if (["NotFoundError", "DevicesNotFoundError", "OverconstrainedError"].includes(name)) {
                    setErrorInfo({ msg: L.noCamera });
                } else if (["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(name)) {
                    setErrorInfo({ msg: L.permissionDenied, hint: L.permissionHint });
                } else {
                    setErrorInfo({ msg: e?.message || L.cameraError, hint: L.permissionHint });
                }
                setStarting(false);
            });

        return () => {
            cancelled = true;
            controlsRef.current?.stop();
            controlsRef.current = null;
        };
        // labels es estático; no lo incluimos para no reiniciar la cámara.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, onScan]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/90 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md bg-card border border-border rounded-2xl overflow-hidden">
                <div className="p-4 flex items-center justify-between border-b border-border">
                    <div className="flex items-center gap-2">
                        <Camera className="w-4 h-4 text-cyan-400" aria-hidden="true" />
                        <h3 className="text-sm font-medium text-foreground">{L.title}</h3>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={onClose}
                        aria-label={L.close}
                    >
                        <X className="w-4 h-4" aria-hidden="true" />
                    </Button>
                </div>

                <div className="relative aspect-square bg-black flex items-center justify-center">
                    {errorInfo ? (
                        <div className="text-center px-6 space-y-3 text-foreground">
                            <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" aria-hidden="true" />
                            <p className="text-sm font-medium">{errorInfo.msg}</p>
                            {errorInfo.hint && (
                                <p className="text-xs text-muted-foreground">{errorInfo.hint}</p>
                            )}
                        </div>
                    ) : (
                        <>
                            <video
                                ref={videoRef}
                                className="w-full h-full object-cover"
                                playsInline
                                muted
                            />
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

                <div className="p-3 text-[11px] text-center text-muted-foreground">{L.aimHint}</div>
            </div>
        </div>
    );
}
