// src/components/Sidebar.jsx
import { FaBell, FaList, FaCogs } from 'react-icons/fa';

const links = ['Dashboard', 'Alerts', 'Logs', 'Sensors', 'Settings'];

const iconMap = {
  Dashboard: <FaList />,
  Alerts: <FaBell />,
  Logs: <FaList />,
  Sensors: <FaCogs />,
  Settings: <FaCogs />
};

export default function Sidebar() {
  return (
    <aside className="w-64 bg-gray-800 border-r border-gray-700 flex-shrink-0 h-screen">
      <div className="p-6 text-gray-300 font-bold text-lg">CyberThreatWatch</div>
      <nav className="mt-6 flex flex-col space-y-2">
        {links.map(link => (
          <a
            key={link}
            href={`#${link.toLowerCase()}`}
            className={`px-6 py-2 flex items-center space-x-2 rounded ${
              window.location.hash === `#${link.toLowerCase()}`
                ? "bg-gray-700 text-white"
                : "text-gray-300 hover:bg-gray-700 hover:text-white"
            }`}
          >
            {iconMap[link]}
            <span>{link}</span>
          </a>
        ))}
      </nav>
    </aside>
  );
}
