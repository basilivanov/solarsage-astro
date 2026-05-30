// AI_HEADER
// module: M-API-CHAT-CLIENT
// wave: W-2.4
// purpose: Production API client for chat (replaces fixtures)

import type { ChatThread, ChatMessage } from '@/lib/contracts/chat';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Create a new chat thread
 * @returns Thread ID and creation timestamp
 */
export async function createChatThread(): Promise<{ id: string; created_at: string }> {
  const res = await fetch(`${API_BASE}/api/chat/threads`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!res.ok) {
    throw new Error('Failed to create thread');
  }

  return res.json();
}

/**
 * Get chat thread with all messages
 * @param threadId - Thread UUID
 * @returns Thread with messages
 */
export async function getChatThread(threadId: string): Promise<ChatThread> {
  const res = await fetch(`${API_BASE}/api/chat/threads/${threadId}`, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error('Thread not found');
    }
    throw new Error('Failed to fetch thread');
  }

  return res.json();
}

/**
 * Send message to chat thread
 * @param threadId - Thread UUID
 * @param content - Message content
 * @returns User message and assistant response
 */
export async function sendChatMessage(
  threadId: string,
  content: string
): Promise<{ user_message: ChatMessage; assistant_message: ChatMessage }> {
  const res = await fetch(`${API_BASE}/api/chat/threads/${threadId}/messages`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) {
    if (res.status === 400) {
      const error = await res.json();
      throw new Error(error.detail || 'Chat quota exceeded');
    }
    throw new Error('Failed to send message');
  }

  return res.json();
}

/**
 * Get all chat threads for current user
 * Note: Backend doesn't have list endpoint yet, so we'll need to track threads client-side
 * or implement backend endpoint later
 */
export async function getChatThreads(): Promise<ChatThread[]> {
  // TODO: Implement when backend has GET /api/chat/threads endpoint
  // For now, return empty array - threads will be created on demand
  return [];
}
