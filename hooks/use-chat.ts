// AI_HEADER
// module: M-HOOK-CHAT
// wave: W-2.4
// purpose: Chat hook

'use client';

import { useReducer, useEffect } from 'react';
import { chatReducer, initialChatState } from '@/lib/reducers/chat-reducer';
import { getChatThreads, sendChatMessage, createChatThread, getChatThread } from '@/lib/api/chat';

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);

  useEffect(() => {
    async function load() {
      dispatch({ type: 'SET_LOADING', loading: true });
      try {
        const threads = await getChatThreads();

        // If no threads exist, create one
        if (threads.length === 0) {
          const newThread = await createChatThread();
          const fullThread = await getChatThread(newThread.id);
          dispatch({ type: 'SET_THREADS', threads: [fullThread] });
          dispatch({ type: 'SET_ACTIVE_THREAD', threadId: fullThread.id });
        } else {
          dispatch({ type: 'SET_THREADS', threads });
          dispatch({ type: 'SET_ACTIVE_THREAD', threadId: threads[0].id });
        }
      } catch (error) {
        dispatch({ type: 'SET_ERROR', error: 'Failed to load threads' });
      } finally {
        dispatch({ type: 'SET_LOADING', loading: false });
      }
    }
    load();
  }, []);

  const sendMessage = async (content: string) => {
    if (!state.activeThreadId) return;

    // Add user message optimistically
    const userMessage = {
      id: `msg-user-${Date.now()}`,
      role: 'user' as const,
      content,
      timestamp: new Date().toISOString(),
    };
    dispatch({ type: 'ADD_MESSAGE', threadId: state.activeThreadId, message: userMessage });

    // Send to API
    dispatch({ type: 'SET_LOADING', loading: true });
    try {
      const response = await sendChatMessage(state.activeThreadId, content);

      // Replace optimistic user message with real one
      dispatch({ type: 'ADD_MESSAGE', threadId: state.activeThreadId, message: {
        id: response.user_message.id,
        role: response.user_message.role,
        content: response.user_message.content,
        timestamp: response.user_message.created_at,
      }});

      // Add assistant message
      dispatch({ type: 'ADD_MESSAGE', threadId: state.activeThreadId, message: {
        id: response.assistant_message.id,
        role: response.assistant_message.role,
        content: response.assistant_message.content,
        timestamp: response.assistant_message.created_at,
      }});
    } catch (error) {
      dispatch({ type: 'SET_ERROR', error: error instanceof Error ? error.message : 'Failed to send message' });
    } finally {
      dispatch({ type: 'SET_LOADING', loading: false });
    }
  };

  const activeThread = state.threads.find(t => t.id === state.activeThreadId);

  return {
    threads: state.threads,
    activeThread,
    loading: state.loading,
    error: state.error,
    sendMessage,
  };
}
