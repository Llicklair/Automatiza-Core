/**
 * Augmentación global de `window.electronAPI` (DIS.UPD / SEC.JWT).
 *
 * El bridge se inyecta desde `desktop/preload.js` via
 * `contextBridge.exposeInMainWorld("electronAPI", ...)`. Aquí declaramos
 * solo la forma — la implementación vive en Electron y queda undefined
 * en browser dev.
 *
 * Los consumidores deben hacer narrowing (`if (window.electronAPI?.X)`)
 * antes de invocar.
 */

export {};

declare global {
    interface SecureStoreApi {
        get: (key: string) => Promise<string | null>;
        set: (key: string, value: string) => Promise<boolean>;
        remove: (key: string) => Promise<boolean>;
        isAvailable: () => Promise<boolean>;
    }

    interface UpdateChannelApi {
        getUpdateChannel?: () => Promise<"stable" | "beta">;
        setUpdateChannel?: (
            channel: "stable" | "beta",
        ) => Promise<{ ok: boolean; channel: "stable" | "beta" }>;
    }

    interface AutoUpdateApi {
        checkForUpdates?: () => Promise<void>;
        installUpdate?: () => Promise<void>;
        onUpdateAvailable?: (cb: (info: { version: string }) => void) => void;
        onUpdateNotAvailable?: (cb: () => void) => void;
        onUpdateDownloadProgress?: (
            cb: (p: { percent: number; transferred: number; total: number }) => void,
        ) => void;
        onUpdateDownloaded?: (cb: () => void) => void;
        onUpdateError?: (cb: (msg: string) => void) => void;
        removeUpdateListeners?: () => void;
    }

    interface PrinterInfo {
        name: string;
        displayName?: string;
        description?: string;
        isDefault?: boolean;
        status?: number;
    }

    interface PrintApi {
        /** Imprime el HTML de un ticket (térmica de TPV o impresora normal). */
        printTicket?: (
            html: string,
            opts?: { silent?: boolean; deviceName?: string },
        ) => Promise<{ success: boolean; failureReason?: string | null }>;
        /** Impresoras disponibles en el sistema. */
        listPrinters?: () => Promise<PrinterInfo[]>;
    }

    interface ElectronAPI extends AutoUpdateApi, UpdateChannelApi, PrintApi {
        secureStore?: SecureStoreApi;
    }

    interface Window {
        electronAPI?: ElectronAPI;
    }
}
