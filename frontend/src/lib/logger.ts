const isDev = process.env.NODE_ENV === "development";

/** Logs errors only in development. In production stays silent. */
export function logError(context: string, error?: unknown): void {
    if (!isDev) return;
    if (error !== undefined) {
        console.error(`[${context}]`, error);
    } else {
        console.error(`[error]`, context);
    }
}

/** Logs debug info only in development. */
export function logDebug(context: string, ...args: unknown[]): void {
    if (!isDev) return;
    console.log(`[${context}]`, ...args);
}
