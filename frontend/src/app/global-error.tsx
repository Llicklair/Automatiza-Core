"use client";

import { useEffect } from "react";
import { reportError } from "@/lib/error-reporter";

/**
 * Global error boundary — catches errors in root layout.
 * Next.js requires this to have its own <html> and <body> tags.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    reportError(error, "GlobalError");
  }, [error]);

  return (
    <html lang="es">
      <body className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <div className="flex flex-col items-center gap-4 p-8">
          <h1 className="text-2xl font-bold">Error critico</h1>
          <p className="text-muted-foreground">
            La aplicacion encontro un error irrecuperable.
          </p>
          <button
            onClick={reset}
            className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Reintentar
          </button>
        </div>
      </body>
    </html>
  );
}
