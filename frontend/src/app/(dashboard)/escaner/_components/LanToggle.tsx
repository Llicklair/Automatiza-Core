import { Wifi, WifiOff } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ElectronNetworkStatus } from "../_hooks/useEscaner";

interface LanToggleProps {
    netStatus: ElectronNetworkStatus;
    netToggling: boolean;
    onToggle: (next: boolean) => void;
}

export default function LanToggle({ netStatus, netToggling, onToggle }: LanToggleProps) {
    const t = useTranslations("escaner");
    return (
        <div className="rounded-xl border border-border bg-card px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-3">
                {netStatus.localNetworkEnabled ? (
                    <Wifi className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
                ) : (
                    <WifiOff className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                )}
                <div>
                    <p className="text-sm font-medium text-foreground">{t("lanToggle.title")}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {netStatus.localNetworkEnabled
                            ? t("lanToggle.enabledHint", { lanIP: netStatus.lanIP || "\u2014" })
                            : t("lanToggle.disabledHint")}
                    </p>
                </div>
            </div>
            <label className="flex items-center gap-3 cursor-pointer select-none self-end sm:self-center">
                <span className="text-xs text-muted-foreground">
                    {netToggling ? t("lanToggle.restarting") : netStatus.localNetworkEnabled ? t("lanToggle.lanActive") : t("lanToggle.localOnly")}
                </span>
                <button
                    type="button"
                    role="switch"
                    aria-checked={netStatus.localNetworkEnabled}
                    disabled={netToggling}
                    onClick={() => void onToggle(!netStatus.localNetworkEnabled)}
                    className={`relative w-11 h-6 rounded-full transition-colors ${
                        netStatus.localNetworkEnabled ? "bg-emerald-600" : "bg-accent"
                    } ${netToggling ? "opacity-60" : ""}`}
                >
                    <span
                        className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform ${
                            netStatus.localNetworkEnabled ? "translate-x-5" : ""
                        }`}
                    />
                </button>
            </label>
        </div>
    );
}
