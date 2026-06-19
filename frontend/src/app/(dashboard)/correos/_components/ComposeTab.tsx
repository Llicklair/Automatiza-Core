"use client";

import type { Dispatch, RefObject, SetStateAction } from "react";
import { useTranslations } from "next-intl";
import { Send, Loader2, Paperclip, X, FileText, HardDrive } from "lucide-react";
import type { EmailStatus } from "@/lib/api/messaging";
import type { Document } from "@/lib/api/documents";
import { formatBytes } from "../format";

interface ComposeTabProps {
    to: string;
    setTo: Dispatch<SetStateAction<string>>;
    subject: string;
    setSubject: Dispatch<SetStateAction<string>>;
    body: string;
    setBody: Dispatch<SetStateAction<string>>;
    attachments: Document[];
    uploading: boolean;
    fileRef: RefObject<HTMLInputElement | null>;
    status: EmailStatus | null;
    loading: boolean;
    handleSend: (e: React.FormEvent) => void;
    handleAttach: (e: React.ChangeEvent<HTMLInputElement>) => void;
    removeAttachment: (id: string) => void;
    openDrivePicker: () => void;
}

export function ComposeTab({
    to,
    setTo,
    subject,
    setSubject,
    body,
    setBody,
    attachments,
    uploading,
    fileRef,
    status,
    loading,
    handleSend,
    handleAttach,
    removeAttachment,
    openDrivePicker,
}: ComposeTabProps) {
    const t = useTranslations("correos");
    return (
        <form onSubmit={handleSend} className="space-y-4">
            <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{t("compose.to")}</label>
                <input
                    type="email"
                    required
                    value={to}
                    onChange={e => setTo(e.target.value)}
                    placeholder={t("compose.toPlaceholder")}
                    className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
            </div>
            <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{t("compose.subject")}</label>
                <input
                    type="text"
                    required
                    value={subject}
                    onChange={e => setSubject(e.target.value)}
                    placeholder={t("compose.subjectPlaceholder")}
                    className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
            </div>
            <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{t("compose.message")}</label>
                <textarea
                    required
                    rows={6}
                    value={body}
                    onChange={e => setBody(e.target.value)}
                    placeholder={t("compose.messagePlaceholder")}
                    className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
            </div>

            {/* Attachments */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-muted-foreground">
                        {t("compose.attachments")} {attachments.length > 0 && `(${attachments.length})`}
                    </label>
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={() => fileRef.current?.click()}
                            disabled={uploading}
                            className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 disabled:opacity-50"
                        >
                            {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Paperclip className="w-3.5 h-3.5" />}
                            {t("compose.attachFile")}
                        </button>
                        {status?.providers.gmail && (
                            <button
                                type="button"
                                onClick={openDrivePicker}
                                className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300"
                            >
                                <HardDrive className="w-3.5 h-3.5" />
                                {t("compose.fromDrive")}
                            </button>
                        )}
                        <input
                            ref={fileRef}
                            type="file"
                            multiple
                            className="hidden"
                            onChange={handleAttach}
                        />
                    </div>
                </div>
                {attachments.length > 0 && (
                    <ul className="space-y-1.5">
                        {attachments.map((a) => (
                            <li
                                key={a.id}
                                className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-xs"
                            >
                                <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                                <span className="flex-1 truncate text-foreground">{a.file_name}</span>
                                <span className="text-muted-foreground tabular-nums">{formatBytes(a.file_size)}</span>
                                <button
                                    type="button"
                                    onClick={() => removeAttachment(a.id)}
                                    className="text-muted-foreground hover:text-foreground"
                                    aria-label={t("compose.removeAttachment")}
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <button
                type="submit"
                disabled={loading || uploading}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {t("compose.send")}
            </button>
        </form>
    );
}
