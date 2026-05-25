import "./globals.css";

export const metadata = { title: "Network Outreach" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white min-h-screen">
        <header className="border-b border-gray-800">
          <div className="px-8 py-5 flex items-center justify-between">
            <div>
              <p className="text-xs tracking-widest uppercase text-blue-500 font-medium mb-0.5">
                Network Outreach
              </p>
              <h1 className="text-xl font-semibold tracking-tight">CRM Dashboard</h1>
            </div>
          </div>
        </header>
        <main className="px-8 py-8">{children}</main>
      </body>
    </html>
  );
}
