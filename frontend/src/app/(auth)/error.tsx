"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { reportError } from "@/lib/error-reporter";

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors");

  useEffect(() => {
    console.error("[AuthError]", error);
    reportError(error, "AuthError");
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-xl font-semibold">{t("authError")}</h1>
      <p className="text-sm text-muted-foreground">
        {t("authErrorDescription")}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {t("retry")}
        </button>
        <Link
          href="/login"
          className="rounded-md border px-6 py-2 text-sm font-medium hover:bg-accent"
        >
          {t("goLogin")}
        </Link>
      </div>
    </main>
  );
}
