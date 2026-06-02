"use client";

import { log } from "console";
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
        fetch(`${API_URL}/`),
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
      console.log("res is ", res);
      if (!res.ok) throw new Error("API responded with error");

      const json = await res.json();
      console.log("Fetched Data:", json); // Debug Log

      if (json.data && Array.isArray(json.data) && json.data.length > 0) {
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
    }, 15000); // Check every 15s
    return () => clearInterval(interval);
  }, []);

  if (loading)
    return (
      <div className="min-h-screen bg-black text-white p-10 text-xl">
        Loading...
      </div>
    );

  return (
    <main className="min-h-screen p-8 font-sans bg-black text-white">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-extrabold bg-clip-text text-white tracking-tight">
            SheetSync Live
          </h1>
          <div className="flex items-center gap-4">
            <div
              className={`px-4 py-1 rounded-full text-sm font-semibold border ${
                syncStatus === "Running"
                  ? "bg-green-900/30 text-green-400 border-green-800"
                  : "bg-red-900/30 text-red-400 border-red-800"
              }`}
            >
              Status: {syncStatus}
            </div>
            {errorMsg && (
              <div className="px-4 py-1 rounded-full text-sm font-semibold bg-red-900/50 text-red-400 border border-red-800">
                {errorMsg}
              </div>
            )}
          </div>
        </div>

        {/* Settings Card */}
        <div className="mb-8 p-6 bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800">
          <div className="flex flex-col md:flex-row gap-4 justify-between items-end md:items-center">
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-wide font-semibold mb-2">
                Active Sheet ID
              </p>
              <code className="block bg-black px-4 py-3 rounded-lg text-sm text-green-400 font-mono border border-zinc-800 select-all truncate max-w-xl">
                {sheetId || "Not Set"}
              </code>
            </div>

            <div className="flex gap-2 w-full md:w-auto">
              <input
                type="text"
                placeholder="Enter new Sheet ID..."
                className="bg-black border border-zinc-700 text-white p-2 rounded-lg grow md:w-80 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-zinc-600"
                value={newSheetId}
                onChange={(e) => setNewSheetId(e.target.value)}
              />
              <button
                onClick={handleUpdateSheetId}
                disabled={updating}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium transition-all active:scale-95"
              >
                {updating ? "..." : "Load"}
              </button>
              <button
                onClick={handleWebhookTrigger}
                className="bg-zinc-800 text-zinc-300 border border-zinc-700 px-4 py-2 rounded-lg hover:bg-zinc-700 font-medium transition-all"
              >
                ↻ Sync
              </button>
            </div>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900">
            <h2 className="font-semibold text-zinc-200">Live Data</h2>
            {lastUpdated && (
              <span className="text-xs text-zinc-500 font-mono">
                Updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>

          {data.length === 0 ? (
            <div className="p-16 text-center text-zinc-500">
              <p className="text-xl font-medium mb-2">No data found</p>
              <p className="text-sm">
                Ensure the Google Sheet is not empty and "Share" permissions are
                set.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-zinc-800">
                <thead className="bg-black">
                  <tr>
                    {Object.keys(data[0]).map((key) => (
                      <th
                        key={key}
                        className="px-6 py-4 text-left text-xs font-semibold text-zinc-400 uppercase tracking-wider"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-zinc-900 divide-y divide-zinc-800">
                  {data.map((row, i) => (
                    <tr
                      key={i}
                      className="hover:bg-zinc-800/50 transition-colors"
                    >
                      {Object.values(row).map((val: any, j) => (
                        <td
                          key={j}
                          className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300"
                        >
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
