"use client";

import { useGenerativeUI, sanitizeHTML } from "./_hooks/useGenerativeUI";

type GenerativeUIProps = {
    html: string;
    className?: string;
    /** Called with a follow-up prompt to regenerate the UI with fresh data. */
    onRefresh?: (prompt: string) => Promise<void>;
};

/**
 * Renders AI-generated HTML safely.
 * - Sanitizes with DOMPurify (strict whitelist)
 * - Intercepts clicks on data-erp-action elements
 * - Validates JSON payload before executing
 * - Shows confirmation if data-confirm is present
 */
export default function GenerativeUI({ html, className = "", onRefresh }: GenerativeUIProps) {
    const { containerRef, loading, sanitized } = useGenerativeUI({ html, onRefresh });

    return (
        <div className={`generative-ui ${className} relative`}>
            {loading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/70 rounded-lg backdrop-blur-sm">
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                        <span className="inline-block w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                        Actualizando panel con datos reales…
                    </div>
                </div>
            )}
            <div
                ref={containerRef}
                className="prose prose-invert prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: sanitized }}
            />
        </div>
    );
}

export { sanitizeHTML };
