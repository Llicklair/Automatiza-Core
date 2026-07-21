/**
 * Ajustes de impresora del TPV — por dispositivo (localStorage), no por tenant:
 * la impresora es física de ESTA máquina. Controla la impresión automática al
 * cobrar y la impresora destino para la impresión silenciosa (Electron).
 */

export interface PrinterSettings {
    /** Imprimir el ticket automáticamente al cobrar (silencioso). */
    autoPrint: boolean;
    /** Impresora destino para impresión silenciosa; null = por defecto del sistema. */
    deviceName: string | null;
}

const KEY = "automatiza.tpv.printer";
const DEFAULTS: PrinterSettings = { autoPrint: false, deviceName: null };

export function getPrinterSettings(): PrinterSettings {
    if (typeof window === "undefined") return { ...DEFAULTS };
    try {
        const raw = window.localStorage.getItem(KEY);
        if (!raw) return { ...DEFAULTS };
        const parsed = JSON.parse(raw) as Partial<PrinterSettings>;
        return {
            autoPrint: Boolean(parsed.autoPrint),
            deviceName: typeof parsed.deviceName === "string" ? parsed.deviceName : null,
        };
    } catch {
        return { ...DEFAULTS };
    }
}

export function setPrinterSettings(patch: Partial<PrinterSettings>): PrinterSettings {
    const next = { ...getPrinterSettings(), ...patch };
    try {
        window.localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
        /* modo privado / cuota: se ignora, quedan los valores por defecto */
    }
    return next;
}
