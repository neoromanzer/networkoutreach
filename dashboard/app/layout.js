import "./globals.css";

export const metadata = { title: "Network Outreach" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <h1 className="text-lg font-semibold">Network Outreach</h1>
        </header>
        <main className="px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
