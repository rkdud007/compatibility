"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";

export default function Home() {
  const router = useRouter();
  const [coordinatorHealthy, setCoordinatorHealthy] = useState<
    boolean | null
  >(null);
  const [enclaveHealthy, setEnclaveHealthy] = useState<boolean | null>(null);
  const [roomIdInput, setRoomIdInput] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    checkHealth();
  }, []);

  async function checkHealth() {
    try {
      await apiClient.checkCoordinatorHealth();
      setCoordinatorHealthy(true);
    } catch {
      setCoordinatorHealthy(false);
    }

    try {
      await apiClient.checkEnclaveHealth();
      setEnclaveHealthy(true);
    } catch {
      setEnclaveHealthy(false);
    }
  }

  async function handleCreateRoom() {
    setIsCreating(true);
    try {
      const { room_id } = await apiClient.createRoom();
      router.push(`/room/${room_id}`);
    } catch (error) {
      alert(`Failed to create room: ${error}`);
    } finally {
      setIsCreating(false);
    }
  }

  function handleJoinRoom() {
    if (!roomIdInput.trim()) {
      alert("Please enter a room ID");
      return;
    }
    router.push(`/room/${roomIdInput.trim()}`);
  }

  const HealthBadge = ({
    name,
    healthy,
  }: {
    name: string;
    healthy: boolean | null;
  }) => (
    <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
      <div
        className={`w-3 h-3 rounded-full ${
          healthy === null
            ? "bg-gray-400 animate-pulse"
            : healthy
            ? "bg-green-500"
            : "bg-red-500"
        }`}
      />
      <span className="text-sm font-mono">
        {name}:{" "}
        {healthy === null ? "checking..." : healthy ? "healthy" : "offline"}
      </span>
    </div>
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black px-4">
      <main className="w-full max-w-2xl space-y-8 py-16">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">
            Compatibility Check
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400">
            Evaluate compatibility between two conversation histories using
            secure enclave processing
          </p>
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Service Status</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <HealthBadge
              name="Coordinator"
              healthy={coordinatorHealthy}
            />
            <HealthBadge name="Enclave" healthy={enclaveHealthy} />
          </div>
        </div>

        <div className="space-y-6 pt-8">
          <button
            onClick={handleCreateRoom}
            disabled={isCreating || !coordinatorHealthy || !enclaveHealthy}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-lg transition-colors text-lg"
          >
            {isCreating ? "Creating Room..." : "Create New Room"}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-zinc-50 dark:bg-black text-gray-500">
                OR
              </span>
            </div>
          </div>

          <div className="space-y-3">
            <label
              htmlFor="room-id"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Join Existing Room
            </label>
            <div className="flex gap-3">
              <input
                id="room-id"
                type="text"
                value={roomIdInput}
                onChange={(e) => setRoomIdInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleJoinRoom()}
                placeholder="Enter room ID"
                className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-900"
              />
              <button
                onClick={handleJoinRoom}
                disabled={!roomIdInput.trim()}
                className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors"
              >
                Join
              </button>
            </div>
          </div>
        </div>

        <div className="pt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Make sure both coordinator and enclave services are running before
            proceeding.
          </p>
        </div>
      </main>
    </div>
  );
}
