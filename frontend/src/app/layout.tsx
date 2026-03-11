import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "AutomatizaPyme — Panel de Control",
    description: "Plataforma de automatización administrativa multiagente para PYMEs",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="es" className="dark">
            <body className={`${inter.className} bg-[#09090b] text-[#fafafa] antialiased`}>
                {children}
            </body>
        </html>
    );
}
