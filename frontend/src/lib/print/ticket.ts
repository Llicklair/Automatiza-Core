/**
 * Impresión de tickets de venta (TPV).
 *
 * El backend entrega el ticket como HTML autocontenido de 80 mm
 * (`api.pos.ticketHtml`). Aquí lo mandamos a imprimir:
 *  - En Electron: vía `electronAPI.printTicket` → impresión nativa (diálogo del
 *    sistema o silenciosa a la impresora elegida). Sirve para impresora térmica
 *    de TPV o normal indistintamente (la que esté conectada / seleccionada).
 *  - En navegador (dev / web): fallback con iframe oculto + `window.print()`.
 */

export interface PrinterInfo {
    name: string;
    displayName?: string;
    description?: string;
    isDefault?: boolean;
    status?: number;
}

export interface PrintTicketResult {
    success: boolean;
    failureReason?: string | null;
}

export interface PrintTicketOptions {
    /** true = imprime directo sin diálogo (requiere Electron + impresora conocida). */
    silent?: boolean;
    /** Nombre de la impresora destino (Electron). Vacío = impresora por defecto. */
    deviceName?: string | null;
}

/** ¿Hay puente de impresión nativa (Electron)? */
export function isElectronPrint(): boolean {
    return typeof window !== "undefined" && !!window.electronAPI?.printTicket;
}

/** Lista de impresoras del sistema (solo Electron; vacío en navegador). */
export async function listPrinters(): Promise<PrinterInfo[]> {
    if (typeof window === "undefined") return [];
    const api = window.electronAPI;
    if (!api?.listPrinters) return [];
    try {
        return await api.listPrinters();
    } catch {
        return [];
    }
}

export async function printTicket(
    html: string,
    opts: PrintTicketOptions = {},
): Promise<PrintTicketResult> {
    const api = typeof window !== "undefined" ? window.electronAPI : undefined;
    if (api?.printTicket) {
        return api.printTicket(html, {
            silent: !!opts.silent,
            deviceName: opts.deviceName ?? undefined,
        });
    }
    // Fallback navegador: iframe oculto + diálogo de impresión del sistema.
    return printViaIframe(html);
}

function printViaIframe(html: string): Promise<PrintTicketResult> {
    return new Promise((resolve) => {
        if (typeof document === "undefined") {
            resolve({ success: false, failureReason: "no-document" });
            return;
        }
        const iframe = document.createElement("iframe");
        Object.assign(iframe.style, {
            position: "fixed",
            right: "0",
            bottom: "0",
            width: "0",
            height: "0",
            border: "0",
        });
        iframe.setAttribute("aria-hidden", "true");
        document.body.appendChild(iframe);
        const doc = iframe.contentWindow?.document;
        if (!doc || !iframe.contentWindow) {
            iframe.remove();
            resolve({ success: false, failureReason: "no-iframe-doc" });
            return;
        }
        doc.open();
        doc.write(html);
        doc.close();
        const win = iframe.contentWindow;
        // Margen para renderizar el QR (data-URI) antes de abrir el diálogo.
        setTimeout(() => {
            try {
                win.focus();
                win.print();
                resolve({ success: true });
            } catch (e) {
                resolve({ success: false, failureReason: String(e) });
            } finally {
                setTimeout(() => iframe.remove(), 1000);
            }
        }, 300);
    });
}
