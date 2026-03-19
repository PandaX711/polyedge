import { useEffect, useState } from 'react';
import type { AIReport } from '../api';
import { api } from '../api';

function ProbBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-400 w-16">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value * 100}%` }} />
      </div>
      <span className="text-xs font-mono w-12 text-right">{(value * 100).toFixed(1)}%</span>
    </div>
  );
}

export default function Analysis() {
  const [reports, setReports] = useState<AIReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReports().then((r) => {
      setReports(r);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-gray-400 text-center py-20">Loading...</div>;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">AI Analysis</h1>

      {reports.length === 0 ? (
        <div className="text-gray-500 text-center py-10">
          No AI reports yet. Reports are generated when strategies run on markets with sufficient data.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {reports.map((r) => (
            <div key={r.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">
                    {r.home_team} vs {r.away_team}
                  </h3>
                  <div className="text-xs text-gray-500 mt-1">
                    {r.created_at && new Date(r.created_at).toLocaleString()}
                    {r.model && <span className="ml-2 text-gray-600">{r.model}</span>}
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-bold px-2 py-1 rounded ${
                    r.prediction === 'HOME_WIN' ? 'bg-blue-900/50 text-blue-400' :
                    r.prediction === 'AWAY_WIN' ? 'bg-purple-900/50 text-purple-400' :
                    'bg-gray-800 text-gray-400'
                  }`}>
                    {r.prediction?.replace('_', ' ')}
                  </span>
                  {r.confidence != null && (
                    <div className="text-xs text-gray-500 mt-1">
                      Confidence: {(r.confidence * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              </div>

              {/* Probability bars */}
              <div className="space-y-2">
                {r.home_win_prob != null && (
                  <ProbBar label="Home" value={r.home_win_prob} color="bg-blue-500" />
                )}
                {r.draw_prob != null && (
                  <ProbBar label="Draw" value={r.draw_prob} color="bg-gray-500" />
                )}
                {r.away_win_prob != null && (
                  <ProbBar label="Away" value={r.away_win_prob} color="bg-purple-500" />
                )}
              </div>

              {/* Key factors */}
              {r.key_factors && r.key_factors.length > 0 && (
                <div>
                  <div className="text-xs text-gray-400 mb-1">Key Factors</div>
                  <div className="flex flex-wrap gap-1">
                    {r.key_factors.map((f, i) => (
                      <span key={i} className="text-xs bg-gray-800 px-2 py-0.5 rounded">{f}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Reasoning */}
              {r.reasoning && (
                <div className="text-sm text-gray-400 border-t border-gray-800 pt-3">
                  {r.reasoning}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
