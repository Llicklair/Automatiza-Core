import { redirect } from "next/navigation";

// Fusionada con /integraciones (audit UX 2026-07-02): Telegram vive en el hub
// único de integraciones y el placeholder de WhatsApp se retiró.
export default function MensajeriaRedirect() {
    redirect("/integraciones");
}
