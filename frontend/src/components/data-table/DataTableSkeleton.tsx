import { Skeleton } from "@/components/ui/skeleton";

interface DataTableSkeletonProps {
    columns?: number;
    rows?: number;
}

export function DataTableSkeleton({ columns = 5, rows = 10 }: DataTableSkeletonProps) {
    return (
        <div className="rounded-md border">
            <div className="border-b bg-muted/50 p-4">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-8 w-[250px]" />
                    <Skeleton className="h-8 w-[100px]" />
                </div>
            </div>
            <div className="border-b">
                <div className="flex items-center h-10 px-4 gap-4">
                    {Array.from({ length: columns }).map((_, i) => (
                        <Skeleton key={i} className="h-4 flex-1" />
                    ))}
                </div>
            </div>
            {Array.from({ length: rows }).map((_, i) => (
                <div key={i} className="flex items-center h-12 px-4 gap-4 border-b last:border-0">
                    {Array.from({ length: columns }).map((_, j) => (
                        <Skeleton key={j} className="h-4 flex-1" />
                    ))}
                </div>
            ))}
        </div>
    );
}
