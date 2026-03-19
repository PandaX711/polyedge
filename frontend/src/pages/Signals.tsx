import { useEffect, useState } from 'react';
import type { Signal } from '../api';
import { api } from '../api';

export default function Signals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.getSignals(filter || undefined).then((s) => {
      setSignals(s);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]);

  const handleAction = async (id: number, action: string) => {
    await api.actionSignal(id, action);
    load();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Signals</h1>
        <button
          onClick={() => { api.triggerStrategies(); setTimeout(load, 3000); }}
          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm"
        >
          Run Strategies
        </button>
      </div>

      <div className="flex gap-1">
        {['', 'pending', 'confirmed', 'executed', 'expired'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-lg text-sm ${
              filter === s ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-gray-400 text-center py-10">Loading...</div>
      ) : signals.length === 0 ? (
        <div className="text-gray-500 text-center py-10">No signals found</div>
      ) : (
        <div className="space-y-3">
          {signals.map((s) => (
            <div key={s.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-mono px-2 py-0.5 rounded font-bold ${
                      s.direction === 'BUY_YES'
                        ? 'bg-green-900/50 text-green-400 border border-green-800'
                        : 'bg-red-900/50 text-red-400 border border-red-800'
                    }`}>
                      {s.direction}
                    </span>
                    <span className="text-sm bg-gray-800 px-2 py-0.5 rounded">{s.strategy}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      s.status === 'pending' ? 'bg-yellow-900/50 text-yellow-400' :
                      s.status === 'confirmed' ? 'bg-blue-900/50 text-blue-400' :
                      s.status === 'executed' ? 'bg-green-900/50 text-green-400' :
                      'bg-gray-800 text-gray-500'
                    }`}>
                      {s.status}
                    </span>
                  </div>

                  <div className="text-xs text-gray-500 font-mono">{s.condition_id}</div>

                  {/* Three-way comparison */}
                  {(s.poly_prob != null || s.book_prob != null || s.ai_prob != null) && (
                    <div className="flex gap-4 text-xs">
                      {s.poly_prob != null && (
                        <div>
                          <span className="text-gray-500">Poly:</span>
                          <span className="text-indigo-400 ml-1">{(s.poly_prob * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {s.book_prob != null && (
                        <div>
                          <span className="text-gray-500">Book:</span>
                          <span className="text-orange-400 ml-1">{(s.book_prob * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {s.ai_prob != null && (
                        <div>
                          <span className="text-gray-500">AI:</span>
                          <span className="text-cyan-400 ml-1">{(s.ai_prob * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {s.consensus_delta != null && (
                        <div>
                          <span className="text-gray-500">Delta:</span>
                          <span className={`ml-1 ${s.consensus_delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {(s.consensus_delta * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="text-right space-y-2">
                  <div>
                    <div className="text-lg font-bold">{(s.confidence * 100).toFixed(0)}%</div>
                    <div className="text-xs text-gray-500">${s.suggested_size?.toFixed(1)} USDC</div>
                  </div>
                  {s.status === 'pending' && (
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleAction(s.id, 'confirm')}
                        className="px-2 py-1 text-xs bg-green-700 hover:bg-green-600 rounded"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => handleAction(s.id, 'reject')}
                        className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
