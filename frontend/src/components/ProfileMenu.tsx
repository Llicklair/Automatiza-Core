"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
    User, Building, Mail, KeyRound, LogOut, ChevronDown,
} from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getUserEmail(): string {
    try {
        const token = localStorage.getItem("access_token");
        if (!token) return "";
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.sub || payload.email || "";
    } catch {
        return "";
    }
}

// ─── ProfileMenu principal ─────────────────────────────────────────────────────

export default function ProfileMenu() {
    const router = useRouter();
    const [open, setOpen] = useState(false);
    const [email, setEmail] = useState("");
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setEmail(getUserEmail());
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
        router.push("/login");
    }

    const initials = email ? email[0].toUpperCase() : "U";

    return (
        <>
            <div ref={ref} className="relative">
                <button
                    onClick={() => setOpen(o => !o)}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors group"
                >
                    <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                        {initials}
                    </div>
                    <span className="text-sm text-zinc-400 group-hover:text-white transition-colors max-w-[140px] truncate hidden sm:block">
                        {email || "Mi cuenta"}
                    </span>
                    <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
                </button>

                {open && (
                    <div className="absolute right-0 top-full mt-2 w-56 bg-[#18181b] border border-[#27272a] rounded-xl shadow-2xl shadow-black/50 z-50 overflow-hidden">
                        {/* Header del menú */}
                        <div className="px-4 py-3 border-b border-[#27272a]">
                            <p className="text-xs font-semibold text-white truncate">{email || "Usuario"}</p>
                            <p className="text-[10px] text-zinc-500 mt-0.5">Plan Pro</p>
                        </div>

                        <div className="py-1">
                            {/* Mi empresa */}
                            <Link
                                href="/configuracion/empresa"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
                            >
                                <Building className="w-4 h-4 text-zinc-500" />
                                Mi empresa
                            </Link>

                            {/* Personalización de perfil */}
                            <Link
                                href="/configuracion/perfil"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
                            >
                                <User className="w-4 h-4 text-zinc-500" />
                                Perfil y empresa
                            </Link>

                            {/* Conectar correo */}
                            <Link
                                href="/integraciones"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
                            >
                                <Mail className="w-4 h-4 text-zinc-500" />
                                Conectar correo
                            </Link>

                            {/* Claves API */}
                            <Link
                                href="/configuracion/api-keys"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
                            >
                                <KeyRound className="w-4 h-4 text-zinc-500" />
                                Claves API
                            </Link>
                        </div>

                        <div className="border-t border-[#27272a] py-1">
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
