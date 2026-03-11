"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegistroPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);

    const [form, setForm] = useState({
        email: "",
        password: "",
        confirmPassword: "",
        full_name: "",
        company_name: "",
        nif: "",
    });

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
        setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");

        if (form.password !== form.confirmPassword) {
            setError("Las contraseñas no coinciden.");
            return;
        }
        if (form.password.length < 8) {
            setError("La contraseña debe tener al menos 8 caracteres.");
            return;
        }

        setLoading(true);
        try {
            await api.auth.register({
                email: form.email,
                password: form.password,
                full_name: form.full_name,
                tenant: {
                    name: form.company_name,
                    nif: form.nif.toUpperCase(),
                },
            });
            setSuccess(true);
            // Auto-redirigir al login tras 2 segundos
            setTimeout(() => router.push("/login"), 2000);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Error al registrarse");
        } finally {
            setLoading(false);
        }
    }

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#09090b]">
                <div className="w-full max-w-md px-8 py-10 rounded-2xl border border-[#27272a] bg-[#111113] shadow-2xl text-center">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-500/10 mb-4">
                        <svg className="w-7 h-7 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">¡Cuenta creada!</h2>
                    <p className="text-zinc-400 text-sm">Redirigiendo al login…</p>
                </div>
            </div>
        );
    }

    const inputClass = "w-full px-4 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition";
    const labelClass = "block text-sm font-medium text-zinc-300 mb-1.5";

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#09090b] py-12">
            <div className="w-full max-w-md px-8 py-10 rounded-2xl border border-[#27272a] bg-[#111113] shadow-2xl">
                {/* Logo */}
                <div className="mb-8 text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-600 mb-4">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <h1 className="text-2xl font-bold text-white">AutomatizaPyme</h1>
                    <p className="mt-1 text-sm text-zinc-400">Crea tu cuenta de empresa</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Datos personales */}
                    <div>
                        <label className={labelClass}>Nombre completo</label>
                        <input
                            name="full_name"
                            type="text"
                            required
                            value={form.full_name}
                            onChange={handleChange}
                            placeholder="Ana García López"
                            className={inputClass}
                        />
                    </div>

                    <div>
                        <label className={labelClass}>Email</label>
                        <input
                            name="email"
                            type="email"
                            required
                            value={form.email}
                            onChange={handleChange}
                            placeholder="ana@miempresa.es"
                            className={inputClass}
                        />
                    </div>

                    {/* Datos de empresa */}
                    <div className="pt-2 border-t border-[#27272a]">
                        <p className="text-xs text-zinc-500 mb-3 uppercase tracking-wider">Datos de tu empresa</p>
                        <div className="space-y-4">
                            <div>
                                <label className={labelClass}>Nombre de la empresa</label>
                                <input
                                    name="company_name"
                                    type="text"
                                    required
                                    value={form.company_name}
                                    onChange={handleChange}
                                    placeholder="Mi Empresa SL"
                                    className={inputClass}
                                />
                            </div>
                            <div>
                                <label className={labelClass}>NIF / CIF</label>
                                <input
                                    name="nif"
                                    type="text"
                                    required
                                    value={form.nif}
                                    onChange={handleChange}
                                    placeholder="B12345678"
                                    maxLength={9}
                                    className={inputClass}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Contraseña */}
                    <div className="pt-2 border-t border-[#27272a]">
                        <p className="text-xs text-zinc-500 mb-3 uppercase tracking-wider">Contraseña</p>
                        <div className="space-y-4">
                            <div>
                                <label className={labelClass}>Contraseña</label>
                                <input
                                    name="password"
                                    type="password"
                                    required
                                    value={form.password}
                                    onChange={handleChange}
                                    placeholder="Mínimo 8 caracteres"
                                    className={inputClass}
                                />
                            </div>
                            <div>
                                <label className={labelClass}>Confirmar contraseña</label>
                                <input
                                    name="confirmPassword"
                                    type="password"
                                    required
                                    value={form.confirmPassword}
                                    onChange={handleChange}
                                    placeholder="Repite la contraseña"
                                    className={inputClass}
                                />
                            </div>
                        </div>
                    </div>

                    {error && (
                        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium transition-colors duration-150 mt-2"
                    >
                        {loading ? "Creando cuenta…" : "Crear cuenta"}
                    </button>
                </form>

                <p className="mt-6 text-center text-xs text-zinc-500">
                    ¿Ya tienes cuenta?{" "}
                    <a href="/login" className="text-indigo-400 hover:text-indigo-300 transition">
                        Inicia sesión
                    </a>
                </p>
            </div>
        </div>
    );
}
