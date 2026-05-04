import type { LucideIcon } from "lucide-react";

interface PageHeaderProps {
    title: string;
    description?: React.ReactNode;
    icon?: LucideIcon;
    actions?: React.ReactNode;
    children?: React.ReactNode;
}

export function PageHeader({ title, description, icon: Icon, actions, children }: PageHeaderProps) {
    return (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
                {Icon && (
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-5 w-5" />
                    </div>
                )}
                <div>
                    <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
                    {description && <p className="text-sm text-muted-foreground mt-0.5">{description}</p>}
                </div>
            </div>
            {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
            {children}
        </div>
    );
}
