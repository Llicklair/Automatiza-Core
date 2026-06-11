import { useTranslations } from "next-intl";
import { Search } from "lucide-react";

interface PayrollFiltersProps {
    search: string;
    setSearch: (v: string) => void;
    filterMonth: string;
    setFilterMonth: (v: string) => void;
    filterEmpId: string;
    setFilterEmpId: (v: string) => void;
    uniqueEmployees: [string, string][];
    drafts: number;
}

export function PayrollFilters({
    search, setSearch, filterMonth, setFilterMonth,
    filterEmpId, setFilterEmpId, uniqueEmployees, drafts,
}: PayrollFiltersProps) {
    const t = useTranslations("rrhh");
    return (
        <div className="p-4 border-b border-border flex flex-wrap justify-between items-center gap-3 bg-muted">
            <div className="flex flex-wrap items-center gap-3">
                <div className="relative">
                    <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                    <input type="text" placeholder={t("nominas.filters.searchPlaceholder")} value={search} onChange={e => setSearch(e.target.value)}
                        className="bg-background border border-border text-sm text-foreground rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-emerald-500 transition-colors w-56" />
                </div>
                <input type="month" value={filterMonth} onChange={e => setFilterMonth(e.target.value)} title={t("nominas.filters.byMonth")}
                    className="bg-background border border-border text-sm text-foreground rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500 transition-colors" />
                <select value={filterEmpId} onChange={e => setFilterEmpId(e.target.value)}
                    className="bg-background border border-border text-sm text-foreground rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500 transition-colors">
                    <option value="">{t("nominas.filters.allEmployees")}</option>
                    {uniqueEmployees.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
                </select>
                {(filterMonth || filterEmpId) && (
                    <button type="button" onClick={() => { setFilterMonth(""); setFilterEmpId(""); }}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                        {t("nominas.filters.clear")}
                    </button>
                )}
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground bg-background px-3 py-1.5 rounded-lg border border-border">
                <span className={`w-2 h-2 rounded-full ${drafts > 0 ? "bg-amber-500 animate-pulse" : "bg-accent"}`} />
                {t("nominas.filters.drafts", { n: drafts })}
            </div>
        </div>
    );
}
