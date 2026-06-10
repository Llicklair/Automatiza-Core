"use client";

import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import type { EmailStatus, InboxMessage, EmailDetail, DriveFile, EmailClassification } from "@/lib/api/messaging";
import type { Document } from "@/lib/api/documents";
import type { TabKey } from "../constants";

export function useCorreos() {
    const [activeTab, setActiveTab] = useState<TabKey>("bandeja");
    const [status, setStatus] = useState<EmailStatus | null>(null);

    // Compose form
    const [to, setTo] = useState("");
    const [subject, setSubject] = useState("");
    const [body, setBody] = useState("");
    const [attachments, setAttachments] = useState<Document[]>([]);
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    // AI instruct form
    const [instruction, setInstruction] = useState("");

    // Inbox
    const [inboxMessages, setInboxMessages] = useState<InboxMessage[] | null>(null);
    const [inboxLoading, setInboxLoading] = useState(false);
    const [inboxProvider, setInboxProvider] = useState<"gmail" | "outlook" | null>(null);
    const [selectedMsg, setSelectedMsg] = useState<EmailDetail | null>(null);
    const [classMap, setClassMap] = useState<Record<string, EmailClassification>>({});
    const [classLoading, setClassLoading] = useState(false);
    const [draftLoading, setDraftLoading] = useState(false);
    const [draftError, setDraftError] = useState<string | null>(null);
    const [bodyLoading, setBodyLoading] = useState(false);

    // Drive picker
    const [showDrive, setShowDrive] = useState(false);
    const [driveFiles, setDriveFiles] = useState<DriveFile[] | null>(null);
    const [driveLoading, setDriveLoading] = useState(false);
    const [driveQuery, setDriveQuery] = useState("");
    const [importingId, setImportingId] = useState<string | null>(null);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

    useEffect(() => {
        api.messaging.email.status().then(setStatus).catch(() => null);
    }, []);

    async function classifyInbox(msgs: InboxMessage[]) {
        if (msgs.length === 0) return;
        setClassLoading(true);
        try {
            const res = await api.messaging.email.classify(
                msgs.map((m) => ({ id: m.id, from: m.from, subject: m.subject, snippet: m.snippet })),
            );
            const map: Record<string, EmailClassification> = {};
            for (const item of res.items) map[item.id] = item;
            setClassMap(map);
        } catch {
            // Silencioso: la bandeja sigue funcional sin clasificación.
        } finally {
            setClassLoading(false);
        }
    }

    async function handleDraftReply() {
        if (!selectedMsg) return;
        setDraftLoading(true);
        setDraftError(null);
        try {
            const draft = await api.messaging.email.draftReply(selectedMsg.id);
            // Pre-rellenar composer y cambiar de pestaña
            setTo(selectedMsg.from);
            setSubject(draft.subject || `Re: ${selectedMsg.subject}`);
            setBody(draft.body);
            setSelectedMsg(null);
            setActiveTab("componer");
        } catch (e) {
            setDraftError(e instanceof Error ? e.message : "No se pudo redactar el borrador");
        } finally {
            setDraftLoading(false);
        }
    }

    async function loadInbox() {
        setInboxLoading(true);
        try {
            const res = await api.messaging.email.inbox(20);
            setInboxMessages(res.messages);
            setInboxProvider(res.provider);
            // Lanzar clasificación IA en segundo plano (no bloquea la UI)
            classifyInbox(res.messages);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al cargar la bandeja" });
            setInboxMessages([]);
        } finally {
            setInboxLoading(false);
        }
    }

    useEffect(() => {
        if (activeTab === "bandeja" && inboxMessages === null) {
            loadInbox();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab]);

    async function openMessage(id: string) {
        setBodyLoading(true);
        setSelectedMsg(null);
        try {
            const detail = await api.messaging.email.getMessage(id);
            setSelectedMsg(detail);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al cargar el mensaje" });
        } finally {
            setBodyLoading(false);
        }
    }

    async function handleSend(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setResult(null);
        try {
            const ids = attachments.map((a) => a.id);
            const res = await api.messaging.email.send(to, subject, body, ids.length ? ids : undefined);
            setResult({ ok: true, message: res.result });
            setTo(""); setSubject(""); setBody(""); setAttachments([]);
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al enviar" });
        } finally {
            setLoading(false);
        }
    }

    async function handleAttach(e: React.ChangeEvent<HTMLInputElement>) {
        const files = Array.from(e.target.files ?? []);
        if (files.length === 0) return;
        setUploading(true);
        try {
            const uploaded = await Promise.all(
                files.map((f) => api.documents.upload(f, "email-attachment"))
            );
            setAttachments((prev) => [...prev, ...uploaded]);
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al subir el archivo" });
        } finally {
            setUploading(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    }

    function removeAttachment(id: string) {
        setAttachments((prev) => prev.filter((a) => a.id !== id));
    }

    async function openDrivePicker() {
        setShowDrive(true);
        if (driveFiles === null) {
            await loadDrive("");
        }
    }

    async function loadDrive(q: string) {
        setDriveLoading(true);
        try {
            const res = await api.messaging.drive.list("root", q);
            setDriveFiles(res.files);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al listar Drive" });
            setDriveFiles([]);
        } finally {
            setDriveLoading(false);
        }
    }

    async function attachFromDrive(file: DriveFile) {
        if (file.is_folder) return;
        setImportingId(file.id);
        try {
            const doc = await api.messaging.drive.attachAsDocument(file.id);
            setAttachments((prev) => [...prev, doc]);
            setShowDrive(false);
        } catch (err) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al importar de Drive" });
        } finally {
            setImportingId(null);
        }
    }

    async function handleInstruct(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setResult(null);
        try {
            const res = await api.messaging.email.instruct(instruction);
            setResult({ ok: res.success, message: res.action });
            if (res.success) setInstruction("");
        } catch (err: unknown) {
            setResult({ ok: false, message: err instanceof Error ? err.message : "Error al procesar instrucción" });
        } finally {
            setLoading(false);
        }
    }

    return {
        activeTab, setActiveTab,
        status,
        to, setTo,
        subject, setSubject,
        body, setBody,
        attachments,
        uploading,
        fileRef,
        instruction, setInstruction,
        inboxMessages,
        inboxLoading,
        inboxProvider,
        selectedMsg, setSelectedMsg,
        classMap,
        classLoading,
        draftLoading,
        draftError,
        bodyLoading, setBodyLoading,
        showDrive, setShowDrive,
        driveFiles,
        driveLoading,
        driveQuery, setDriveQuery,
        importingId,
        loading,
        result, setResult,
        handleDraftReply,
        loadInbox,
        openMessage,
        handleSend,
        handleAttach,
        removeAttachment,
        openDrivePicker,
        loadDrive,
        attachFromDrive,
        handleInstruct,
    };
}

export type CorreosState = ReturnType<typeof useCorreos>;
