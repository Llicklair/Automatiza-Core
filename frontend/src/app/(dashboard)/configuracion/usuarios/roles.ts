export const USER_ROLES = ["admin", "user"] as const;
export const INVITE_ROLES = ["employee", "user", "admin"] as const;

export const ROLE_LABEL: Record<string, string> = {
    admin: "Admin",
    user: "Usuario",
    viewer: "Solo lectura",
    employee: "Empleado (solo Mi portal)",
};
