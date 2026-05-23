'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { 
  TrendingUp, 
  RefreshCw, 
  Search,
  ShieldCheck,
  Zap,
  Sparkles,
  Database
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface Article {
  id: string;
  title: string;
  url: string;
  source: string;
  sentiment: string | null;
  sentiment_score: number | null;
  credibility_score: number | null;
  key_entities: string | null;
  published_at: string;
}

interface AnalyticsStats {
  total_articles: number;
  positivity_ratio: number;
  sentiment_breakdown: Record<string, number>;
  sources_breakdown: Record<string, number>;
  timeline_data: Array<{ date: string; count: number }>;
}


export default function DashboardPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'standard' | 'semantic'>('standard');
  const [isSyncing, setIsSyncing] = useState(false);
  
  // Analytics State
  const [stats, setStats] = useState<AnalyticsStats | null>(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      let articlesRes;
      if (searchMode === 'semantic' && searchQuery.trim() !== '') {
        articlesRes = await apiClient.get<Article[]>('/news/search/semantic', {
          params: { query: searchQuery, limit: 10 }
        });
      } else {
        articlesRes = await apiClient.get<Article[]>('/news', {
          params: { limit: 10, search: searchQuery || undefined }
        });
      }
      setArticles(articlesRes.data);

      // Fetch stats
      const statsRes = await apiClient.get<AnalyticsStats>('/news/analytics/stats');
      setStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  }, [searchQuery, searchMode]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const triggerSync = async () => {
    setIsSyncing(true);
    try {
      await apiClient.post('/news/sync');
      setTimeout(async () => {
        await fetchDashboardData();
        setIsSyncing(false);
      }, 4000);
    } catch (err) {
      console.error('Sync failed:', err);
      setIsSyncing(false);
    }
  };

  const getPositivityPercentage = () => {
    if (!stats || stats.total_articles === 0) return 50;
    return Math.round(stats.positivity_ratio * 100);
  };

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Intelligence Dashboard</h1>
          <p className="text-zinc-400 mt-1">Monitor real-time news streams and Multi-Agent analytical reports.</p>
        </div>
        <button
          onClick={triggerSync}
          disabled={isSyncing}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-lg shadow-blue-600/30"
        >
          <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
          {isSyncing ? 'Synchronizing Feeds...' : 'Sync Raw Feeds'}
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-zinc-400">Total Analyzed Articles</span>
            <h3 className="text-3xl font-bold mt-1">{stats ? stats.total_articles : 0}</h3>
          </div>
          <div className="h-10 w-10 bg-blue-500/10 rounded-lg flex items-center justify-center text-blue-500">
            <Zap className="h-5 w-5" />
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-zinc-400">Positivity Index</span>
            <h3 className="text-3xl font-bold mt-1">{getPositivityPercentage()}%</h3>
          </div>
          <div className="h-10 w-10 bg-green-500/10 rounded-lg flex items-center justify-center text-green-500">
            <TrendingUp className="h-5 w-5" />
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex items-center justify-between sm:col-span-2 lg:col-span-1">
          <div>
            <span className="text-sm font-medium text-zinc-400">Vector Collection Status</span>
            <h3 className="text-xl font-bold text-green-400 mt-2 flex items-center gap-1.5">
              <ShieldCheck className="h-5 w-5" /> Operational
            </h3>
          </div>
          <div className="text-xs text-zinc-500 text-right">
            <div>ChromaDB: Indexed</div>
            <div className="mt-0.5">Agents: Multi-Orchestrator</div>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline Chart */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold">Chronological News Stream Counts</h2>
            <span className="text-xs text-zinc-500">Aggregated Timeline</span>
          </div>
          
          <div className="h-48 w-full flex items-end justify-between gap-3 pt-4">
            {stats && stats.timeline_data && stats.timeline_data.length > 0 ? (
              stats.timeline_data.map((item, i) => {
                const maxCount = Math.max(...stats.timeline_data.map(d => d.count), 1);
                const heightPercentage = (item.count / maxCount) * 100;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-2">
                    <div 
                      className="w-full bg-gradient-to-t from-blue-600 to-indigo-500 rounded-t-md transition-all duration-300 hover:brightness-125 relative group"
                      style={{ height: `${heightPercentage}%` }}
                    >
                      {/* Tooltip */}
                      <span className="absolute -top-8 left-1/2 -translate-x-1/2 scale-0 group-hover:scale-100 transition-all bg-zinc-800 text-[10px] text-zinc-200 px-2 py-0.5 rounded border border-zinc-700 whitespace-nowrap z-10 shadow-lg">
                        {item.count} articles
                      </span>
                    </div>
                    <span className="text-[10px] text-zinc-500 truncate max-w-[50px]">{item.date.slice(5)}</span>
                  </div>
                );
              })
            ) : (
              <div className="w-full h-full flex items-center justify-center text-zinc-600 text-sm">
                Awaiting timeline records. Run sync raw feeds to populate index.
              </div>
            )}
          </div>
        </div>

        {/* Sources Breakdown list */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h2 className="text-lg font-bold mb-4">Ingestion Source Ratios</h2>
          <div className="space-y-3">
            {stats && stats.sources_breakdown && Object.keys(stats.sources_breakdown).length > 0 ? (
              Object.entries(stats.sources_breakdown).map(([source, count]) => {
                const percentage = Math.round((count / (stats.total_articles || 1)) * 100);
                return (
                  <div key={source} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-medium text-zinc-400">
                      <span>{source}</span>
                      <span>{count} articles ({percentage}%)</span>
                    </div>
                    <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${percentage}%` }} />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-sm text-zinc-500 text-center py-8">
                No sources ingested yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Article List Section */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-zinc-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <h2 className="text-lg font-bold">Recent Intelligence Records</h2>
          
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Search mode toggler */}
            <div className="flex bg-zinc-950 p-1 rounded-lg border border-zinc-850">
              <button
                type="button"
                onClick={() => setSearchMode('standard')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  searchMode === 'standard'
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <Database className="h-3 w-3" />
                Standard SQL
              </button>
              <button
                type="button"
                onClick={() => setSearchMode('semantic')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  searchMode === 'semantic'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/10'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <Sparkles className="h-3 w-3" />
                AI Semantic
              </button>
            </div>

            {/* Search bar */}
            <div className="relative flex-1 md:w-72">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
              <input
                type="text"
                placeholder={searchMode === 'semantic' ? "Ask a semantic topic..." : "Search title or source..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 bg-zinc-950 border border-zinc-850 rounded-lg text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/50 text-xs font-semibold text-zinc-400">
                <th className="p-4">Title</th>
                <th className="p-4">Source</th>
                <th className="p-4">Sentiment</th>
                <th className="p-4">Credibility</th>
                <th className="p-4">Key Entities</th>
                <th className="p-4">Published At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-sm text-zinc-300">
              {articles.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-zinc-500">
                    No articles found. Try syncing raw feeds or adjusting search criteria.
                  </td>
                </tr>
              ) : (
                articles.map((article) => (
                  <tr key={article.id} className="hover:bg-zinc-850 transition-colors">
                    <td className="p-4 font-medium max-w-sm truncate text-white">
                      <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                        {article.title}
                      </a>
                    </td>
                    <td className="p-4">{article.source}</td>
                    <td className="p-4">
                      {article.sentiment ? (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                          article.sentiment === 'POSITIVE' ? 'bg-green-500/10 text-green-400' :
                          article.sentiment === 'NEGATIVE' ? 'bg-red-500/10 text-red-400' :
                          'bg-zinc-500/10 text-zinc-400'
                        }`}>
                          {article.sentiment}
                        </span>
                      ) : (
                        <span className="text-zinc-500 italic">Processing...</span>
                      )}
                    </td>
                    <td className="p-4">
                      {article.credibility_score !== null ? (
                        <span className={`font-semibold text-xs ${
                          article.credibility_score >= 0.9 ? 'text-green-400' :
                          article.credibility_score >= 0.7 ? 'text-zinc-300' :
                          'text-yellow-500'
                        }`}>
                          {Math.round(article.credibility_score * 100)}%
                        </span>
                      ) : (
                        <span className="text-zinc-500">-</span>
                      )}
                    </td>
                    <td className="p-4 max-w-[150px] truncate text-xs text-zinc-400">
                      {article.key_entities || <span className="text-zinc-600">-</span>}
                    </td>
                    <td className="p-4 text-xs text-zinc-500">
                      {new Date(article.published_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
