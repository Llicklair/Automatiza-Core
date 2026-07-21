"use client";

import { useEffect, useState } from "react";
import { Printer, X, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/stores/toast";
import {
    isElectronPrint,
    listPrinters,
    printTicket,
    type PrinterInfo,
} from "@/lib/print/ticket";
import { getPrinterSettings, setPrinterSettings } from "@/lib/print/printerSettings";

const TEST_TICKET = `<!doctype html><html lang="es"><head><meta charset="utf-8"/>
<style>@page{size:72mm auto;margin:0}body{width:72mm;padding:4mm 3mm;margin:0;
font-family:"Courier New",monospace;font-size:12px;text-align:center;color:#000;background:#fff}
h1{font-size:15px;margin:0 0 8px}.hr{border-top:1px dashed #000;margin:8px 0}</style></head>
<body><h1>AutomatizaCore</h1><div class="hr"></div><div>Impresión de prueba</div>
<div>Ticket 80 mm</div><div class="hr"></div><div>OK ✔</div></body></html>`;

/** Ajustes de impresora del TPV: impresión automática al cobrar + impresora destino. */
export function PrinterSettings() {
    const t = useTranslations("tpv");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const [open, setOpen] = useState(false);
    const [autoPrint, setAutoPrint] = useState(false);
    const [deviceName, setDeviceName] = useState("");
    const [printers, setPrinters] = useState<PrinterInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const electron = isElectronPrint();

    useEffect(() => {
        if (!open) return;
        const s = getPrinterSettings();
        setAutoPrint(s.autoPrint);
        setDeviceName(s.deviceName ?? "");
        setLoading(true);
        listPrinters()
            .then(setPrinters)
            .finally(() => setLoading(false));
    }, [open]);

    const persist = (patch: { autoPrint?: boolean; deviceName?: string | null }) => {
        const next = setPrinterSettings(patch);
        setAutoPrint(next.autoPrint);
        setDeviceName(next.deviceName ?? "");
    };

    const testPrint = async () => {
        const res = await printTicket(TEST_TICKET, {
            silent: electron && !!deviceName,
            deviceName: deviceName || null,
        });
        if (res.success) toast.success(t("printer.testOk"));
        else toast.error(t("printer.testError"));
    };

    return (
        <>
            <Button variant="outline" size="sm" onClick={() => setOpen(true)} title={t("printer.button")}>
                <Printer className="mr-1 w-3.5 h-3.5" aria-hidden="true" /> {t("printer.button")}
            </Button>
            {open && (
                <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-md overflow-hidden">
                        <div className="p-4 flex items-center justify-between border-b border-border">
                            <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
                                <Printer className="w-4 h-4" aria-hidden="true" /> {t("printer.title")}
                            </h3>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => setOpen(false)}
                                aria-label={tc("close")}
                            >
                                <X className="w-4 h-4" aria-hidden="true" />
                            </Button>
                        </div>
                        <div className="p-6 space-y-5">
                            {!electron && (
                                <p className="text-xs text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                                    {t("printer.browserNote")}
                                </p>
                            )}

                            {/* Impresora destino (Electron) */}
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-foreground">
                                    {t("printer.printer")}
                                </label>
                                {loading ? (
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> {tc("loading")}
                                    </div>
                                ) : (
                                    <select
                                        value={deviceName}
                                        disabled={!electron}
                                        onChange={(e) => persist({ deviceName: e.target.value || null })}
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm disabled:opacity-50"
                                    >
                                        <option value="">{t("printer.defaultPrinter")}</option>
                                        {printers.map((p) => (
                                            <option key={p.name} value={p.name}>
                                                {p.displayName || p.name}
                                                {p.isDefault ? " ★" : ""}
                                            </option>
                                        ))}
                                    </select>
                                )}
                            </div>

                            {/* Impresión automática al cobrar */}
                            <label className="flex items-start gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={autoPrint}
                                    disabled={!electron}
                                    onChange={(e) => persist({ autoPrint: e.target.checked })}
                                    className="mt-0.5 h-4 w-4 accent-cyan-500 disabled:opacity-50"
                                />
                                <span className="text-sm text-foreground">
                                    {t("printer.autoPrint")}
                                    <span className="block text-xs text-muted-foreground">
                                        {t("printer.autoPrintHint")}
                                    </span>
                                </span>
                            </label>

                            <Button variant="outline" className="w-full" onClick={testPrint}>
                                <Printer className="mr-2 w-4 h-4" aria-hidden="true" /> {t("printer.test")}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
