"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Zap, ArrowLeft, Mail, CheckCircle2, Loader2 } from "lucide-react";

export default function ForgotPasswordPage() {
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
            setError("Error al procesar la solicitud. Inténtalo de nuevo.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#09090b] px-4">
            <div
                className="w-full max-w-sm px-8 py-10 rounded-2xl border border-white/10 shadow-2xl"
                style={{ background: "rgba(17,17,19,0.95)", backdropFilter: "blur(20px)" }}
            >
                <div className="flex items-center gap-2.5 mb-8">
                    <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                        <Zap className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-white font-semibold text-sm">AutomatizaPyme</span>
                </div>

                {sent ? (
                    <div className="text-center">
                        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4">
                            <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                        </div>
                        <h2 className="text-lg font-bold text-white mb-2">Revisa tu email</h2>
                        <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                            Si existe una cuenta con <span className="text-zinc-200">{email}</span>, recibirás un enlace de recuperación en breve.
                        </p>
                        <Link href="/login" className="text-indigo-400 hover:text-indigo-300 text-sm transition">
                            Volver al inicio de sesión
                        </Link>
                    </div>
                ) : (
                    <>
                        <h1 className="text-xl font-bold text-white mb-1">¿Olvidaste tu contraseña?</h1>
                        <p className="text-zinc-500 text-sm mb-6">
                            Introduce tu email y te enviaremos un enlace para restablecerla.
                        </p>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                                    <input
                                        type="email"
                                        required
                                        value={email}
                                        onChange={e => setEmail(e.target.value)}
                                        placeholder="tu@empresa.es"
                                        className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm"
                                    />
                                </div>
                            </div>

                            {error && (
                                <p className="text-red-400 text-xs">{error}</p>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
                            >
                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                {loading ? "Enviando…" : "Enviar enlace"}
                            </button>
                        </form>

                        <Link
                            href="/login"
                            className="flex items-center gap-1.5 mt-6 text-xs text-zinc-500 hover:text-zinc-300 transition"
                        >
                            <ArrowLeft className="w-3.5 h-3.5" /> Volver al inicio de sesión
                        </Link>
                    </>
                )}
            </div>
        </div>
    );
}
