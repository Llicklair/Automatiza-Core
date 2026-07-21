"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { CheckCircle2, Printer, ShoppingCart } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { SimplifiedInvoice } from "@/lib/api/pos";
import { printTicket } from "@/lib/print/ticket";
import { getPrinterSettings } from "@/lib/print/printerSettings";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);

interface Props {
    factura: SimplifiedInvoice;
    onNew: () => void;
}

export function TicketEmitido({ factura, onNew }: Props) {
    const t = useTranslations("tpv");
    const toast = useToastStore();
    const [printing, setPrinting] = useState(false);
    const autoPrinted = useRef(false);
    const number = factura.invoice_number ?? factura.id.slice(0, 8);

    const doPrint = useCallback(
        async (silent: boolean) => {
            setPrinting(true);
            try {
                const html = await api.pos.ticketHtml(factura.id);
                const settings = getPrinterSettings();
                const res = await printTicket(html, {
                    silent,
                    deviceName: settings.deviceName,
                });
                if (!res.success) toast.error(t("ticket.printError"));
            } catch (e) {
                logError("tpv/TicketEmitido.print", e);
                toast.error(t("ticket.printError"));
            } finally {
                setPrinting(false);
            }
        },
        [factura.id, t, toast],
    );

    // Impresión automática al cobrar (silenciosa) si está activada en ajustes.
    useEffect(() => {
        if (autoPrinted.current) return;
        if (getPrinterSettings().autoPrint) {
            autoPrinted.current = true;
            void doPrint(true);
        }
    }, [doPrint]);

    return (
        <div className="bg-card border border-border rounded-2xl p-8 text-center space-y-5 max-w-md mx-auto">
            <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-400" aria-hidden="true" />
            </div>
            <div>
                <h2 className="text-base font-semibold text-foreground">{t("ticket.title")}</h2>
                <p className="text-sm text-muted-foreground mt-1">
                    {t("ticket.subtitle", { number })}
                </p>
                <p className="text-2xl font-bold text-foreground mt-2 tabular-nums">
                    {fmt(factura.amount_total)}
                </p>
            </div>

            {factura.verifactu ? (
                <div className="flex flex-col items-center gap-2">
                    {/* Fondo blanco: los lectores necesitan alto contraste. */}
                    <div className="bg-white p-3 rounded-xl">
                        <QRCodeSVG value={factura.verifactu.verify_url} size={160} />
                    </div>
                    <p className="text-xs text-muted-foreground">{t("ticket.qrHint")}</p>
                </div>
            ) : (
                <p className="text-xs text-muted-foreground">{t("ticket.noQr")}</p>
            )}

            <div className="flex gap-2">
                <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => doPrint(false)}
                    disabled={printing}
                >
                    <Printer className="mr-2 w-4 h-4" aria-hidden="true" /> {t("ticket.print")}
                </Button>
                <Button className="flex-1" onClick={onNew} disabled={printing}>
                    <ShoppingCart className="mr-2 w-4 h-4" aria-hidden="true" /> {t("ticket.newSale")}
                </Button>
            </div>
        </div>
    );
}
