/*
 * Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaPyme
 * SPDX-License-Identifier: LicenseRef-Proprietary
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { GlobalErrorListener } from "@/components/GlobalErrorListener";
import { LicenseListener } from "@/components/LicenseListener";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "AutomatizaPyme — Panel de Control",
    description: "Plataforma de automatización administrativa multiagente para PYMEs",
};

export default async function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const locale = await getLocale();
    const messages = await getMessages();

    return (
        <html lang={locale} suppressHydrationWarning>
            <head>
                {/* UI.DEN — aplica densidad antes de hidratar React para evitar flash. */}
                <script
                    dangerouslySetInnerHTML={{
                        __html: `
try {
  var d = localStorage.getItem('ui_density_v1');
  document.documentElement.setAttribute('data-density', d === 'compact' ? 'compact' : 'comfortable');
} catch (e) { /* ignore */ }
`,
                    }}
                />
            </head>
            <body className={`${inter.className} antialiased`}>
                <NextIntlClientProvider messages={messages}>
                    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
                        <GlobalErrorListener />
                        <LicenseListener />
                        {children}
                    </ThemeProvider>
                </NextIntlClientProvider>
            </body>
        </html>
    );
}
