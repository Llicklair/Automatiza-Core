import { NextRequest, NextResponse } from "next/server";

/**
 * Middleware de autenticación: protege todas las rutas del dashboard.
 * Redirige a /login si no hay access_token en las cookies.
 */
const PUBLIC_PATHS = ["/login", "/register", "/api", "/_next", "/favicon.ico"];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Permitir rutas públicas
    if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
        return NextResponse.next();
    }

    // Para rutas del dashboard, verificar token en cookie
    // Nota: el token principal está en localStorage (client-side),
    // pero el middleware SSR solo puede ver cookies.
    // Usamos una cookie "auth_flag" que el cliente setea al hacer login.
    const authFlag = request.cookies.get("auth_flag");
    if (!authFlag?.value) {
        const loginUrl = new URL("/login", request.url);
        loginUrl.searchParams.set("redirect", pathname);
        return NextResponse.redirect(loginUrl);
    }

    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
