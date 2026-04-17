import { differenceInDays, isPast } from "date-fns";
import { AlertTriangle, Clock, Calendar } from "lucide-react";

interface DueBadgeProps {
    dueDate: string | null;
}

export default function DueBadge({ dueDate }: DueBadgeProps) {
    if (!dueDate) return <span className="text-xs text-muted-foreground">Sin vencimiento</span>;
    const d = new Date(dueDate);
    const days = differenceInDays(d, new Date());
    if (isPast(d) && days < 0) {
        return (
            <span className="flex items-center gap-1 text-xs font-medium text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full">
                <AlertTriangle className="w-3 h-3" /> Vencida hace {Math.abs(days)}d
            </span>
        );
    }
    if (days <= 7) {
        return (
            <span className="flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                <Clock className="w-3 h-3" /> {days === 0 ? "Hoy" : `${days}d`}
            </span>
        );
    }
    return (
        <span className="flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            <Calendar className="w-3 h-3" /> {days}d
        </span>
    );
}
