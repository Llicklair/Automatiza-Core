import { ScanLine } from "lucide-react";
import { RefObject } from "react";
import { useTranslations } from "next-intl";

interface DropZoneProps {
    dragOver: boolean;
    setDragOver: (v: boolean) => void;
    onFiles: (files: FileList | null) => void;
    fileInputRef: RefObject<HTMLInputElement | null>;
}

export default function DropZone({ dragOver, setDragOver, onFiles, fileInputRef }: DropZoneProps) {
    const t = useTranslations("escaner");
    return (
        <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); onFiles(e.dataTransfer.files); }}
            onClick={() => fileInputRef.current?.click()}
            className={`rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-300 cursor-pointer ${
                dragOver
                    ? "border-primary bg-primary/10 scale-[1.01]"
                    : "border-border bg-card hover:border-border"
            }`}
        >
            <div className="flex justify-center mb-4">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${
                    dragOver ? "bg-primary/20" : "bg-muted"
                }`}>
                    <ScanLine className={`w-8 h-8 transition-colors ${dragOver ? "text-primary" : "text-muted-foreground"}`} />
                </div>
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-1">
                {t("dropZone.title")}
            </h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
                {t("dropZone.subtitle")}
            </p>
            <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.xls,.csv,.txt,.eml,.msg,.ods,.odt,.webp,.tiff,.tif,.bmp,.gif,.zip"
                onChange={e => onFiles(e.target.files)}
            />
        </div>
    );
}
