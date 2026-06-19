"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { BarChart3, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { llmUsage, LlmMonthStats } from "@/lib/api/llm_usage";

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function monthLabel(ym: string) {
  const [y, m] = ym.split("-");
  const d = new Date(Number(y), Number(m) - 1, 1);
  return d.toLocaleDateString("es-ES", { month: "short", year: "2-digit" });
}

export function UsageStatsCard() {
  const t = useTranslations("configuracion");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<LlmMonthStats[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [activeMonth, setActiveMonth] = useState<string | null>(null);

  useEffect(() => {
    llmUsage
      .stats(3)
      .then((r) => {
        setData(r.months);
        if (r.months.length > 0) setActiveMonth(r.months[0].month);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (data.length === 0 || data.every((m) => m.total_calls === 0)) return null;

  const current = data.find((m) => m.month === activeMonth) ?? data[0];

  return (
    <div className="bg-card border border-border rounded-xl p-5 mt-5">
      <button
        className="w-full flex items-center justify-between"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          <span className="font-medium text-sm">{t("apiKeys.usageTitle")}</span>
          <span className="text-xs text-muted-foreground ml-1">
            {t("apiKeys.usdEstimate", { amount: data.reduce((s, m) => s + m.estimated_cost_usd, 0).toFixed(2) })}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4">
          {/* Selector de mes */}
          <div className="flex gap-2">
            {data.map((m) => (
              <button
                key={m.month}
                onClick={() => setActiveMonth(m.month)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                  activeMonth === m.month
                    ? "bg-primary text-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/70"
                }`}
              >
                {monthLabel(m.month)}
              </button>
            ))}
          </div>

          {/* Resumen del mes */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: t("apiKeys.calls"), value: String(current.total_calls) },
              {
                label: t("apiKeys.tokens"),
                value: fmt(current.total_tokens_in + current.total_tokens_out),
              },
              {
                label: t("apiKeys.estCost"),
                value: `$${current.estimated_cost_usd.toFixed(3)}`,
              },
            ].map(({ label, value }) => (
              <div key={label} className="bg-muted/40 rounded-lg p-3 text-center">
                <p className="text-lg font-semibold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </div>
            ))}
          </div>

          {/* Detalle por agente */}
          {current.by_agent.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left py-1.5 pr-4">{t("apiKeys.agent")}</th>
                    <th className="text-right py-1.5 pr-4">{t("apiKeys.calls")}</th>
                    <th className="text-right py-1.5 pr-4">{t("apiKeys.tokensIn")}</th>
                    <th className="text-right py-1.5 pr-4">{t("apiKeys.tokensOut")}</th>
                    <th className="text-right py-1.5">{t("apiKeys.estCost")}</th>
                  </tr>
                </thead>
                <tbody>
                  {current.by_agent.map((row, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-muted/20">
                      <td className="py-1.5 pr-4">
                        <span className="font-medium capitalize">{row.agent}</span>
                        <span className="text-muted-foreground ml-1.5">({row.provider})</span>
                      </td>
                      <td className="text-right py-1.5 pr-4">{row.calls}</td>
                      <td className="text-right py-1.5 pr-4">{fmt(row.tokens_in)}</td>
                      <td className="text-right py-1.5 pr-4">{fmt(row.tokens_out)}</td>
                      <td className="text-right py-1.5">${row.cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            {t("apiKeys.usageFootnote")}
          </p>
        </div>
      )}
    </div>
  );
}
