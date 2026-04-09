import { redirect } from "next/navigation";

export default function ActividadesRedirect() {
    redirect("/bandeja?tab=actividad");
}
