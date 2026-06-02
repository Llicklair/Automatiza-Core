import { redirect } from "next/navigation";

// Horarios se fusionó en «Jornada y ausencias» (pestaña Horarios).
export default function HorariosRedirect() {
    redirect("/rrhh/jornada?tab=horarios");
}
