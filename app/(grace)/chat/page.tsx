// AI_HEADER
// module: M-WEB-CHAT-PAGE
// wave: W-2.4
// purpose: Chat screen

'use client';

import { useState } from 'react';
import { useChat } from '@/hooks/use-chat';

export default function ChatPage() {
  const { activeThread, loading, sendMessage } = useChat();
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  if (loading && !activeThread) {
    return <div className="p-4">Загрузка...</div>;
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b p-4">
        <h1 className="text-xl font-bold">Чат с астрологом</h1>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeThread?.messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-900'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="bg-white border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSend()}
            placeholder="Задайте вопрос..."
            className="flex-1 border rounded-lg px-4 py-2"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            Отправить
          </button>
        </div>
      </div>
    </div>
  );
}
