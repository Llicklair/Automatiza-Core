import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
    title: string;
    value: string | number;
    icon?: LucideIcon;
    trend?: {
        value: number;
        direction: "up" | "down" | "neutral";
    };
    description?: string;
    className?: string;
}

export function KpiCard({ title, value, icon: Icon, trend, description, className }: KpiCardProps) {
    return (
        <Card className={cn("relative overflow-hidden", className)}>
            <CardContent className="p-5">
                <div className="flex items-center justify-between">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{title}</p>
                    {Icon && (
                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                            <Icon className="h-4 w-4" />
                        </div>
                    )}
                </div>
                <div className="mt-2">
                    <p className="text-2xl font-bold tracking-tight text-foreground">{value}</p>
                </div>
                {(trend || description) && (
                    <div className="mt-2 flex items-center gap-1.5">
                        {trend && (
                            <span className={cn(
                                "inline-flex items-center gap-0.5 text-xs font-medium",
                                trend.direction === "up" && "text-success",
                                trend.direction === "down" && "text-destructive",
                                trend.direction === "neutral" && "text-muted-foreground",
                            )}>
                                {trend.direction === "up" && <TrendingUp className="h-3 w-3" />}
                                {trend.direction === "down" && <TrendingDown className="h-3 w-3" />}
                                {trend.direction === "neutral" && <Minus className="h-3 w-3" />}
                                {trend.value > 0 ? "+" : ""}{trend.value}%
                            </span>
                        )}
                        {description && <span className="text-xs text-muted-foreground">{description}</span>}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
