import { useEffect, useRef } from 'react';
import type { StatusUpdate } from '../types/agent';

interface UseWebSocketOptions {
  onMessage?: (data: StatusUpdate) => void;
  onError?: () => void;
}

export function useWebSocket(
  jobId: string | null,
  options: UseWebSocketOptions = {}
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;
  const jobIdRef = useRef(jobId);

  // Keep refs updated
  const onMessageRef = useRef(options.onMessage);
  const onErrorRef = useRef(options.onError);

  useEffect(() => {
    onMessageRef.current = options.onMessage;
    onErrorRef.current = options.onError;
  }, [options.onMessage, options.onError]);

  useEffect(() => {
    jobIdRef.current = jobId;

    // Cleanup previous connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (!jobId) {
      reconnectAttemptsRef.current = 0;
      return;
    }

    let reconnectTimeout: number | undefined;
    let isMounted = true;

    const connect = () => {
      if (!isMounted || !jobIdRef.current) return;

      // Use the vite proxy - connect to same host
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/${jobIdRef.current}`;

      console.log(`Connecting WebSocket: ${wsUrl}`);

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`WebSocket connected for job ${jobIdRef.current}`);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as StatusUpdate;
          onMessageRef.current?.(data);

          // If job completed or errored, don't reconnect
          if (data.status === 'complete' || data.status === 'error') {
            reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnection
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = (event) => {
        console.log(`WebSocket closed: code=${event.code}, reason=${event.reason}`);

        // Only reconnect if:
        // - Still mounted
        // - Job still active
        // - Haven't exceeded max attempts
        // - Not a clean close (1000) or going away (1001)
        if (
          isMounted &&
          jobIdRef.current &&
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          event.code !== 1000 &&
          event.code !== 1001
        ) {
          reconnectAttemptsRef.current++;
          console.log(`Reconnect attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}...`);
          reconnectTimeout = window.setTimeout(connect, 2000);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts && event.code !== 1000) {
          // Only show error if we exhausted reconnect attempts on a non-clean close
          console.error('WebSocket connection failed after max attempts');
          onErrorRef.current?.();
        }
      };

      wsRef.current = ws;
    };

    // Small delay to ensure backend has registered the job
    const initialTimeout = window.setTimeout(connect, 100);

    return () => {
      isMounted = false;
      clearTimeout(initialTimeout);
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [jobId]);
}
