"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [sheetId, setSheetId] = useState("");
  const [newSheetId, setNewSheetId] = useState("");
  const [updating, setUpdating] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string>("Checking...");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchSettings = async () => {
    try {
      // Fetch Status and Settings
      const [settingsRes, rootRes] = await Promise.all([
        fetch(`${API_URL}/settings`),
        fetch(`${API_URL}/`)
      ]);

      if (settingsRes.ok) {
        const settings = await settingsRes.json();
        setSheetId(settings.sheet_id);
      }

      if (rootRes.ok) {
        const root = await rootRes.json();
        setSyncStatus(root.status); // "Running" or "Stopped"
      }

      setErrorMsg(null);
    } catch (error) {
      console.error("Failed to fetch settings:", error);
      setSyncStatus("Unreachable");
      setErrorMsg("Cannot connect to Backend API");
    }
  };

  const handleUpdateSheetId = async () => {
    if (!newSheetId) return;
    setUpdating(true);
    try {
      await fetch(`${API_URL}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sheet_id: newSheetId }),
      });
      setSheetId(newSheetId);
      setNewSheetId("");
      alert("Sheet ID updated! Sync restarting...");
      fetchSettings(); // Refresh status
      fetchData(); // Refresh data
    } catch (error) {
      alert("Failed to update Sheet ID");
    } finally {
      setUpdating(false);
    }
  };

  const handleWebhookTrigger = async () => {
    try {
      await fetch(`${API_URL}/webhook`, { method: "POST" });
      alert("Sync triggered manually!");
      fetchData();
    } catch (error) {
      console.error("Error in syncing manually", error);
      alert("Failed to trigger sync");
    }
  };

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_URL}/data`);
      if (!res.ok) throw new Error("API responded with error");

      const json = await res.json();

      if (json.data) {
        setData(json.data);
      } else {
        setData([]);
      }
      setLastUpdated(new Date());
      setErrorMsg(null);
    } catch (error) {
      console.error("Failed to fetch data:", error);
      // Don't overwrite errorMsg if it's already set to "Unreachable"
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    fetchData();
    const interval = setInterval(() => {
      fetchData();
      fetchSettings(); // Also poll status
    }, 5000); // Check every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-10 text-xl">Loading...</div>;

  return (
    <main className="min-h-screen p-8 font-sans bg-gray-50 text-gray-800">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-extrabold text-blue-900 tracking-tight">SheetSync Live</h1>
          <div className="flex items-center gap-4">
            <div className={`px-4 py-1 rounded-full text-sm font-semibold ${syncStatus === "Running" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
              }`}>
              Status: {syncStatus}
            </div>
            {errorMsg && (
              <div className="px-4 py-1 rounded-full text-sm font-semibold bg-red-100 text-red-600">
                {errorMsg}
              </div>
            )}
          </div>
        </div>

        {/* Settings Card */}
        <div className="mb-8 p-6 bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex flex-col md:flex-row gap-4 justify-between items-end md:items-center">
            <div>
              <p className="text-sm text-gray-500 uppercase tracking-wide font-semibold mb-1">Active Sheet ID</p>
              <p className="font-mono text-lg bg-gray-100 px-3 py-1 rounded select-all truncate max-w-md">
                {sheetId || "Not Set"}
              </p>
            </div>

            <div className="flex gap-2 w-full md:w-auto">
              <input
                type="text"
                placeholder="Enter new Sheet ID..."
                className="border border-gray-300 p-2 rounded-lg flex-grow md:w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={newSheetId}
                onChange={(e) => setNewSheetId(e.target.value)}
              />
              <button
                onClick={handleUpdateSheetId}
                disabled={updating}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors"
              >
                {updating ? "..." : "Load"}
              </button>
              <button
                onClick={handleWebhookTrigger}
                className="bg-white text-gray-700 border border-gray-300 px-4 py-2 rounded-lg hover:bg-gray-50 font-medium transition-colors"
              >
                ↻ Sync
              </button>
            </div>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
            <h2 className="font-semibold text-gray-700">Live Data</h2>
            {lastUpdated && (
              <span className="text-xs text-gray-500">
                Updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>

          {data.length === 0 ? (
            <div className="p-10 text-center text-gray-400">
              <p className="text-lg">No data available.</p>
              <p className="text-sm mt-2">
                Verify your Sheet ID and ensure the backend is "Running".
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(data[0]).map((key) => (
                      <th
                        key={key}
                        className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {data.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      {Object.values(row).map((val: any, j) => (
                        <td key={j} className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 border-r border-transparent last:border-r-0">
                          {val}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
