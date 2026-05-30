// AI_HEADER
// module: M-CHAT-REDUCER
// wave: W-2.4
// purpose: Chat state reducer

import { ChatMessage, ChatThread } from '@/lib/contracts/chat';

export interface ChatState {
  threads: ChatThread[];
  activeThreadId: string | null;
  loading: boolean;
  error: string | null;
}

export type ChatAction =
  | { type: 'SET_THREADS'; threads: ChatThread[] }
  | { type: 'SET_ACTIVE_THREAD'; threadId: string }
  | { type: 'ADD_MESSAGE'; threadId: string; message: ChatMessage }
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_ERROR'; error: string | null };

export const initialChatState: ChatState = {
  threads: [],
  activeThreadId: null,
  loading: false,
  error: null,
};

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_THREADS':
      return { ...state, threads: action.threads };

    case 'SET_ACTIVE_THREAD':
      return { ...state, activeThreadId: action.threadId };

    case 'ADD_MESSAGE': {
      const threads = state.threads.map(thread =>
        thread.id === action.threadId
          ? { ...thread, messages: [...thread.messages, action.message] }
          : thread
      );
      return { ...state, threads };
    }

    case 'SET_LOADING':
      return { ...state, loading: action.loading };

    case 'SET_ERROR':
      return { ...state, error: action.error };

    default:
      return state;
  }
}
