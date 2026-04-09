import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

export function KpiCardSkeleton() {
    return (
        <Card>
            <CardContent className="p-5">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-8 w-8 rounded-md" />
                </div>
                <Skeleton className="mt-3 h-8 w-28" />
                <Skeleton className="mt-3 h-3 w-16" />
            </CardContent>
        </Card>
    );
}

export function PageSkeleton() {
    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <div>
                        <Skeleton className="h-5 w-40" />
                        <Skeleton className="mt-1.5 h-3 w-60" />
                    </div>
                </div>
                <Skeleton className="h-9 w-32" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => <KpiCardSkeleton key={i} />)}
            </div>
            <div className="rounded-md border">
                <div className="border-b p-4">
                    <Skeleton className="h-8 w-[250px]" />
                </div>
                {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="flex items-center h-12 px-4 gap-4 border-b">
                        {Array.from({ length: 5 }).map((_, j) => (
                            <Skeleton key={j} className="h-4 flex-1" />
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
}
