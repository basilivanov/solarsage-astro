// AI_HEADER
// module: M-API-CHAT-FIXTURES
// wave: W-2.4
// purpose: Chat fixtures (until W-CHAT-1 backend is ready)

import { ChatThread, ChatMessage } from '@/lib/contracts/chat';

export const FIXTURE_THREADS: ChatThread[] = [
  {
    id: 'thread-1',
    title: 'Вопрос о карьере',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Когда лучше начать новый проект?',
        timestamp: '2026-05-30T10:00:00Z',
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: 'Судя по вашей карте, следующая неделя будет благоприятной для начинаний. Марс в вашем 10 доме поддерживает карьерные инициативы.',
        timestamp: '2026-05-30T10:00:05Z',
      },
    ],
    createdAt: '2026-05-30T10:00:00Z',
    updatedAt: '2026-05-30T10:00:05Z',
  },
];

export async function sendChatMessage(threadId: string, content: string): Promise<ChatMessage> {
  // Fixture: simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  return {
    id: `msg-${Date.now()}`,
    role: 'assistant',
    content: 'Это тестовый ответ. Реальный backend будет в W-CHAT-1.',
    timestamp: new Date().toISOString(),
  };
}

export async function getChatThreads(): Promise<ChatThread[]> {
  // Fixture: return hardcoded threads
  await new Promise(resolve => setTimeout(resolve, 300));
  return FIXTURE_THREADS;
}
