import { useEffect, useState } from 'react';
import type { Market } from '../api';
import { api } from '../api';

const LEAGUES = ['All', 'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'UCL', 'WorldCup'];

export default function Markets() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [league, setLeague] = useState('All');
  const [loading, setLoading] = useState(true);

  const load = (l: string) => {
    setLoading(true);
    api.getMarkets(l === 'All' ? undefined : l).then((m) => {
      setMarkets(m);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(league); }, [league]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Markets</h1>
        <button
          onClick={() => { api.triggerScan(); setTimeout(() => load(league), 3000); }}
          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm"
        >
          Refresh
        </button>
      </div>

      {/* League filter tabs */}
      <div className="flex gap-1 flex-wrap">
        {LEAGUES.map((l) => (
          <button
            key={l}
            onClick={() => setLeague(l)}
            className={`px-3 py-1 rounded-lg text-sm transition-colors ${
              league === l ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-gray-400 text-center py-10">Loading...</div>
      ) : markets.length === 0 ? (
        <div className="text-gray-500 text-center py-10">
          No markets found. Click Refresh to scan Polymarket.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800 text-left">
                <th className="py-3 px-2">Match</th>
                <th className="py-3 px-2">League</th>
                <th className="py-3 px-2 text-right">Price</th>
                <th className="py-3 px-2 text-right">Volume</th>
                <th className="py-3 px-2 text-right">Liquidity</th>
              </tr>
            </thead>
            <tbody>
              {markets.map((m) => (
                <tr key={m.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-3 px-2">
                    <div className="font-medium text-white">{m.home_team} vs {m.away_team}</div>
                    <div className="text-xs text-gray-500 truncate max-w-md">{m.question}</div>
                  </td>
                  <td className="py-3 px-2">
                    <span className="text-xs px-2 py-0.5 bg-gray-800 rounded">{m.league}</span>
                  </td>
                  <td className="py-3 px-2 text-right font-mono">
                    {m.yes_price != null ? (
                      <span className="text-green-400">{(m.yes_price * 100).toFixed(1)}%</span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                  <td className="py-3 px-2 text-right text-gray-400">
                    ${m.volume >= 1000 ? `${(m.volume / 1000).toFixed(1)}K` : m.volume.toFixed(0)}
                  </td>
                  <td className="py-3 px-2 text-right text-gray-400">
                    ${m.liquidity >= 1000 ? `${(m.liquidity / 1000).toFixed(1)}K` : m.liquidity.toFixed(0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
