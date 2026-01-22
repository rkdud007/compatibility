"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { apiClient, Conversation } from "@/lib/api-client";
import { LogConsole, LogEntry } from "@/components/log-console";

type AuthState = {
  isAuthenticated: boolean;
  username: string;
  password: string;
};

type UserData = {
  conversations: Conversation[] | null;
  prompt: string;
  expected: string;
};

export default function RoomPage() {
  const params = useParams();
  const roomId = params.roomId as string;

  // Auth state - initialize without localStorage to avoid hydration mismatch
  const [auth, setAuth] = useState<AuthState>({
    isAuthenticated: false,
    username: "",
    password: "",
  });

  // Form inputs for login
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // User data state
  const [userData, setUserData] = useState<UserData>({
    conversations: null,
    prompt: "",
    expected: "",
  });

  // Load from localStorage after mount
  useEffect(() => {
    const saved = localStorage.getItem(`room_${roomId}_auth`);
    if (saved) {
      const authData = JSON.parse(saved);
      setAuth(authData);

      // Load user data for this username
      if (authData.isAuthenticated) {
        const userDataSaved = localStorage.getItem(
          `room_${roomId}_data_${authData.username}`
        );
        if (userDataSaved) {
          setUserData(JSON.parse(userDataSaved));
        }
      }
    }
  }, [roomId]);

  const [roomStatus, setRoomStatus] = useState<{
    state: string;
    user_a_ready: boolean;
    user_b_ready: boolean;
    user_a_username: string | null;
    user_b_username: string | null;
    result?: { a_to_b_score: number; b_to_a_score: number };
  } | null>(null);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isReady, setIsReady] = useState(false);

  // Save auth to localStorage
  useEffect(() => {
    localStorage.setItem(`room_${roomId}_auth`, JSON.stringify(auth));
  }, [roomId, auth]);

  // Save user data to localStorage
  useEffect(() => {
    if (auth.isAuthenticated) {
      localStorage.setItem(
        `room_${roomId}_data_${auth.username}`,
        JSON.stringify(userData)
      );
    }
  }, [roomId, auth.isAuthenticated, auth.username, userData]);

  const addLog = useCallback(
    (step: number, message: string, color: LogEntry["color"] = "cyan") => {
      setLogs((prev) => [
        ...prev,
        { step, message, color, timestamp: Date.now() },
      ]);
    },
    []
  );

  const fetchStatus = useCallback(async () => {
    try {
      const status = await apiClient.getRoomStatus(roomId);
      setRoomStatus(status);
      return status;
    } catch (err) {
      addLog(0, `Failed to fetch status: ${err}`, "red");
      return null;
    }
  }, [roomId, addLog]);

  useEffect(() => {
    addLog(0, `Room ID: ${roomId}`, "cyan");
    fetchStatus();
  }, [roomId, fetchStatus, addLog]);

  const handleLogin = () => {
    if (!loginUsername || !loginPassword) {
      alert("Please enter both username and password");
      return;
    }

    setAuth({
      isAuthenticated: true,
      username: loginUsername,
      password: loginPassword,
    });

    addLog(1, `Logged in as ${loginUsername}`, "green");

    // Load saved data for this username if it exists
    const saved = localStorage.getItem(
      `room_${roomId}_data_${loginUsername}`
    );
    if (saved) {
      setUserData(JSON.parse(saved));
      addLog(1, `Loaded previous session data`, "cyan");
    }
  };

  const handleLogout = () => {
    setAuth({ isAuthenticated: false, username: "", password: "" });
    setUserData({ conversations: null, prompt: "", expected: "" });
    setIsReady(false);
    setLoginUsername("");
    setLoginPassword("");
    addLog(1, `Logged out`, "yellow");
  };

  const handleFileUpload = async (file: File) => {
    try {
      const text = await file.text();
      const conversations = JSON.parse(text);
      setUserData((prev) => ({ ...prev, conversations }));
      addLog(2, `Loaded ${conversations.length} conversations`, "green");
    } catch (err) {
      alert(`Failed to parse JSON file: ${err}`);
    }
  };

  const handleLoadDefault = async () => {
    try {
      // For now, just load default user_a conversations
      // You could modify this to have different defaults based on username
      const response = await fetch(`/api/default-conversations?user=a`);
      if (!response.ok) {
        throw new Error("Failed to load default conversations");
      }
      const conversations = await response.json();
      setUserData((prev) => ({ ...prev, conversations }));
      addLog(2, `Loaded default conversations`, "green");
    } catch (err) {
      alert(`Failed to load default conversations: ${err}`);
    }
  };

  const handleSubmit = async () => {
    if (!userData.conversations || !userData.prompt || !userData.expected) {
      alert("Please fill in all fields (conversations, prompt, expected)");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Step 1: Upload data
      addLog(2, `Uploading data for ${auth.username}`, "cyan");

      await apiClient.uploadData(roomId, {
        username: auth.username,
        password: auth.password,
        conversations: userData.conversations,
        prompt: userData.prompt,
        expected: userData.expected,
      });

      addLog(2, `✓ Data uploaded successfully`, "green");

      // Step 2: Mark ready
      addLog(3, `Marking ${auth.username} as ready`, "cyan");

      await apiClient.markReady(roomId, {
        username: auth.username,
        password: auth.password,
      });

      addLog(3, `✓ ${auth.username} is ready`, "green");
      setIsReady(true);

      const status = await fetchStatus();
      if (status?.user_a_ready && status?.user_b_ready) {
        addLog(3, "→ Both users ready! Evaluation triggered!", "yellow");
        await pollForCompletion();
      }
    } catch (err) {
      const errorMsg = `Failed to submit: ${err}`;
      setError(errorMsg);
      addLog(2, errorMsg, "red");
    } finally {
      setIsSubmitting(false);
    }
  };

  const pollForCompletion = useCallback(async () => {
    setIsPolling(true);
    addLog(4, "Waiting for evaluation...", "cyan");
    addLog(4, "The evaluation performs 4 OpenAI API calls:", "yellow");
    addLog(4, "  1/4: Answer A's prompt with B's conversations", "yellow");
    addLog(4, "  2/4: Calculate A→B similarity score", "yellow");
    addLog(4, "  3/4: Answer B's prompt with A's conversations", "yellow");
    addLog(4, "  4/4: Calculate B→A similarity score", "yellow");
    addLog(4, "This typically takes 30-60 seconds total.", "yellow");

    const startTime = Date.now();
    const timeout = 120000; // 120 seconds

    const poll = async () => {
      const status = await fetchStatus();
      if (!status) {
        setIsPolling(false);
        addLog(4, "✗ Failed to get status", "red");
        return;
      }

      if (status.state === "COMPLETED") {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        addLog(4, `✓ Evaluation completed in ${elapsed}s`, "green");
        setIsPolling(false);
        return;
      }

      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      if (elapsed * 1000 >= timeout) {
        addLog(4, "✗ Timeout waiting for evaluation", "red");
        setIsPolling(false);
        return;
      }

      // Poll every 2 seconds
      setTimeout(poll, 2000);
    };

    poll();
  }, [fetchStatus, addLog]);

  // Auto-poll for status when user is ready but waiting for other user or evaluation
  useEffect(() => {
    if (!isReady || isPolling) return;

    const intervalId = setInterval(async () => {
      const status = await fetchStatus();
      if (!status) return;

      // If both users are ready and we weren't polling yet, start polling
      if (status.user_a_ready && status.user_b_ready && !isPolling) {
        addLog(3, "→ Both users ready! Evaluation triggered!", "yellow");
        clearInterval(intervalId);
        await pollForCompletion();
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(intervalId);
  }, [isReady, isPolling, fetchStatus, addLog, pollForCompletion]);

  const copyRoomId = () => {
    navigator.clipboard.writeText(roomId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const result = roomStatus?.result;
  const average = result
    ? (result.a_to_b_score + result.b_to_a_score) / 2
    : null;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold">Room: {roomId}</h1>
            <button
              onClick={copyRoomId}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
            >
              {copied ? "Copied!" : "Copy ID"}
            </button>
          </div>

          {roomStatus && (
            <div className="flex items-center gap-4 text-sm">
              <span className="font-mono">
                State: <span className="font-bold">{roomStatus.state}</span>
              </span>
              <span className="font-mono">
                {roomStatus.user_a_username || "User A"}:{" "}
                {roomStatus.user_a_ready ? "✓" : "✗"}
              </span>
              <span className="font-mono">
                {roomStatus.user_b_username || "User B"}:{" "}
                {roomStatus.user_b_ready ? "✓" : "✗"}
              </span>
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Main section - either login or data upload */}
        <div className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg p-6 space-y-4">
          {!auth.isAuthenticated ? (
            // Login Form
            <>
              <h2 className="text-xl font-semibold">Login to Room</h2>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium">Username</label>
                  <input
                    type="text"
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium">Password</label>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900"
                  />
                </div>
                <button
                  onClick={handleLogin}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition-colors"
                >
                  Login
                </button>
              </div>
            </>
          ) : (
            // Data Upload Form
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">
                  Logged in as: {auth.username} {isReady && "✓"}
                </h2>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                  disabled={isReady}
                >
                  Logout
                </button>
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium">
                  Conversations JSON
                </label>
                <div className="flex gap-2">
                  <input
                    type="file"
                    accept=".json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileUpload(file);
                    }}
                    className="flex-1 text-sm"
                    disabled={isReady}
                  />
                  <button
                    onClick={handleLoadDefault}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-sm disabled:opacity-50"
                    disabled={isReady}
                  >
                    Load Default
                  </button>
                </div>
                {userData.conversations && (
                  <p className="text-xs text-green-600">
                    ✓ Loaded {userData.conversations.length} conversations
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium">Prompt</label>
                <input
                  type="text"
                  value={userData.prompt}
                  onChange={(e) =>
                    setUserData((prev) => ({ ...prev, prompt: e.target.value }))
                  }
                  placeholder="e.g., Does this person like to travel?"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900"
                  disabled={isReady}
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium">
                  Expected Answer
                </label>
                <input
                  type="text"
                  value={userData.expected}
                  onChange={(e) =>
                    setUserData((prev) => ({
                      ...prev,
                      expected: e.target.value,
                    }))
                  }
                  placeholder="e.g., Yes, the person likes to travel"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900"
                  disabled={isReady}
                />
              </div>

              <button
                onClick={handleSubmit}
                disabled={
                  isSubmitting ||
                  isReady ||
                  !userData.conversations ||
                  !userData.prompt ||
                  !userData.expected
                }
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded transition-colors"
              >
                {isSubmitting ? "Submitting..." : "Submit & Ready"}
              </button>
            </>
          )}
        </div>

        {isPolling && (
          <div className="bg-blue-100 dark:bg-blue-900 border border-blue-400 dark:border-blue-700 text-blue-700 dark:text-blue-200 px-4 py-3 rounded text-center">
            ⏳ Evaluation in progress... (this may take 30-60 seconds)
          </div>
        )}

        {roomStatus?.state === "COMPLETED" && result && (
          <div className="bg-green-100 dark:bg-green-900 border-2 border-green-500 rounded-lg p-6 space-y-3">
            <h2 className="text-2xl font-bold text-green-800 dark:text-green-200">
              ✅ Compatibility Results
            </h2>
            <div className="space-y-2 text-lg">
              <p>
                <span className="font-semibold">A→B Compatibility:</span>{" "}
                {result.a_to_b_score}%
              </p>
              <p>
                <span className="font-semibold">B→A Compatibility:</span>{" "}
                {result.b_to_a_score}%
              </p>
              <p className="text-xl font-bold">
                <span className="font-semibold">Average:</span>{" "}
                {average?.toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        <LogConsole logs={logs} />
      </div>
    </div>
  );
}
