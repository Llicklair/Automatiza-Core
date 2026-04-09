import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FormFieldProps {
    label: string;
    error?: string;
    description?: string;
    required?: boolean;
    className?: string;
    children: React.ReactNode;
}

export function FormField({ label, error, description, required, className, children }: FormFieldProps) {
    return (
        <div className={cn("grid gap-2", className)}>
            <Label className={cn(error && "text-destructive")}>
                {label}
                {required && <span className="text-destructive ml-0.5">*</span>}
            </Label>
            {children}
            {description && !error && <p className="text-[0.8rem] text-muted-foreground">{description}</p>}
            {error && <p className="text-[0.8rem] text-destructive">{error}</p>}
        </div>
    );
}
