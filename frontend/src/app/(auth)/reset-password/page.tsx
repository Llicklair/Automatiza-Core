"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Zap, Eye, EyeOff, CheckCircle2, Loader2, AlertCircle } from "lucide-react";

function ResetPasswordForm() {
    const router = useRouter();
    const t = useTranslations("auth");
    const searchParams = useSearchParams();
    const token = searchParams.get("token") || "";

    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [showPwd, setShowPwd] = useState(false);
    const [loading, setLoading] = useState(false);
    const [done, setDone] = useState(false);
    const [error, setError] = useState("");

    if (!token) {
        return (
            <div className="text-center">
                <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
                <p className="text-muted-foreground text-sm">{t("invalidLink")}</p>
                <Link href="/forgot-password" className="text-indigo-400 hover:text-indigo-300 text-sm mt-4 inline-block">
                    {t("requestNewLink")}
                </Link>
            </div>
        );
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        if (password !== confirm) { setError(t("errorPasswordMismatch")); return; }
        if (password.length < 8) { setError(t("errorPasswordShort")); return; }

        setLoading(true);
        try {
            await api.auth.resetPassword(token, password);
            setDone(true);
            setTimeout(() => router.push("/login"), 2500);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : t("errorInvalidLink"));
        } finally {
            setLoading(false);
        }
    }

    if (done) {
        return (
            <div className="text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4">
                    <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                </div>
                <h2 className="text-lg font-bold text-foreground mb-2">{t("passwordUpdated")}</h2>
                <p className="text-muted-foreground text-sm">{t("redirectingToLogin")}</p>
            </div>
        );
    }

    const inputClass = "w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm";

    return (
        <>
            <h1 className="text-xl font-bold text-foreground mb-1">{t("resetPasswordTitle")}</h1>
            <p className="text-muted-foreground text-sm mb-6">{t("resetPasswordDescription")}</p>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("newPassword")}</label>
                    <div className="relative">
                        <input
                            type={showPwd ? "text" : "password"}
                            required
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder={t("newPasswordPlaceholder")}
                            className={`${inputClass} pr-10`}
                        />
                        <button type="button" onClick={() => setShowPwd(p => !p)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                            {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                </div>

                <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("confirmPassword")}</label>
                    <input
                        type="password"
                        required
                        value={confirm}
                        onChange={e => setConfirm(e.target.value)}
                        placeholder={t("confirmPasswordPlaceholder")}
                        className={inputClass}
                    />
                </div>

                {error && <p className="text-red-400 text-xs">{error}</p>}

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-foreground font-medium transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
                >
                    {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                    {loading ? t("savingPassword") : t("savePassword")}
                </button>
            </form>
        </>
    );
}

export default function ResetPasswordPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <div
                className="w-full max-w-sm px-8 py-10 rounded-2xl border border-white/10 shadow-2xl"
                style={{ background: "rgba(17,17,19,0.95)", backdropFilter: "blur(20px)" }}
            >
                <div className="flex items-center gap-2.5 mb-8">
                    <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                        <Zap className="w-4 h-4 text-foreground" />
                    </div>
                    <span className="text-foreground font-semibold text-sm">AutomatizaCore</span>
                </div>
                <Suspense fallback={<div className="text-muted-foreground text-sm">{/* loading */}</div>}>
                    <ResetPasswordForm />
                </Suspense>
            </div>
        </div>
    );
}
