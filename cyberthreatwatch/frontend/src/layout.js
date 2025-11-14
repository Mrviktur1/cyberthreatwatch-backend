// src/app/layout.js
import './globals.css';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <title>CyberThreatWatch</title>
      </head>
      <body className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-auto">
          {/* Topbar */}
          <Topbar />

          {/* Page content */}
          <main className="flex-1 p-6 bg-gray-900 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
