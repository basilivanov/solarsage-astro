// AI_HEADER
// module: M-CONTRACTS-CHAT
// wave: W-2.4
// purpose: Chat contracts (frontend-only for now)

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatThread {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}
