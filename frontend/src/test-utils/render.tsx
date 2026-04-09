import { render, type RenderOptions } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React, { type ReactElement } from "react";

/**
 * Custom render that wraps components with any needed providers.
 * Currently no global providers required — extend as needed.
 */
function AllProviders({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}

function customRender(
    ui: ReactElement,
    options?: Omit<RenderOptions, "wrapper">,
) {
    return {
        user: userEvent.setup(),
        ...render(ui, { wrapper: AllProviders, ...options }),
    };
}

// Re-export everything
export * from "@testing-library/react";
export { customRender as render, userEvent };
