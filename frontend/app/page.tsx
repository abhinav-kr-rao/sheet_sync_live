"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [sheetId, setSheetId] = useState("");
  const [newSheetId, setNewSheetId] = useState("");
  const [updating, setUpdating] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/settings`);
      const json = await res.json();
      setSheetId(json.sheet_id);
    } catch (error) {
      console.error("Failed to fetch settings:", error);
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
      fetchData(); // Refresh data immediately
    } catch (error) {
      alert("Failed to update Sheet ID");
      console.error(error);
    } finally {
      setUpdating(false);
    }
  };

  const handleWebhookTrigger = async () => {
    try {
      await fetch(`${API_URL}/webhook`, { method: "POST" });
      alert("Sync triggered manually!");
    } catch (error) {
      console.error(error);
      console.log("Error in syncing manually", error);

    }
  };

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_URL}/data`);
      // console.log("The result recieved from api is ", res);

      const json = await res.json();
      // console.log("The result recieved from api in json is ", json);

      if (json.data) {
        setData(json.data);
      }
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch data:", error);
      console.log("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    fetchData();
    // Poll every 2 seconds
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-10 text-xl">Loading...</div>;

  return (
    <main className="min-h-screen p-8 font-sans">
      <h1 className="text-3xl font-bold mb-4">Google Sheets Sync</h1>

      {/* Settings Section */}
      <div className="mb-8 p-4 border rounded bg-gray-50">
        <p className="text-sm text-gray-600 mb-2">
          Current Sheet ID: <span className="font-mono font-bold">{sheetId}</span>
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Enter new Sheet ID"
            className="border p-2 rounded w-96 text-black"
            value={newSheetId}
            onChange={(e) => setNewSheetId(e.target.value)}
          />
          <button
            onClick={handleUpdateSheetId}
            disabled={updating}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {updating ? "Updating..." : "Change Sheet"}
          </button>
          <button
            onClick={handleWebhookTrigger}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 ml-4"
          >
            Trigger Sync Now
          </button>
        </div>
      </div>
      <p className="mb-8 text-gray-500">
        Live data from MySQL (synced from Google Sheets)
        {lastUpdated && (
          <span className="ml-2 text-sm text-green-600">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </p>

      {data.length === 0 ? (
        <p>No data found.</p>
      ) : (
        <div className="overflow-x-auto border rounded-lg shadow">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {Object.keys(data[0]).map((key) => (
                  <th
                    key={key}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.map((row, i) => (
                <tr key={i}>
                  {Object.values(row).map((val: any, j) => (
                    <td key={j} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {val}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
