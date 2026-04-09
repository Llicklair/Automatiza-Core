import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// ── Mock next/navigation ─────────────────────────────────────────────────────
const pushMock = vi.fn();
const replaceMock = vi.fn();
const backMock = vi.fn();
const prefetchMock = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: pushMock,
        replace: replaceMock,
        back: backMock,
        prefetch: prefetchMock,
        pathname: "/",
    }),
    usePathname: () => "/",
    useSearchParams: () => new URLSearchParams(),
    useParams: () => ({}),
}));

// ── Mock next/image ──────────────────────────────────────────────────────────
vi.mock("next/image", () => ({
    __esModule: true,
    default: (props: Record<string, unknown>) => {
        const imgProps = { ...props } as Record<string, unknown>;
        delete imgProps.fill;
        delete imgProps.priority;
        return imgProps;
    },
}));

// ── Mock next/link ───────────────────────────────────────────────────────────
vi.mock("next/link", () => ({
    __esModule: true,
    default: ({ children, ...rest }: { children: React.ReactNode; [key: string]: unknown }) => {
        return children;
    },
}));

// ── Browser API mocks ────────────────────────────────────────────────────────
class ResizeObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
}
globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

class IntersectionObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    constructor(
        _callback: IntersectionObserverCallback,
        _options?: IntersectionObserverInit,
    ) {}
}
globalThis.IntersectionObserver = IntersectionObserverMock as unknown as typeof IntersectionObserver;

Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// ── Export mocks for test access ─────────────────────────────────────────────
export { pushMock, replaceMock, backMock, prefetchMock };
