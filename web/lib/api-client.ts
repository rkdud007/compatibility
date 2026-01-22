// Typed API client for compatibility backend services.

const COORDINATOR_URL = process.env.NEXT_PUBLIC_COORDINATOR_URL || "http://localhost:8000";
const ENCLAVE_URL = process.env.NEXT_PUBLIC_ENCLAVE_URL || "http://localhost:8001";

// Types
export interface Conversation {
  title: string;
  create_time: number;
  update_time: number;
  mapping: Record<string, unknown>;
  [key: string]: unknown;
}

export interface UploadRequest {
  username: string;
  password: string;
  conversations: Conversation[];
  prompt: string;
  expected: string;
}

export interface RoomCreateResponse {
  room_id: string;
}

export interface RoomStatusResponse {
  state: string;
  user_a_ready: boolean;
  user_b_ready: boolean;
  user_a_username: string | null;
  user_b_username: string | null;
  result?: {
    a_to_b_score: number;
    b_to_a_score: number;
  };
}

export interface ReadyRequest {
  username: string;
  password: string;
}

export interface HealthResponse {
  status: string;
}

// API client
export class ApiClient {
  private async request<T>(
    url: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorPayload;
      try {
        errorPayload = JSON.parse(errorText);
      } catch {
        errorPayload = errorText;
      }
      throw new Error(
        JSON.stringify({
          status: response.status,
          statusText: response.statusText,
          error: errorPayload,
        })
      );
    }

    return response.json();
  }

  // Coordinator service endpoints
  async checkCoordinatorHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>(`${COORDINATOR_URL}/room/health`);
  }

  async createRoom(): Promise<RoomCreateResponse> {
    return this.request<RoomCreateResponse>(`${COORDINATOR_URL}/room/create`, {
      method: "POST",
    });
  }

  async uploadData(roomId: string, data: UploadRequest): Promise<void> {
    await this.request<void>(`${COORDINATOR_URL}/room/${roomId}/upload`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getRoomStatus(roomId: string): Promise<RoomStatusResponse> {
    return this.request<RoomStatusResponse>(
      `${COORDINATOR_URL}/room/${roomId}/status`
    );
  }

  async markReady(roomId: string, data: ReadyRequest): Promise<void> {
    await this.request<void>(`${COORDINATOR_URL}/room/${roomId}/ready`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Enclave service endpoints
  async checkEnclaveHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>(`${ENCLAVE_URL}/health`);
  }
}

export const apiClient = new ApiClient();
