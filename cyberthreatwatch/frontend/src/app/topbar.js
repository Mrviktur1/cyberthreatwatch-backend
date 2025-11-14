// src/app/components/TopBar.js
"use client";

import { useState, useEffect } from "react";
import { FaBell, FaUserCircle, FaMoon, FaSun, FaRobot } from "react-icons/fa";

// Add more ISO language codes as needed
const languages = [
  "en", "es", "fr", "de", "zh", "ar", "ru", "ja", "pt", "hi", "bn", "ko"
];

export default function TopBar({ onLanguageChange, wsAlerts }) {
  const [lang, setLang] = useState("en");
  const [darkMode, setDarkMode] = useState(false);
  const [notifications, setNotifications] = useState([]);

  // WebSocket placeholder for real-time alerts
  useEffect(() => {
    if (!wsAlerts) return;

    wsAlerts.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setNotifications((prev) => [data.alert, ...prev].slice(0, 5)); // keep last 5 alerts
    };
  }, [wsAlerts]);

  const handleLanguageChange = (e) => {
    const selectedLang = e.target.value;
    setLang(selectedLang);
    if (onLanguageChange) onLanguageChange(selectedLang);
    // TODO: Connect to i18n system like react-i18next
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle("dark");
  };

  const handleAIButton = () => {
    // TODO: Connect to AIWidget modal
    alert("AI Assistant opened. Ask your question here!");
  };

  return (
    <header className="w-full bg-gray-800 dark:bg-gray-900 text-white p-4 flex justify-between items-center shadow-md">
      {/* App Title */}
      <h1 className="text-xl font-bold">CyberThreatWatch</h1>

      {/* Right Controls */}
      <div className="flex items-center space-x-4">
        {/* Notifications */}
        <button className="relative p-2 hover:bg-gray-700 rounded">
          <FaBell size={20} />
          {notifications.length > 0 && (
            <span className="absolute top-0 right-0 inline-flex items-center justify-center px-1 py-0.5 text-xs font-bold text-red-500 bg-white rounded-full">
              {notifications.length}
            </span>
          )}
        </button>

        {/* Language Switcher */}
        <select
          value={lang}
          onChange={handleLanguageChange}
          className="bg-gray-700 text-white px-2 py-1 rounded"
        >
          {languages.map((l) => (
            <option key={l} value={l}>
              {l.toUpperCase()}
            </option>
          ))}
        </select>

        {/* Dark Mode Toggle */}
        <button
          onClick={toggleDarkMode}
          className="p-2 hover:bg-gray-700 rounded"
          title={darkMode ? "Light Mode" : "Dark Mode"}
        >
          {darkMode ? <FaSun size={20} /> : <FaMoon size={20} />}
        </button>

        {/* AI Quick Question */}
        <button
          onClick={handleAIButton}
          className="p-2 hover:bg-gray-700 rounded flex items-center"
          title="Ask AI Assistant"
        >
          <FaRobot size={20} />
        </button>

        {/* User Settings */}
        <div className="relative group">
          <button className="p-2 hover:bg-gray-700 rounded flex items-center">
            <FaUserCircle size={20} />
          </button>
          <div className="absolute right-0 mt-2 w-40 bg-gray-800 border border-gray-700 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity">
            <a href="#profile" className="block px-4 py-2 hover:bg-gray-700">
              Profile
            </a>
            <a href="#settings" className="block px-4 py-2 hover:bg-gray-700">
              Settings
            </a>
            <a href="#logout" className="block px-4 py-2 hover:bg-gray-700">
              Logout
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
