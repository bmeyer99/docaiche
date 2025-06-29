/**
 * WebSocket Manager - Singleton pattern to handle WebSocket connections
 * This ensures only one WebSocket connection exists regardless of React re-renders
 */

type WebSocketEventHandler = (data: any) => void;
type ConnectionEventHandler = (event: Event) => void;
type ErrorEventHandler = (event: Event) => void;

interface WebSocketManagerOptions {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
}

class WebSocketManager {
  private static instances: Map<string, WebSocketManager> = new Map();
  private ws: WebSocket | null = null;
  private url: string;
  private options: WebSocketManagerOptions;
  private messageHandlers: Set<WebSocketEventHandler> = new Set();
  private connectionHandlers: Set<ConnectionEventHandler> = new Set();
  private errorHandlers: Set<ErrorEventHandler> = new Set();
  private reconnectCount = 0;
  private reconnectTimeoutId: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private shouldReconnect = true;

  private constructor(options: WebSocketManagerOptions) {
    this.url = options.url;
    this.options = options;
  }

  static getInstance(url: string, options?: Partial<WebSocketManagerOptions>): WebSocketManager {
    let instance = this.instances.get(url);
    
    if (!instance) {
      instance = new WebSocketManager({
        url,
        reconnect: true,
        reconnectInterval: 3000,
        reconnectAttempts: 5,
        ...options
      });
      this.instances.set(url, instance);
    }
    
    return instance;
  }

  connect(): void {
    // Prevent multiple simultaneous connection attempts
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;
    this.shouldReconnect = this.options.reconnect ?? true;

    try {
      console.log('[WebSocketManager] Creating connection to:', this.url);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = (event) => {
        console.log('[WebSocketManager] Connected');
        this.isConnecting = false;
        this.reconnectCount = 0;
        this.connectionHandlers.forEach(handler => handler(event));
      };

      this.ws.onclose = (event) => {
        console.log('[WebSocketManager] Disconnected:', event.code, event.reason);
        this.isConnecting = false;
        this.ws = null;

        // Clear any existing reconnect timeout
        if (this.reconnectTimeoutId) {
          clearTimeout(this.reconnectTimeoutId);
          this.reconnectTimeoutId = null;
        }

        // Attempt reconnection if enabled and not a normal closure
        if (
          this.shouldReconnect &&
          this.options.reconnect &&
          this.reconnectCount < (this.options.reconnectAttempts ?? 5) &&
          event.code !== 1000
        ) {
          const delay = Math.min(
            (this.options.reconnectInterval ?? 3000) * Math.pow(1.5, this.reconnectCount),
            30000
          );
          
          console.log(`[WebSocketManager] Reconnecting in ${delay}ms (attempt ${this.reconnectCount + 1})`);
          
          this.reconnectTimeoutId = setTimeout(() => {
            this.reconnectCount++;
            this.connect();
          }, delay);
        }
      };

      this.ws.onerror = (event) => {
        console.error('[WebSocketManager] Error:', event);
        this.isConnecting = false;
        this.errorHandlers.forEach(handler => handler(event));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.messageHandlers.forEach(handler => handler(data));
        } catch (error) {
          console.error('[WebSocketManager] Failed to parse message:', error);
        }
      };
    } catch (error) {
      console.error('[WebSocketManager] Failed to create WebSocket:', error);
      this.isConnecting = false;
    }
  }

  disconnect(): void {
    console.log('[WebSocketManager] Disconnecting');
    this.shouldReconnect = false;
    
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
  }

  send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof message === 'string' ? message : JSON.stringify(message));
    } else {
      console.warn('[WebSocketManager] Cannot send message - not connected');
    }
  }

  onMessage(handler: WebSocketEventHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnect(handler: ConnectionEventHandler): () => void {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }

  onError(handler: ErrorEventHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  static cleanup(): void {
    this.instances.forEach(instance => instance.disconnect());
    this.instances.clear();
  }
}

export default WebSocketManager;