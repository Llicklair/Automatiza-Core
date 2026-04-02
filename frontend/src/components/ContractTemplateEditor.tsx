"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Bold, Heading2, Italic, List, ListOrdered, Loader2, Save, X } from "lucide-react";
import { documents } from "@/lib/api/documents";
import { useToastStore } from "@/stores/toast";
import { cn } from "@/lib/utils";

type Props = {
    templateId: string;
    fileName: string;
    initialHtml: string;
    onClose: () => void;
    onSaved: () => void;
};

/**
 * Editor TipTap embebido para plantillas .docx (V2 del plan).
 * Guarda vía PUT body-html → htmldocx en el backend.
 */
export default function ContractTemplateEditor({
    templateId,
    fileName,
    initialHtml,
    onClose,
    onSaved,
}: Props) {
    const show = useToastStore((s) => s.show);
    const [saving, setSaving] = useState(false);

    const editor = useEditor({
        extensions: [StarterKit],
        content: "<p></p>",
        immediatelyRender: false,
        editorProps: {
            attributes: {
                class:
                    "min-h-[min(360px,45vh)] px-3 py-2 focus:outline-none max-w-none text-zinc-200 text-sm leading-relaxed",
            },
        },
    });

    useEffect(() => {
        if (!editor || initialHtml === undefined) return;
        editor.commands.setContent(initialHtml || "<p></p>", { emitUpdate: false });
    }, [editor, initialHtml]);

    const handleSave = useCallback(async () => {
        if (!editor) return;
        setSaving(true);
        try {
            const html = editor.getHTML();
            await documents.contractTemplates.saveBodyHtml(templateId, html);
            show("Plantilla guardada como .docx", "success");
            onSaved();
            onClose();
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "Error al guardar";
            show(msg, "error");
        } finally {
            setSaving(false);
        }
    }, [editor, templateId, onClose, onSaved, show]);

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 p-3 sm:p-4">
            <div
                className="w-full max-w-4xl max-h-[92vh] flex flex-col bg-[#18181b] border border-[#27272a] rounded-xl shadow-2xl overflow-hidden"
                role="dialog"
                aria-labelledby="contract-editor-title"
            >
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#27272a] shrink-0">
                    <div className="min-w-0">
                        <h2 id="contract-editor-title" className="text-sm font-semibold text-white">
                            Editar plantilla
                        </h2>
                        <p className="text-xs text-zinc-500 truncate">{fileName}</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-1.5 text-zinc-500 hover:text-white rounded-lg hover:bg-zinc-800"
                        aria-label="Cerrar"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <p className="px-4 py-2 text-[10px] text-amber-400/95 bg-amber-500/10 border-b border-amber-500/15 leading-snug">
                    Al guardar se reescribe el .docx (estilos complejos pueden simplificarse). Para maquetación fina,
                    usa la app de escritorio y «Abrir en Word».
                </p>

                {editor && (
                    <div className="flex flex-wrap gap-1 px-2 py-2 border-b border-[#27272a] bg-[#111113] shrink-0">
                        <ToolbarBtn
                            label="Negrita"
                            active={editor.isActive("bold")}
                            onClick={() => editor.chain().focus().toggleBold().run()}
                        >
                            <Bold className="w-3.5 h-3.5" />
                        </ToolbarBtn>
                        <ToolbarBtn
                            label="Cursiva"
                            active={editor.isActive("italic")}
                            onClick={() => editor.chain().focus().toggleItalic().run()}
                        >
                            <Italic className="w-3.5 h-3.5" />
                        </ToolbarBtn>
                        <ToolbarBtn
                            label="Título"
                            active={editor.isActive("heading", { level: 2 })}
                            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                        >
                            <Heading2 className="w-3.5 h-3.5" />
                        </ToolbarBtn>
                        <ToolbarBtn
                            label="Lista"
                            active={editor.isActive("bulletList")}
                            onClick={() => editor.chain().focus().toggleBulletList().run()}
                        >
                            <List className="w-3.5 h-3.5" />
                        </ToolbarBtn>
                        <ToolbarBtn
                            label="Lista numerada"
                            active={editor.isActive("orderedList")}
                            onClick={() => editor.chain().focus().toggleOrderedList().run()}
                        >
                            <ListOrdered className="w-3.5 h-3.5" />
                        </ToolbarBtn>
                    </div>
                )}

                <div className="flex-1 overflow-y-auto bg-[#09090b] min-h-0">
                    {!editor ? (
                        <div className="flex items-center justify-center py-16 text-zinc-500 text-sm gap-2">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Cargando editor…
                        </div>
                    ) : (
                        <EditorContent editor={editor} />
                    )}
                </div>

                <div className="flex justify-end gap-2 px-4 py-3 border-t border-[#27272a] bg-[#18181b] shrink-0">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-3 py-1.5 text-xs text-zinc-400 border border-zinc-700 rounded-lg hover:bg-zinc-800 transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={() => void handleSave()}
                        disabled={saving || !editor}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
                    >
                        {saving ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                            <Save className="w-3.5 h-3.5" />
                        )}
                        Guardar .docx
                    </button>
                </div>
            </div>
        </div>
    );
}

function ToolbarBtn({
    children,
    active,
    onClick,
    label,
}: {
    children: ReactNode;
    active: boolean;
    onClick: () => void;
    label: string;
}) {
    return (
        <button
            type="button"
            title={label}
            onClick={onClick}
            className={cn(
                "p-1.5 rounded-md border border-transparent text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors",
                active && "bg-zinc-700 text-white border-zinc-600"
            )}
        >
            {children}
        </button>
    );
}
