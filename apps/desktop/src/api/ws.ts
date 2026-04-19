import type {
  ClientTextEvent,
  ServerEvent,
} from "@eatit/shared-types";
import { API_BASE_URL } from "@/api/client";

type EventHandler<TEvent extends ServerEvent = ServerEvent> = (event: TEvent) => void;

type SubscriptionMap = {
  [K in ServerEvent["event"]]?: Set<EventHandler<Extract<ServerEvent, { event: K }>>>;
};

const toWebSocketBaseUrl = (baseUrl: string): string => {
  if (baseUrl.startsWith("https://")) {
    return baseUrl.replace("https://", "wss://");
  }
  return baseUrl.replace("http://", "ws://");
};

export class InterviewSocketClient {
  private readonly sessionId: string;
  private readonly token: string;
  private readonly baseUrl: string;
  private readonly subscriptions: SubscriptionMap = {};
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private manuallyClosed = false;

  constructor(sessionId: string, token = "mock-token", baseUrl = API_BASE_URL) {
    this.sessionId = sessionId;
    this.token = token;
    this.baseUrl = toWebSocketBaseUrl(baseUrl);
  }

  connect(): void {
    this.manuallyClosed = false;
    this.socket = new WebSocket(
      `${this.baseUrl}/ws/sessions/${this.sessionId}?token=${encodeURIComponent(this.token)}`,
    );

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (message) => {
      const parsed = JSON.parse(message.data) as ServerEvent;
      this.emit(parsed);
    };

    this.socket.onclose = () => {
      this.socket = null;
      if (!this.manuallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  subscribe<TEventName extends ServerEvent["event"]>(
    eventName: TEventName,
    handler: EventHandler<Extract<ServerEvent, { event: TEventName }>>,
  ): () => void {
    const handlers = this.subscriptions[eventName] ?? new Set();
    handlers.add(handler as EventHandler);
    this.subscriptions[eventName] = handlers as SubscriptionMap[TEventName];

    return () => {
      handlers.delete(handler as EventHandler);
      if (handlers.size === 0) {
        delete this.subscriptions[eventName];
      }
    };
  }

  send(event: ClientTextEvent): void {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not open.");
    }
    this.socket.send(JSON.stringify(event));
  }

  sendAudioChunk(chunk: Blob | ArrayBuffer): void {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not open.");
    }
    this.socket.send(chunk);
  }

  close(): void {
    this.manuallyClosed = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  private emit(event: ServerEvent): void {
    const handlers = this.subscriptions[event.event];
    handlers?.forEach((handler) => {
      handler(event as never);
    });
  }

  private scheduleReconnect(): void {
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 5000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }
}

export const createInterviewSocket = (
  sessionId: string,
  token = "mock-token",
): InterviewSocketClient => {
  const client = new InterviewSocketClient(sessionId, token);
  client.connect();
  return client;
};
