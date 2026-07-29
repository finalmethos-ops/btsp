import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Buddy's Purchasing Intelligence",
  description:
    "Data-driven purchasing, operations, and vendor intelligence for Buddy's.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `(() => {
              if (!['localhost', '127.0.0.1', '::1'].includes(location.hostname) || !('serviceWorker' in navigator)) return;
              navigator.serviceWorker.getRegistrations().then((registrations) => {
                registrations
                  .filter((registration) => registration.active?.scriptURL.endsWith('/event-sw.js'))
                  .forEach((registration) => registration.unregister());
              });
            })();`,
          }}
        />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
