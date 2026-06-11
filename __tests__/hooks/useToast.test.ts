
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USETOAST_TEST
// ROLE: Unit tests for useToast.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for useToast.test.ts — __tests__/hooks/useToast.test.ts
// owns:
//   - __tests__/hooks/useToast.test.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import { describe, it, expect } from 'vitest';
import { reducer } from '../../hooks/use-toast';

const mockToast = (id: string, overrides = {}) => ({
  id,
  title: 'Test Toast',
  description: 'Test description',
  open: true,
  onOpenChange: () => {},
  ...overrides,
});

describe('toast reducer', () => {
  it('ADD_TOAST prepends a new toast', () => {
    const toast = mockToast('1');
    const state = reducer({ toasts: [] }, { type: 'ADD_TOAST', toast });
    expect(state.toasts).toHaveLength(1);
    expect(state.toasts[0]).toEqual(toast);
  });

  it('ADD_TOAST respects TOAST_LIMIT of 1, replacing old toast', () => {
    const existing = mockToast('1');
    const newToast = mockToast('2');
    const state = reducer(
      { toasts: [existing] },
      { type: 'ADD_TOAST', toast: newToast }
    );
    expect(state.toasts).toHaveLength(1);
    expect(state.toasts[0].id).toBe('2');
  });

  it('UPDATE_TOAST updates matching toast by id', () => {
    const toast1 = mockToast('1', { title: 'Old Title' });
    const toast2 = mockToast('2', { title: 'Keep Me' });
    const state = reducer(
      { toasts: [toast1, toast2] },
      { type: 'UPDATE_TOAST', toast: { id: '1', title: 'New Title' } }
    );
    expect(state.toasts[0].title).toBe('New Title');
    expect(state.toasts[1].title).toBe('Keep Me');
  });

  it('UPDATE_TOAST does nothing for unmatched id', () => {
    const toast1 = mockToast('1', { title: 'Title' });
    const state = reducer(
      { toasts: [toast1] },
      { type: 'UPDATE_TOAST', toast: { id: 'nonexistent', title: 'Changed' } }
    );
    expect(state.toasts[0].title).toBe('Title');
  });

  it('DISMISS_TOAST sets open=false for matching toast', () => {
    const toast1 = mockToast('1', { open: true });
    const state = reducer(
      { toasts: [toast1] },
      { type: 'DISMISS_TOAST', toastId: '1' }
    );
    expect(state.toasts[0].open).toBe(false);
  });

  it('DISMISS_TOAST with no toastId dismisses all', () => {
    const toast1 = mockToast('1', { open: true });
    const toast2 = mockToast('2', { open: true });
    const state = reducer(
      { toasts: [toast1, toast2] },
      { type: 'DISMISS_TOAST' }
    );
    expect(state.toasts[0].open).toBe(false);
    expect(state.toasts[1].open).toBe(false);
  });

  it('REMOVE_TOAST removes matching toast by id', () => {
    const toast1 = mockToast('1');
    const toast2 = mockToast('2');
    const state = reducer(
      { toasts: [toast1, toast2] },
      { type: 'REMOVE_TOAST', toastId: '1' }
    );
    expect(state.toasts).toHaveLength(1);
    expect(state.toasts[0].id).toBe('2');
  });

  it('REMOVE_TOAST with no toastId removes all toasts', () => {
    const toast1 = mockToast('1');
    const toast2 = mockToast('2');
    const state = reducer(
      { toasts: [toast1, toast2] },
      { type: 'REMOVE_TOAST' }
    );
    expect(state.toasts).toHaveLength(0);
  });

  it('DISMISS_TOAST with unmatched toastId does not affect others', () => {
    const toast1 = mockToast('1', { open: true });
    const state = reducer(
      { toasts: [toast1] },
      { type: 'DISMISS_TOAST', toastId: 'nonexistent' }
    );
    expect(state.toasts[0].open).toBe(true);
  });

  it('REMOVE_TOAST with unmatched toastId keeps all toasts', () => {
    const toast1 = mockToast('1');
    const state = reducer(
      { toasts: [toast1] },
      { type: 'REMOVE_TOAST', toastId: 'nonexistent' }
    );
    expect(state.toasts).toHaveLength(1);
  });
});
