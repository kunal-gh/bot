import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BOT — AI Analytics Agent",
  description:
    "An intelligent AI-powered data analytics platform. Upload any Excel file and get instant insights through natural language — with built-in ML forecasting, anomaly detection, and clustering.",
  keywords: ["AI analytics", "Excel chatbot", "machine learning", "data analytics", "text-to-SQL", "forecasting"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
