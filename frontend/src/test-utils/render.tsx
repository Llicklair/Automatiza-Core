import { render, type RenderOptions } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React, { type ReactElement } from "react";

import { NextIntlClientProvider } from "next-intl";
import messages from "../messages/es.json";

/**
 * Custom render that wraps components with any needed providers.
 */
function AllProviders({ children }: { children: React.ReactNode }) {
    return (
        <NextIntlClientProvider locale="es" messages={messages}>
            {children}
        </NextIntlClientProvider>
    );
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
