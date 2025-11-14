"use client"; // required for hooks

import { useEffect, useState } from "react";

export default function Page() {
  const [alerts, setAlerts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [sensors, setSensors] = useState([]);

  useEffect(() => {
    // Example: fetch alerts from backend
    fetch("http://192.168.1.182:8000/") // replace with your backend URL
      .then((res) => res.json())
      .then((data) => setAlerts(data.alerts || ["Sample alert 1", "Sample alert 2"]))
      .catch((err) => console.error("Error fetching alerts:", err));

    // You can add similar fetch calls for logs and sensors
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
      {/* Alerts box */}
      <div className="p-4 bg-gray-800 rounded shadow">
        <h2 className="text-xl font-semibold text-blue-400">Threat Alerts</h2>
        <ul className="mt-2 space-y-1 text-gray-300">
          {alerts.length > 0
            ? alerts.map((alert, idx) => <li key={idx}>{alert}</li>)
            : "Loading alerts..."}
        </ul>
      </div>

      {/* Logs box */}
      <div className="p-4 bg-gray-800 rounded shadow">
        <h2 className="text-xl font-semibold text-blue-400">Logs</h2>
        {logs.length > 0 ? (
          <ul className="mt-2 space-y-1 text-gray-300">
            {logs.map((log, idx) => <li key={idx}>{log}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-gray-300">Loading logs...</p>
        )}
      </div>

      {/* Sensors box */}
      <div className="p-4 bg-gray-800 rounded shadow">
        <h2 className="text-xl font-semibold text-blue-400">Sensors</h2>
        {sensors.length > 0 ? (
          <ul className="mt-2 space-y-1 text-gray-300">
            {sensors.map((sensor, idx) => <li key={idx}>{sensor}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-gray-300">Loading sensors data...</p>
        )}
      </div>
    </div>
  );
}
