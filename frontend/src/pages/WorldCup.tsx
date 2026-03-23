import { useEffect, useState } from 'react';
import type { MultiOutcomeEvent, Outcome } from '../api';
import { api } from '../api';

function fmt$(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function ProbBar({ pct, maxPct }: { pct: number; maxPct: number }) {
  const width = maxPct > 0 ? (pct / maxPct) * 100 : 0;
  return (
    <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
      <div
        className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-indigo-400 transition-all"
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  const colors = rank === 1
    ? 'bg-yellow-600 text-yellow-100'
    : rank === 2
    ? 'bg-gray-400 text-gray-900'
    : rank === 3
    ? 'bg-amber-700 text-amber-100'
    : 'bg-gray-800 text-gray-400';
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${colors}`}>
      {rank}
    </span>
  );
}

export default function WorldCup() {
  const [winner, setWinner] = useState<MultiOutcomeEvent | null>(null);
  const [qualifiers, setQualifiers] = useState<Outcome[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'winner' | 'qualifiers'>('winner');

  useEffect(() => {
    Promise.all([
      api.getWCWinner().catch(() => null),
      api.getWCQualifiers().catch(() => []),
    ]).then(([w, q]) => {
      setWinner(w);
      setQualifiers(q);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="text-gray-400 text-center py-20">Loading World Cup data...</div>;
  }

  const maxYes = winner?.outcomes?.[0]?.yes_price ?? 0.15;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">2026 FIFA World Cup</h1>
          <p className="text-gray-400 text-sm mt-1">
            June 11 - July 19 | USA, Canada, Mexico | 48 Teams
          </p>
        </div>
        {winner && (
          <div className="flex gap-4 text-right">
            <div>
              <div className="text-xs text-gray-500">Total Volume</div>
              <div className="text-lg font-bold text-white">{fmt$(winner.total_volume)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Total Liquidity</div>
              <div className="text-lg font-bold text-white">{fmt$(winner.total_liquidity)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1">
        {(['winner', 'qualifiers'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {t === 'winner' ? `Winner (${winner?.outcomes?.length ?? 0} teams)` : `Qualifiers (${qualifiers.length})`}
          </button>
        ))}
      </div>

      {/* Winner Tab */}
      {tab === 'winner' && (
        <>
          {!winner || winner.outcomes.length === 0 ? (
            <div className="text-gray-500 text-center py-10">No winner market data available</div>
          ) : (
            <div className="space-y-1">
              {winner.outcomes.map((o, i) => (
                <div
                  key={o.condition_id}
                  className="flex items-center gap-3 px-4 py-3 bg-gray-900 border border-gray-800/50 rounded-lg hover:border-gray-700 transition-colors"
                >
                  <RankBadge rank={i + 1} />
                  <div className="w-32 font-medium text-white truncate">{o.team}</div>
                  <ProbBar pct={o.yes_price} maxPct={maxYes} />
                  <div className="w-16 text-right font-mono text-sm">
                    <span className={`${
                      o.yes_price >= 0.10 ? 'text-green-400' :
                      o.yes_price >= 0.03 ? 'text-yellow-400' :
                      'text-gray-500'
                    }`}>
                      {(o.yes_price * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-20 text-right text-xs text-gray-500">
                    {fmt$(o.volume)}
                  </div>
                </div>
              ))}

              {/* Probability sum check */}
              <div className="text-xs text-gray-600 text-right mt-2 pr-4">
                Sum of probabilities: {(winner.outcomes.reduce((s, o) => s + o.yes_price, 0) * 100).toFixed(1)}%
                {winner.outcomes.reduce((s, o) => s + o.yes_price, 0) > 1.05 && (
                  <span className="text-yellow-500 ml-2">(overround detected)</span>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Qualifiers Tab */}
      {tab === 'qualifiers' && (
        <>
          {qualifiers.length === 0 ? (
            <div className="text-gray-500 text-center py-10">No qualifier markets available</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {qualifiers.map((q) => (
                <div
                  key={q.condition_id}
                  className="flex items-center justify-between px-4 py-3 bg-gray-900 border border-gray-800/50 rounded-lg"
                >
                  <span className="font-medium text-white">{q.team}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-20 bg-gray-800 rounded-full h-3 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          q.yes_price >= 0.8 ? 'bg-green-500' :
                          q.yes_price >= 0.5 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${q.yes_price * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-sm w-14 text-right">
                      {(q.yes_price * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
