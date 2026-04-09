"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

// ── Neural network canvas background ──────────────────────────────────────────
function NeuralBackground() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animId: number;

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener("resize", resize);

        // Nodes
        const NODE_COUNT = 60;
        const nodes = Array.from({ length: NODE_COUNT }, () => ({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
            r: Math.random() * 2 + 1.5,
            pulse: Math.random() * Math.PI * 2, // phase offset
        }));

        const MAX_DIST = 160;

        const draw = () => {
            const W = canvas.width;
            const H = canvas.height;
            ctx.clearRect(0, 0, W, H);

            const t = performance.now() / 1000;

            // Move nodes
            for (const n of nodes) {
                n.x += n.vx;
                n.y += n.vy;
                if (n.x < 0 || n.x > W) n.vx *= -1;
                if (n.y < 0 || n.y > H) n.vy *= -1;
                n.pulse += 0.012;
            }

            // Connections
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x;
                    const dy = nodes[i].y - nodes[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < MAX_DIST) {
                        const alpha = (1 - dist / MAX_DIST) * 0.18;
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`; // indigo-500
                        ctx.lineWidth = 0.8;
                        ctx.moveTo(nodes[i].x, nodes[i].y);
                        ctx.lineTo(nodes[j].x, nodes[j].y);
                        ctx.stroke();
                    }
                }
            }

            // Nodes
            for (const n of nodes) {
                const pulse = 0.5 + 0.5 * Math.sin(n.pulse);
                const alpha = 0.25 + 0.2 * pulse;
                const radius = n.r + pulse * 0.8;

                // glow
                const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, radius * 3);
                grad.addColorStop(0, `rgba(139, 92, 246, ${alpha})`);  // violet
                grad.addColorStop(1, `rgba(99, 102, 241, 0)`);
                ctx.beginPath();
                ctx.arc(n.x, n.y, radius * 3, 0, Math.PI * 2);
                ctx.fillStyle = grad;
                ctx.fill();

                // core dot
                ctx.beginPath();
                ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(165, 180, 252, ${alpha + 0.1})`; // indigo-300
                ctx.fill();
            }

            animId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            cancelAnimationFrame(animId);
            window.removeEventListener("resize", resize);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="fixed inset-0 w-full h-full pointer-events-none"
            style={{ zIndex: 0 }}
        />
    );
}

// ── Login form ─────────────────────────────────────────────────────────────────
export default function LoginPage() {
    const router = useRouter();
    const t = useTranslations("auth");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            const data = await api.auth.login(email, password);
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("refresh_token", data.refresh_token);
            document.cookie = "auth_flag=1; path=/; SameSite=Lax";
            router.push("/");
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : t("errorLogin"));
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
            {/* Animated neural network */}
            <NeuralBackground />

            {/* Ambient glow blobs */}
            <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl animate-pulse" />
                <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-violet-600/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1.5s" }} />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-indigo-500/5 rounded-full blur-2xl" />
            </div>

            {/* Card */}
            <div
                className="relative w-full max-w-md px-8 py-10 rounded-2xl border border-white/10 shadow-2xl"
                style={{
                    zIndex: 10,
                    background: "rgba(17, 17, 19, 0.85)",
                    backdropFilter: "blur(20px)",
                    WebkitBackdropFilter: "blur(20px)",
                }}
            >
                {/* Logo */}
                <div className="mb-8 text-center">
                    <img src="/logo.svg" alt="AutomatizaPyme" className="w-14 h-14 rounded-2xl mb-4 shadow-lg shadow-indigo-500/30 ring-1 ring-indigo-400/30 mx-auto" />
                    <h1 className="text-2xl font-bold text-foreground tracking-tight">AutomatizaPyme</h1>
                    <p className="mt-1 text-sm text-muted-foreground">{t("tagline")}</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">{t("email")}</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder={t("emailPlaceholder")}
                            className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10
                                       text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2
                                       focus:ring-indigo-500 focus:border-transparent transition"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">{t("password")}</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder={t("passwordPlaceholder")}
                            className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10
                                       text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2
                                       focus:ring-indigo-500 focus:border-transparent transition"
                        />
                    </div>

                    {error && (
                        <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500
                                   disabled:opacity-50 disabled:cursor-not-allowed text-foreground font-medium
                                   transition-all duration-150 shadow-lg shadow-indigo-500/25
                                   hover:shadow-indigo-500/40"
                    >
                        {loading ? (
                            <span className="inline-flex items-center justify-center gap-2">
                                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                                </svg>
                                {t("loggingIn")}
                            </span>
                        ) : t("login")}
                    </button>
                </form>

                <div className="mt-6 flex flex-col items-center gap-2">
                    <a href="/forgot-password" className="text-xs text-muted-foreground hover:text-foreground transition">
                        {t("forgotPassword")}
                    </a>
                    <p className="text-xs text-muted-foreground">
                        {t("noAccount")}{" "}
                        <a href="/registro" className="text-indigo-400 hover:text-indigo-300 transition">
                            {t("registerHere")}
                        </a>
                    </p>
                </div>
            </div>
        </div>
    );
}
