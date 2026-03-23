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
                <th className="py-3 px-2 text-center" style={{ minWidth: '200px' }}>Yes / No</th>
                <th className="py-3 px-2 text-right">Volume</th>
                <th className="py-3 px-2 text-right">Liquidity</th>
              </tr>
            </thead>
            <tbody>
              {markets.map((m) => {
                const yes = m.yes_price ?? 0;
                const no = m.no_price ?? (1 - yes);
                const yesPct = (yes * 100).toFixed(1);
                const noPct = (no * 100).toFixed(1);
                return (
                <tr key={m.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-3 px-2">
                    <div className="font-medium text-white">
                      {m.away_team ? `${m.home_team} vs ${m.away_team}` : m.home_team}
                    </div>
                    <div className="text-xs text-gray-500 truncate max-w-md">{m.question}</div>
                  </td>
                  <td className="py-3 px-2">
                    <span className="text-xs px-2 py-0.5 bg-gray-800 rounded">{m.league}</span>
                  </td>
                  <td className="py-3 px-2">
                    {m.yes_price != null ? (
                      <div className="space-y-1">
                        {/* Price bar */}
                        <div className="flex h-5 rounded-md overflow-hidden bg-gray-800">
                          <div
                            className="bg-green-600 flex items-center justify-center text-[10px] font-bold text-white transition-all"
                            style={{ width: `${yes * 100}%`, minWidth: yes > 0.05 ? '32px' : '0' }}
                          >
                            {yes >= 0.05 && `${yesPct}%`}
                          </div>
                          <div
                            className="bg-red-600/80 flex items-center justify-center text-[10px] font-bold text-white transition-all"
                            style={{ width: `${no * 100}%`, minWidth: no > 0.05 ? '32px' : '0' }}
                          >
                            {no >= 0.05 && `${noPct}%`}
                          </div>
                        </div>
                        {/* Labels */}
                        <div className="flex justify-between text-[10px] font-mono">
                          <span className="text-green-400">Yes {yesPct}%</span>
                          <span className="text-red-400">No {noPct}%</span>
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-600 text-center block">—</span>
                    )}
                  </td>
                  <td className="py-3 px-2 text-right text-gray-400">
                    ${m.volume >= 1000 ? `${(m.volume / 1000).toFixed(1)}K` : m.volume.toFixed(0)}
                  </td>
                  <td className="py-3 px-2 text-right text-gray-400">
                    ${m.liquidity >= 1000 ? `${(m.liquidity / 1000).toFixed(1)}K` : m.liquidity.toFixed(0)}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
