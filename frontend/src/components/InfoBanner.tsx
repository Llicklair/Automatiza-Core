"use client";

import { useState, useEffect } from "react";
import { Info, X } from "lucide-react";

interface InfoBannerProps {
    id: string;
    title: string;
    children: React.ReactNode;
}

export default function InfoBanner({ id, title, children }: InfoBannerProps) {
    const storageKey = `info-banner-dismissed-${id}`;
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        if (!localStorage.getItem(storageKey)) setVisible(true);
    }, [storageKey]);

    if (!visible) return null;

    const dismiss = () => {
        localStorage.setItem(storageKey, "1");
        setVisible(false);
    };

    return (
        <div className="mb-6 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 relative">
            <button
                onClick={dismiss}
                className="absolute top-3 right-3 text-zinc-500 hover:text-white transition"
                aria-label="Cerrar"
            >
                <X className="w-4 h-4" />
            </button>
            <div className="flex gap-3">
                <div className="flex-shrink-0 mt-0.5">
                    <Info className="w-5 h-5 text-indigo-400" />
                </div>
                <div className="pr-6">
                    <h3 className="text-sm font-semibold text-indigo-300 mb-1">{title}</h3>
                    <div className="text-sm text-zinc-400 leading-relaxed space-y-1">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
