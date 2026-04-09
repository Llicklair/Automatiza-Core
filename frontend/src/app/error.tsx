"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { reportError } from "@/lib/error-reporter";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors");

  useEffect(() => {
    console.error("[RootError]", error);
    reportError(error, "RootError");
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <div className="rounded-full bg-destructive/10 p-4">
        <svg
          className="h-8 w-8 text-destructive"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <h1 className="text-xl font-semibold">{t("generic")}</h1>
      <p className="text-sm text-muted-foreground">
        {t("genericDescription")}
      </p>
      <button
        onClick={reset}
        className="mt-2 rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        {t("retry")}
      </button>
    </main>
  );
}
