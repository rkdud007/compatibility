"use client";

import { useState } from "react";

export interface LogEntry {
  step: number;
  message: string;
  color: "green" | "yellow" | "red" | "cyan" | "bold";
  timestamp: number;
}

interface LogConsoleProps {
  logs: LogEntry[];
}

export function LogConsole({ logs }: LogConsoleProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const colorClasses = {
    green: "text-green-600",
    yellow: "text-yellow-600",
    red: "text-red-600",
    cyan: "text-cyan-600",
    bold: "font-bold text-black dark:text-white",
  };

  return (
    <div className="border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-800 text-left font-mono text-sm flex items-center justify-between hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      >
        <span>Log Console ({logs.length} entries)</span>
        <span>{isExpanded ? "▼" : "▶"}</span>
      </button>
      {isExpanded && (
        <div className="bg-black text-white font-mono text-xs p-4 max-h-96 overflow-y-auto">
          {logs.length === 0 ? (
            <div className="text-gray-500">No logs yet...</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="mb-1">
                <span className="text-gray-500 mr-2">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={colorClasses[log.color]}>
                  [Step {log.step}] {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
