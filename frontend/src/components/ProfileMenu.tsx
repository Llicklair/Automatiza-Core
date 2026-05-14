"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
    User, Building, Mail, KeyRound, LogOut, ChevronDown, RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { getToken } from "@/lib/api/client";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function readJwt(): { name: string; email: string } {
    try {
        const token = getToken();
        if (!token) return { name: "", email: "" };
        const p = JSON.parse(atob(token.split(".")[1]));
        // sub es el UUID del usuario — nunca usarlo como nombre o email
        const email = p.email ?? "";
        const name  = p.full_name || p.name || "";
        return { name, email };
    } catch {
        return { name: "", email: "" };
    }
}

// ─── ProfileMenu principal ─────────────────────────────────────────────────────

export default function ProfileMenu() {
    const router = useRouter();
    const [open, setOpen] = useState(false);
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // 1. Carga inmediata desde JWT (sin petición de red)
        const { name: jwtName, email: jwtEmail } = readJwt();
        if (jwtName) setName(jwtName);
        if (jwtEmail) setEmail(jwtEmail);

        // 2. Si falta el nombre en el JWT (token antiguo), pide /auth/me
        if (!jwtName) {
            if (!getToken()) return;
            api.auth.me()
                .then(data => {
                    setName(data.full_name || data.email?.split("@")[0] || "");
                    if (!jwtEmail) setEmail(data.email || "");
                })
                .catch(() => {});
        }
    }, []);

    // Cerrar al clickar fuera
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        }
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    function logout() {
        localStorage.clear();
        document.cookie = "auth_flag=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        router.push("/login");
    }

    const displayName = name || email || "Mi cuenta";
    const initials = name ? name[0].toUpperCase() : (email ? email[0].toUpperCase() : "U");

    return (
        <>
            <div ref={ref} className="relative z-[9999]">
                <button
                    onClick={() => setOpen(o => !o)}
                    aria-haspopup="true"
                    aria-expanded={open}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors group"
                >
                    <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-foreground text-xs font-bold flex-shrink-0">
                        {initials}
                    </div>
                    <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors max-w-[140px] truncate hidden sm:block">
                        {displayName}
                    </span>
                    <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
                </button>

                {open && (
                    <div className="fixed right-6 top-16 w-56 bg-card border border-border rounded-xl shadow-2xl shadow-black/50 overflow-hidden" style={{ zIndex: 2147483647 }}>
                        {/* Header del menú */}
                        <div className="px-4 py-3 border-b border-border">
                            <p className="text-xs font-semibold text-foreground truncate">{name || "Usuario"}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5 truncate">{email}</p>
                        </div>

                        <div className="py-1">
                            {/* Mi empresa */}
                            <Link
                                href="/configuracion/empresa"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                            >
                                <Building className="w-4 h-4 text-muted-foreground" />
                                Mi empresa
                            </Link>

                            {/* Personalización de perfil */}
                            <Link
                                href="/configuracion/perfil"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                            >
                                <User className="w-4 h-4 text-muted-foreground" />
                                Perfil y empresa
                            </Link>

                            {/* Conectar correo */}
                            <Link
                                href="/integraciones"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                            >
                                <Mail className="w-4 h-4 text-muted-foreground" />
                                Conectar correo
                            </Link>

                            {/* Claves API */}
                            <Link
                                href="/configuracion/api-keys"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                            >
                                <KeyRound className="w-4 h-4 text-muted-foreground" />
                                Claves API
                            </Link>

                            {/* Actualizaciones */}
                            <Link
                                href="/configuracion/actualizaciones"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                            >
                                <RefreshCw className="w-4 h-4 text-muted-foreground" />
                                Actualizaciones
                            </Link>
                        </div>

                        <div className="border-t border-border py-1">
                            <button
                                onClick={logout}
                                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                            >
                                <LogOut className="w-4 h-4" />
                                Cerrar sesión
                            </button>
                        </div>
                    </div>
                )}
            </div>

        </>
    );
}
