'use client';

import React, { useState } from 'react';
import { 
  Send, 
  Bot, 
  User as UserIcon, 
  ExternalLink,
  BookOpen,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface Message {
  sender: 'user' | 'assistant';
  text: string;
  sources?: any[];
}

export default function RAGChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: "Hello! I am your NeuralPulse AI News Assistant. Ask me anything about the ingested news articles (e.g., 'What is happening with tech stocks?' or 'Are there any recent cybersecurity exploits?'). I will search the vector archive and answer with citations."
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input;
    setInput('');
    setError(null);
    setIsLoading(true);

    // Prepend user message
    setMessages((prev) => [...prev, { sender: 'user', text: userText }]);

    try {
      // Build simple history mapping
      const history = messages
        .filter((m) => m.text !== '')
        .map((m) => ({
          role: m.sender === 'user' ? 'user' : 'assistant',
          content: m.text
        }));

      const response = await apiClient.post('/news/chat', {
        question: userText,
        chat_history: history
      });

      setMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: response.data.answer,
          sources: response.data.sources
        }
      ]);
    } catch (err: any) {
      console.error(err);
      setError('Failed to generate answer. Please verify backend or API credentials.');
      setMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: "I encountered an error trying to process your request. Check connection variables."
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] max-w-4xl mx-auto space-y-4">
      {/* Header bar */}
      <div className="border-b border-zinc-800 pb-3 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-2">
            AI Chat Assistant
            <Sparkles className="h-5 w-5 text-blue-500" />
          </h1>
          <p className="text-zinc-400 mt-1">Retrieval-Augmented Chat (RAG) over ingested news archives.</p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto bg-zinc-900/40 border border-zinc-800 rounded-xl p-6 space-y-6 scrollbar-thin">
        {messages.map((msg, index) => (
          <div 
            key={index}
            className={`flex gap-4 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender === 'assistant' && (
              <div className="h-8 w-8 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-500 shrink-0">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div className="space-y-3 max-w-[85%]">
              <div 
                className={`rounded-xl p-4 text-sm leading-relaxed ${
                  msg.sender === 'user' 
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/10' 
                    : 'bg-zinc-900 border border-zinc-800 text-zinc-200'
                }`}
              >
                {msg.text}
              </div>

              {/* Render citations if available */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="pl-2 border-l border-zinc-800 space-y-2">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-500 flex items-center gap-1">
                    <BookOpen className="h-3 w-3" /> Reference Citations:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {msg.sources.map((source, sIdx) => (
                      <div 
                        key={source.id || sIdx}
                        className="bg-zinc-900/60 border border-zinc-850 p-2.5 rounded-lg text-xs hover:border-zinc-700 transition-colors flex justify-between items-start"
                      >
                        <div className="truncate pr-2">
                          <span className="font-bold text-blue-400 mr-1">[{sIdx + 1}]</span>
                          <span className="font-semibold text-zinc-300 truncate">{source.title}</span>
                          <span className="block text-[10px] text-zinc-500 mt-0.5">{source.source}</span>
                        </div>
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white shrink-0"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.sender === 'user' && (
              <div className="h-8 w-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300 shrink-0">
                <UserIcon className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-4 justify-start">
            <div className="h-8 w-8 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-500 shrink-0 animate-pulse">
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-2 text-sm text-zinc-400">
              <div className="flex gap-1">
                <span className="h-2 w-2 bg-zinc-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-2 w-2 bg-zinc-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-2 w-2 bg-zinc-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span>Searching vector database and generating answer...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input console */}
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask AI about news articles..."
          disabled={isLoading}
          className="flex-1 bg-zinc-900 border border-zinc-850 focus:border-zinc-750 px-4 py-3 rounded-xl text-sm focus:outline-none text-zinc-200 placeholder-zinc-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white p-3 rounded-xl transition-all flex items-center justify-center shadow-lg shadow-blue-600/20"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
