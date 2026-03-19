import { useEffect, useState } from 'react';
import type { PortfolioSummary, Signal, Market } from '../api';
import { api } from '../api';

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="text-gray-400 text-sm mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getPortfolioSummary().catch(() => null),
      api.getSignals('pending').catch(() => []),
      api.getMarkets().catch(() => []),
    ]).then(([s, sig, m]) => {
      setSummary(s);
      setSignals(sig);
      setMarkets(m);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="text-gray-400 text-center py-20">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Active Markets" value={markets.length} />
        <StatCard label="Pending Signals" value={summary?.pending_signals ?? 0} />
        <StatCard label="Open Positions" value={summary?.open_positions ?? 0} />
        <StatCard
          label="Total PnL"
          value={`$${(summary?.total_pnl ?? 0).toFixed(2)}`}
          sub={`$${(summary?.total_invested ?? 0).toFixed(0)} invested`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Signals */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Recent Signals</h2>
          {signals.length === 0 ? (
            <p className="text-gray-500 text-sm">No pending signals</p>
          ) : (
            <div className="space-y-3">
              {signals.slice(0, 5).map((s) => (
                <div key={s.id} className="flex items-center justify-between border-b border-gray-800 pb-2">
                  <div>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                      s.direction === 'BUY_YES' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                    }`}>
                      {s.direction}
                    </span>
                    <span className="text-sm ml-2 text-gray-300">{s.strategy}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-white">{(s.confidence * 100).toFixed(0)}%</div>
                    <div className="text-xs text-gray-500">${s.suggested_size?.toFixed(1)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* League Distribution */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Markets by League</h2>
          {(() => {
            const leagues: Record<string, number> = {};
            markets.forEach((m) => {
              const l = m.league || 'Other';
              leagues[l] = (leagues[l] || 0) + 1;
            });
            return (
              <div className="space-y-2">
                {Object.entries(leagues)
                  .sort(([, a], [, b]) => b - a)
                  .map(([league, count]) => (
                    <div key={league} className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">{league}</span>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 bg-indigo-600 rounded"
                          style={{ width: `${Math.min(count * 3, 120)}px` }}
                        />
                        <span className="text-xs text-gray-500 w-6 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
