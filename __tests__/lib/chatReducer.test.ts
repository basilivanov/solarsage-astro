// AI_HEADER
// module: M-TEST-CHAT-REDUCER
// wave: W-2.4
// purpose: Chat reducer tests

import { describe, it, expect } from 'vitest';
import { chatReducer, initialChatState } from '@/lib/reducers/chat-reducer';

describe('chatReducer', () => {
  it('SET_THREADS updates threads', () => {
    const threads = [{ id: 'thread-1', title: 'Test', messages: [], createdAt: '', updatedAt: '' }];
    const state = chatReducer(initialChatState, { type: 'SET_THREADS', threads });
    expect(state.threads).toEqual(threads);
  });

  it('SET_ACTIVE_THREAD updates activeThreadId', () => {
    const state = chatReducer(initialChatState, { type: 'SET_ACTIVE_THREAD', threadId: 'thread-1' });
    expect(state.activeThreadId).toBe('thread-1');
  });

  it('ADD_MESSAGE appends message to thread', () => {
    const initialState = {
      ...initialChatState,
      threads: [{ id: 'thread-1', title: 'Test', messages: [], createdAt: '', updatedAt: '' }],
    };

    const message = { id: 'msg-1', role: 'user' as const, content: 'Hello', timestamp: '' };
    const state = chatReducer(initialState, { type: 'ADD_MESSAGE', threadId: 'thread-1', message });

    expect(state.threads[0].messages).toHaveLength(1);
    expect(state.threads[0].messages[0]).toEqual(message);
  });

  it('SET_LOADING sets loading to true', () => {
    const state = chatReducer(initialChatState, { type: 'SET_LOADING', loading: true });
    expect(state.loading).toBe(true);
  });

  it('SET_LOADING sets loading to false', () => {
    const state = chatReducer({ ...initialChatState, loading: true }, { type: 'SET_LOADING', loading: false });
    expect(state.loading).toBe(false);
  });

  it('SET_ERROR sets error message', () => {
    const state = chatReducer(initialChatState, { type: 'SET_ERROR', error: 'Something went wrong' });
    expect(state.error).toBe('Something went wrong');
  });

  it('SET_ERROR clears error when null', () => {
    const state = chatReducer({ ...initialChatState, error: 'Old error' }, { type: 'SET_ERROR', error: null });
    expect(state.error).toBeNull();
  });

  it('ADD_MESSAGE to non-existent thread does nothing', () => {
    const message = { id: 'msg-1', role: 'user' as const, content: 'Hello', timestamp: '' };
    const state = chatReducer(initialChatState, { type: 'ADD_MESSAGE', threadId: 'nonexistent', message });
    expect(state.threads).toEqual(initialChatState.threads);
  });

  it('default case returns unchanged state for unknown action', () => {
    const state = chatReducer(initialChatState, { type: 'UNKNOWN_ACTION' as any });
    expect(state).toBe(initialChatState);
  });
});
