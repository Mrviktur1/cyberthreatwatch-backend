// src/app/layout.js
"use client"; // needed for hooks and interactivity

import { Geist, Geist_Mono } from "next/font/google";
import Sidebar from "../components/Sidebar";
import TopBar from "../components/Topbar";
import AIWidget from "../components/AIWidget";
import "./globals.css";

// Load custom fonts
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "CyberThreatWatch",
  description: "Next-gen SOC Dashboard with AI assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        <div className="flex h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-white">
          {/* Sidebar */}
          <Sidebar />

          {/* Main content */}
          <div className="flex-1 flex flex-col">
            {/* TopBar */}
            <TopBar />

            {/* Page content */}
            <main className="flex-1 overflow-auto p-6">{children}</main>
          </div>

          {/* Floating AI Assistant */}
          <AIWidget />
        </div>
      </body>
    </html>
  );
}
