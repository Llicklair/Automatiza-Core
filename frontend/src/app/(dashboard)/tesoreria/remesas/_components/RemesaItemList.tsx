import { Loader2, FileText, Building2, WalletCards } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { cn } from "@/lib/utils";
import type { RemesaItem, RemesaType } from "../_hooks/useRemesas";
import { TYPE_CONFIG } from "../_hooks/useRemesas";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

interface RemesaItemListProps {
    filtered: RemesaItem[];
    activeType: RemesaType;
    loading: boolean;
    onToggle: (id: string) => void;
    onSelectAll: () => void;
    onDeselectAll: () => void;
}

export default function RemesaItemList({
    filtered, activeType, loading, onToggle, onSelectAll, onDeselectAll,
}: RemesaItemListProps) {
    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            {/* Toolbar */}
            <div className="px-5 py-3 border-b border-border flex items-center justify-between bg-muted">
                <span className="text-sm text-muted-foreground">
                    {filtered.filter(i => i.selected).length} de {filtered.length} seleccionados
                </span>
                <div className="flex gap-3 text-xs">
                    <button onClick={onSelectAll} className="text-primary hover:text-primary transition-colors">Seleccionar todo</button>
                    <span className="text-muted-foreground">|</span>
                    <button onClick={onDeselectAll} className="text-muted-foreground hover:text-foreground transition-colors">Ninguno</button>
                </div>
            </div>

            {loading ? (
                <div className="py-12 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="py-12 text-center">
                    {activeType === "cobros" && <FileText className="w-10 h-10 text-muted-foreground mx-auto mb-3" />}
                    {activeType === "pagos" && <Building2 className="w-10 h-10 text-muted-foreground mx-auto mb-3" />}
                    {activeType === "nominas" && <WalletCards className="w-10 h-10 text-muted-foreground mx-auto mb-3" />}
                    <p className="text-muted-foreground text-sm">
                        {activeType === "cobros" && "No hay facturas emitidas pendientes de cobro"}
                        {activeType === "pagos" && "No hay facturas recibidas pendientes de pago"}
                        {activeType === "nominas" && "No hay nominas emitidas pendientes de transferencia"}
                    </p>
                </div>
            ) : (
                <div className="divide-y divide-border">
                    {filtered.map(item => (
                        <label
                            key={item.id}
                            className={cn(
                                "flex items-center gap-4 px-5 py-4 cursor-pointer transition-colors",
                                item.selected ? "bg-primary/5" : "hover:bg-accent/50"
                            )}
                        >
                            <input
                                type="checkbox"
                                checked={item.selected}
                                onChange={() => onToggle(item.id)}
                                className="w-4 h-4 rounded accent-indigo-500 shrink-0"
                            />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-foreground truncate">{item.label}</p>
                                <p className="text-xs text-muted-foreground">{item.sublabel} · {format(new Date(item.date), "d MMM yyyy", { locale: es })}</p>
                            </div>
                            <span className={cn("text-sm font-semibold shrink-0", TYPE_CONFIG[item.type].color)}>
                                {fmt(item.amount)}
                            </span>
                        </label>
                    ))}
                </div>
            )}
        </div>
    );
}
