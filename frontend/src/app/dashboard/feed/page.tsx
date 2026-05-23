'use client';

import React, { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { apiClient } from '@/lib/apiClient';
import { 
  Activity, 
  Wifi, 
  WifiOff, 
  MessageSquareCode, 
  ArrowUpRight 
} from 'lucide-react';

interface FeedMessage {
  type: string;
  timestamp: string;
  payload: {
    id: string;
    title: string;
    url: string;
    source: string;
    content: string | null;
    summary: string | null;
    sentiment: string | null;
    sentiment_score: number | null;
    published_at: string;
  };
}

export default function LiveFeedPage() {
  const [liveArticles, setLiveArticles] = useState<any[]>([]);
  const { isConnected, messages } = useWebSocket<any>();

  // Fetch initial articles to pre-populate feed
  useEffect(() => {
    apiClient.get('/news', { params: { limit: 15 } })
      .then((res) => {
        setLiveArticles(res.data);
      })
      .catch((err) => {
        console.error('Failed to load initial feed:', err);
      });
  }, []);

  // Sync new WS messages into page state
  useEffect(() => {
    if (messages.length > 0) {
      const latestMsg = messages[0];
      if (latestMsg.type === 'NEW_ARTICLE' && latestMsg.payload) {
        setLiveArticles((prev) => {
          // Prevent duplicates
          if (prev.some(a => a.id === latestMsg.payload.id)) {
            return prev;
          }
          return [latestMsg.payload, ...prev];
        });
      }
    }
  }, [messages]);

  return (
    <div className="space-y-6">
      {/* Header section with WebSocket connectivity status indicator */}
      <div className="flex justify-between items-center border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-2">
            Live Stream Feed
            <span className="relative flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isConnected ? 'bg-green-400' : 'bg-red-400'
              }`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></span>
            </span>
          </h1>
          <p className="text-zinc-400 mt-1">Real-time incoming intelligence logs processed by LLM agents.</p>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border ${
          isConnected 
            ? 'bg-green-500/10 text-green-400 border-green-500/20' 
            : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
          {isConnected ? (
            <>
              <Wifi className="h-3.5 w-3.5" />
              Connected
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5" />
              Disconnected
            </>
          )}
        </div>
      </div>

      {/* Grid of feed cards */}
      <div className="space-y-4">
        {liveArticles.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center text-zinc-500">
            Awaiting news article feeds. Run sync on the Dashboard to fetch articles.
          </div>
        ) : (
          liveArticles.map((article, i) => (
            <div 
              key={article.id || i} 
              className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-all rounded-xl p-6 flex flex-col md:flex-row md:items-start justify-between gap-4"
            >
              <div className="space-y-3 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 bg-zinc-800 text-zinc-300 font-semibold rounded">
                    {article.source}
                  </span>
                  <span className="text-zinc-500">
                    {new Date(article.published_at).toLocaleTimeString()}
                  </span>
                  {article.sentiment && (
                    <span className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                      article.sentiment === 'POSITIVE' ? 'bg-green-500/15 text-green-400' :
                      article.sentiment === 'NEGATIVE' ? 'bg-red-500/15 text-red-400' :
                      'bg-zinc-800 text-zinc-400'
                    }`}>
                      {article.sentiment} ({article.sentiment_score?.toFixed(2) || '0.00'})
                    </span>
                  )}
                </div>

                <h3 className="text-lg font-bold text-white flex items-center gap-1">
                  {article.title}
                </h3>

                {article.summary ? (
                  <p className="text-sm text-zinc-400 leading-relaxed bg-zinc-950/40 p-3 rounded-lg border border-zinc-850">
                    <strong className="text-zinc-300 block text-xs uppercase tracking-wider mb-1">AI Summary</strong>
                    {article.summary}
                  </p>
                ) : (
                  <p className="text-sm text-zinc-500 italic">Analysis processing in background...</p>
                )}
              </div>

              <div className="flex self-end md:self-start">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 bg-zinc-800 hover:bg-zinc-750 text-zinc-400 hover:text-white rounded-lg transition-colors flex items-center gap-1.5 text-xs font-semibold"
                >
                  Source Feed
                  <ArrowUpRight className="h-4 w-4" />
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
