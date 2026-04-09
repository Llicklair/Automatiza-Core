"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { Zap, ArrowLeft, Mail, CheckCircle2, Loader2 } from "lucide-react";

export default function ForgotPasswordPage() {
    const t = useTranslations("auth");
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState("");

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            await api.auth.forgotPassword(email);
            setSent(true);
        } catch {
            setError(t("errorRequest"));
        } finally {
            setLoading(false);
        }
    }

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
                    <span className="text-foreground font-semibold text-sm">AutomatizaPyme</span>
                </div>

                {sent ? (
                    <div className="text-center">
                        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4">
                            <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                        </div>
                        <h2 className="text-lg font-bold text-foreground mb-2">{t("checkEmail")}</h2>
                        <p className="text-muted-foreground text-sm leading-relaxed mb-6">
                            {t("checkEmailDescription", { email })}
                        </p>
                        <Link href="/login" className="text-indigo-400 hover:text-indigo-300 text-sm transition">
                            {t("backToLogin")}
                        </Link>
                    </div>
                ) : (
                    <>
                        <h1 className="text-xl font-bold text-foreground mb-1">{t("forgotPasswordTitle")}</h1>
                        <p className="text-muted-foreground text-sm mb-6">
                            {t("forgotPasswordDescription")}
                        </p>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1.5">{t("email")}</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                    <input
                                        type="email"
                                        required
                                        value={email}
                                        onChange={e => setEmail(e.target.value)}
                                        placeholder={t("emailPlaceholder")}
                                        className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm"
                                    />
                                </div>
                            </div>

                            {error && (
                                <p className="text-red-400 text-xs">{error}</p>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-foreground font-medium transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
                            >
                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                {loading ? t("sendingLink") : t("sendLink")}
                            </button>
                        </form>

                        <Link
                            href="/login"
                            className="flex items-center gap-1.5 mt-6 text-xs text-muted-foreground hover:text-foreground transition"
                        >
                            <ArrowLeft className="w-3.5 h-3.5" /> {t("backToLogin")}
                        </Link>
                    </>
                )}
            </div>
        </div>
    );
}
