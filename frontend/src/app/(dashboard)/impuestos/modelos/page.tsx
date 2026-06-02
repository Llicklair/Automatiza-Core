import { redirect } from "next/navigation";

// Modelos AEAT se fusionó en «Impuestos» (pestaña Modelos AEAT).
export default function ModelosRedirect() {
    redirect("/impuestos?tab=modelos");
}
