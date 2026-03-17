"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CheckCircle2, Zap, FileText, Users, BrainCircuit } from "lucide-react";

function NeuralBackground() {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        let animId: number;
        const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
        resize();
        window.addEventListener("resize", resize);
        const nodes = Array.from({ length: 50 }, () => ({
            x: Math.random() * window.innerWidth, y: Math.random() * window.innerHeight,
            vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
            r: Math.random() * 2 + 1.5, pulse: Math.random() * Math.PI * 2,
        }));
        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (const n of nodes) {
                n.x += n.vx; n.y += n.vy; n.pulse += 0.012;
                if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
                if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
            }
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 150) {
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(99,102,241,${(1 - dist / 150) * 0.15})`;
                        ctx.lineWidth = 0.8;
                        ctx.moveTo(nodes[i].x, nodes[i].y);
                        ctx.lineTo(nodes[j].x, nodes[j].y);
                        ctx.stroke();
                    }
                }
            }
            for (const n of nodes) {
                const pulse = 0.5 + 0.5 * Math.sin(n.pulse);
                const alpha = 0.2 + 0.2 * pulse;
                const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 3);
                grad.addColorStop(0, `rgba(139,92,246,${alpha})`);
                grad.addColorStop(1, "rgba(99,102,241,0)");
                ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 3, 0, Math.PI * 2);
                ctx.fillStyle = grad; ctx.fill();
                ctx.beginPath(); ctx.arc(n.x, n.y, n.r + pulse * 0.8, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(165,180,252,${alpha + 0.1})`; ctx.fill();
            }
            animId = requestAnimationFrame(draw);
        };
        draw();
        return () => { cancelAnimationFrame(animId); window.removeEventListener("resize", resize); };
    }, []);
    return <canvas ref={canvasRef} className="fixed inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }} />;
}

const FEATURES = [
    { icon: BrainCircuit, text: "Agentes IA que ejecutan tareas en lenguaje natural" },
    { icon: FileText,     text: "Facturación automática con numeración correlativa AEAT" },
    { icon: Users,        text: "RRHH, nóminas y SS calculadas con tasas reales 2025" },
    { icon: Zap,          text: "Automatizaciones que trabajan mientras tú descansas" },
];

export default function RegistroPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [form, setForm] = useState({
        email: "", password: "", confirmPassword: "",
        full_name: "", company_name: "", nif: "",
    });

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
        setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        if (form.password !== form.confirmPassword) { setError("Las contraseñas no coinciden."); return; }
        if (form.password.length < 8) { setError("La contraseña debe tener al menos 8 caracteres."); return; }
        setLoading(true);
        try {
            await api.auth.register({
                email: form.email, password: form.password, full_name: form.full_name,
                tenant: { name: form.company_name, nif: form.nif.toUpperCase() },
            });
            setSuccess(true);
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
                <NeuralBackground />
                <div className="relative z-10 text-center" style={{ backdropFilter: "blur(20px)" }}>
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-500/30 mb-4">
                        <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">¡Cuenta creada!</h2>
                    <p className="text-zinc-400">Redirigiendo al login…</p>
                </div>
            </div>
        );
    }

    const inputClass = "w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm";
    const labelClass = "block text-xs font-medium text-zinc-400 mb-1.5";

    return (
        <div className="min-h-screen flex bg-[#09090b] relative overflow-hidden">
            <NeuralBackground />

            {/* Ambient glows */}
            <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/8 rounded-full blur-3xl" />
                <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-violet-600/8 rounded-full blur-3xl" />
            </div>

            {/* Left — propuesta de valor */}
            <div className="hidden lg:flex flex-col justify-center px-16 w-1/2 relative z-10">
                <div className="max-w-md">
                    <div className="flex items-center gap-3 mb-10">
                        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                            <Zap className="w-4.5 h-4.5 text-white" />
                        </div>
                        <span className="text-white font-semibold text-lg">AutomatizaPyme</span>
                    </div>

                    <h2 className="text-4xl font-bold text-white leading-tight mb-4">
                        El ERP que trabaja<br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-400">
                            con inteligencia
                        </span>
                    </h2>
                    <p className="text-zinc-400 text-base mb-10 leading-relaxed">
                        Gestiona tu empresa en lenguaje natural. Los agentes IA se encargan del trabajo administrativo para que tú te centres en lo importante.
                    </p>

                    <div className="space-y-4">
                        {FEATURES.map((f, i) => (
                            <div key={i} className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                                    <f.icon className="w-4 h-4 text-indigo-400" />
                                </div>
                                <span className="text-zinc-300 text-sm">{f.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right — formulario */}
            <div className="flex flex-1 items-center justify-center px-6 py-12 relative z-10">
                <div
                    className="w-full max-w-md px-8 py-8 rounded-2xl border border-white/10 shadow-2xl"
                    style={{ background: "rgba(17,17,19,0.88)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)" }}
                >
                    {/* Header móvil */}
                    <div className="flex items-center gap-2.5 mb-6 lg:hidden">
                        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                            <Zap className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-white font-semibold">AutomatizaPyme</span>
                    </div>

                    <h1 className="text-xl font-bold text-white mb-1">Crea tu cuenta</h1>
                    <p className="text-zinc-500 text-sm mb-6">Empieza gratis, sin tarjeta de crédito.</p>

                    <form onSubmit={handleSubmit} className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className={labelClass}>Nombre completo</label>
                                <input name="full_name" type="text" required value={form.full_name} onChange={handleChange} placeholder="Ana García" className={inputClass} />
                            </div>
                            <div>
                                <label className={labelClass}>Email</label>
                                <input name="email" type="email" required value={form.email} onChange={handleChange} placeholder="ana@empresa.es" className={inputClass} />
                            </div>
                        </div>

                        <div className="pt-1 border-t border-white/5">
                            <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Tu empresa</p>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className={labelClass}>Nombre empresa</label>
                                    <input name="company_name" type="text" required value={form.company_name} onChange={handleChange} placeholder="Mi Empresa SL" className={inputClass} />
                                </div>
                                <div>
                                    <label className={labelClass}>NIF / CIF</label>
                                    <input name="nif" type="text" required value={form.nif} onChange={handleChange} placeholder="B12345678" maxLength={9} className={inputClass} />
                                </div>
                            </div>
                        </div>

                        <div className="pt-1 border-t border-white/5">
                            <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Contraseña</p>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className={labelClass}>Contraseña</label>
                                    <input name="password" type="password" required value={form.password} onChange={handleChange} placeholder="Mín. 8 caracteres" className={inputClass} />
                                </div>
                                <div>
                                    <label className={labelClass}>Confirmar</label>
                                    <input name="confirmPassword" type="password" required value={form.confirmPassword} onChange={handleChange} placeholder="Repite la clave" className={inputClass} />
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium transition-all shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 mt-1"
                        >
                            {loading ? "Creando cuenta…" : "Empezar ahora"}
                        </button>
                    </form>

                    <p className="mt-5 text-center text-xs text-zinc-500">
                        ¿Ya tienes cuenta?{" "}
                        <a href="/login" className="text-indigo-400 hover:text-indigo-300 transition">Inicia sesión</a>
                    </p>
                </div>
            </div>
        </div>
    );
}
