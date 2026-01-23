import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "blowrout | Advance Basketball Prediction",
  description: "Advanced basketball prediction platform with real-time analytics for NBA, NCAA, and European leagues.",
  keywords: ["basketball", "predictions", "NBA", "NCAA", "EuroLeague", "sports analytics"],
};

/**
 * Root Layout - Dark Theme Foundation
 * 
 * No global header - pages handle their own navigation
 * (Landing has nav bar, dashboard pages have sidebar)
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${outfit.variable} antialiased bg-dash-bg text-dash-text-primary`}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
