// AI_HEADER
// module: M-TEST-E2E-CHAT
// wave: W-TEST-3
// purpose: Real-API E2E (no route interception): send a chat message and
//   prove the structural assistant reply on the real stack (P1-6 slice).

// START_MODULE_CONTRACT: M-TEST-E2E-CHAT
// purpose: Prove the real chat path: user message stored, assistant reply
//   streamed back through the real thread/messages API.
// owns:
//   - e2e/chat.spec.ts
// inputs: real Telegram HMAC auth via e2e/fixtures.ts (uniqueTelegramUser),
//   real chat API/LLM endpoints.
// outputs: Playwright pass/fail; created users tracked for the acceptance
//   cleanup adapter via E2E_CREATED_USERS_FILE (fixtures default).
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding).
// side_effects: Creates one real user, one chat thread and one real LLM
//   exchange.
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; no conditional early returns or
//     expect(true) passes; assertions are structural (roles/counts/non-empty),
//     never LLM-text-dependent.
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-CHAT

// START_MODULE_MAP: M-TEST-E2E-CHAT
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - CHAT_FLOW: send → user bubble → assistant bubble non-empty
// END_MODULE_MAP: M-TEST-E2E-CHAT

import { test, expect, completeOnboarding } from './fixtures';

test.describe('Chat — Real API (P1-6)', () => {
  test.use({ uniqueTelegramUser: true });

  test('sends a message and receives a structural assistant reply', async ({ page }) => {
    test.setTimeout(120000);

    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    await page.goto('/onboarding');
    await completeOnboarding(page);

    await page.goto('/chat');
    await expect(page.getByTestId('chat-screen')).toHaveAttribute('data-state', 'empty', { timeout: 15000 });

    await page.getByTestId('chat-input').fill('Что сегодня за день по моей карте?');
    await page.getByTestId('chat-send').click();

    // Screen leaves the empty state; both bubbles exist with contract roles.
    await expect(page.getByTestId('chat-screen')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    const userMessage = page.locator('[data-testid="chat-message"][data-role="user"]').first();
    await expect(userMessage).toBeVisible({ timeout: 15000 });
    const assistantMessage = page.locator('[data-testid="chat-message"][data-role="assistant"]').first();
    await expect(assistantMessage).toBeVisible({ timeout: 60000 });

    // Structural proof of a real reply: assistant content becomes non-empty.
    await expect(async () => {
      const text = await assistantMessage.textContent();
      expect((text ?? '').trim().length).toBeGreaterThan(0);
    }).toPass({ timeout: 60000 });
  });
});
