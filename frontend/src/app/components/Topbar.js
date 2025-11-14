export default function Topbar() {
  return (
    <header className="flex items-center justify-between h-16 px-6 bg-gray-800 border-b border-gray-700">
      <h1 className="text-xl font-bold text-blue-400">CyberThreatWatch</h1>
      <div className="flex items-center space-x-4">
        <span className="text-gray-300">Victor Enemmoh</span>
        <button className="px-3 py-1 bg-blue-600 rounded hover:bg-blue-500">Logout</button>
      </div>
    </header>
  );
}
