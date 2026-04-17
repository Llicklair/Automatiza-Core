import { CheckCircle2, Clock, Send } from "lucide-react";

export function PayrollStatusBadge({ status }: { status: string }) {
    switch (status) {
        case "draft": return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20"><Clock className="w-3 h-3" /> Borrador</span>;
        case "sent":  return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"><Send className="w-3 h-3" /> Emitida</span>;
        case "paid":  return <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" /> Pagada</span>;
        default:      return <span className="text-xs text-muted-foreground capitalize">{status}</span>;
    }
}
