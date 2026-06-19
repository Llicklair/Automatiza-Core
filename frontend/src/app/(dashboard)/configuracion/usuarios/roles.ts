export const USER_ROLES = ["admin", "user"] as const;
export const INVITE_ROLES = ["employee", "user", "admin"] as const;

type RoleTranslator = (key: string) => string;

export function roleLabels(t: RoleTranslator): Record<string, string> {
    return {
        admin: t("usuarios.roleAdmin"),
        user: t("usuarios.roleUser"),
        viewer: t("usuarios.roleViewer"),
        employee: t("usuarios.roleEmployee"),
    };
}
