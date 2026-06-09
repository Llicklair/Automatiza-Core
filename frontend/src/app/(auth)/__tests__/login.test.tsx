import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@/test-utils/render";
import LoginPage from "../login/page";

// Mock the api module
const loginMock = vi.fn();
vi.mock("@/lib/api", () => ({
    api: {
        auth: {
            login: (...args: unknown[]) => loginMock(...args),
        },
    },
}));

// Capture the router push mock
const pushMock = vi.fn();
vi.mock("next/navigation", async () => {
    return {
        useRouter: () => ({
            push: pushMock,
            replace: vi.fn(),
            back: vi.fn(),
            prefetch: vi.fn(),
            pathname: "/login",
        }),
        usePathname: () => "/login",
        useSearchParams: () => new URLSearchParams(),
        useParams: () => ({}),
    };
});

beforeEach(() => {
    loginMock.mockReset();
    pushMock.mockReset();
    localStorage.clear();
});

describe("LoginPage", () => {
    it("renders email and password fields", () => {
        render(<LoginPage />);

        expect(screen.getByPlaceholderText("tu@empresa.es")).toBeInTheDocument();
        expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
    });

    it("renders the submit button with correct text", () => {
        render(<LoginPage />);

        expect(
            screen.getByRole("button", { name: /iniciar sesión/i }),
        ).toBeInTheDocument();
    });

    it("renders the page title", () => {
        render(<LoginPage />);

        expect(screen.getByText("AutomatizaCore")).toBeInTheDocument();
    });

    it("renders forgot password and register links", () => {
        render(<LoginPage />);

        expect(
            screen.getByText(/¿olvidaste tu contraseña\?/i),
        ).toBeInTheDocument();
        expect(screen.getByText(/regístrarte aquí/i)).toBeInTheDocument();
    });

    it("submits form and redirects on success", async () => {
        loginMock.mockResolvedValueOnce({
            access_token: "test-token",
            refresh_token: "test-refresh",
        });

        const { user } = render(<LoginPage />);

        await user.type(screen.getByPlaceholderText("tu@empresa.es"), "user@test.com");
        await user.type(screen.getByPlaceholderText("••••••••"), "password123");
        await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

        await waitFor(() => {
            expect(loginMock).toHaveBeenCalledWith("user@test.com", "password123");
        });

        await waitFor(() => {
            expect(pushMock).toHaveBeenCalledWith("/");
        });

        expect(localStorage.getItem("access_token")).toBe("test-token");
        expect(localStorage.getItem("refresh_token")).toBe("test-refresh");
    });

    it("displays error message on login failure", async () => {
        loginMock.mockRejectedValueOnce(new Error("Credenciales incorrectas"));

        const { user } = render(<LoginPage />);

        await user.type(screen.getByPlaceholderText("tu@empresa.es"), "bad@test.com");
        await user.type(screen.getByPlaceholderText("••••••••"), "wrong");
        await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

        await waitFor(() => {
            expect(screen.getByText("Credenciales incorrectas")).toBeInTheDocument();
        });

        expect(pushMock).not.toHaveBeenCalled();
    });

    it("shows loading state while submitting", async () => {
        // Make login hang
        loginMock.mockImplementation(() => new Promise(() => {}));

        const { user } = render(<LoginPage />);

        await user.type(screen.getByPlaceholderText("tu@empresa.es"), "user@test.com");
        await user.type(screen.getByPlaceholderText("••••••••"), "pass");
        await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

        await waitFor(() => {
            expect(screen.getByText(/entrando/i)).toBeInTheDocument();
        });
    });
});
