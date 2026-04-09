import { redirect } from "next/navigation";

export default function AprobacionesRedirect() {
    redirect("/bandeja?tab=aprobaciones");
}
