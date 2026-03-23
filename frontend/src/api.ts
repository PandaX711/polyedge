const BASE = '/api';

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface Market {
  id: number;
  condition_id: string;
  question: string;
  slug?: string;
  league?: string;
  home_team?: string;
  away_team?: string;
  match_date?: string;
  active: number;
  volume: number;
  liquidity: number;
  yes_price?: number;
  no_price?: number;
  created_at?: string;
}

export interface Signal {
  id: number;
  condition_id: string;
  strategy: string;
  direction: string;
  confidence: number;
  suggested_size?: number;
  poly_prob?: number;
  book_prob?: number;
  ai_prob?: number;
  consensus_delta?: number;
  status: string;
  created_at?: string;
}

export interface AIReport {
  id: number;
  condition_id: string;
  home_team?: string;
  away_team?: string;
  prediction?: string;
  confidence?: number;
  home_win_prob?: number;
  draw_prob?: number;
  away_win_prob?: number;
  key_factors?: string[];
  reasoning?: string;
  model?: string;
  created_at?: string;
}

export interface PortfolioSummary {
  total_positions: number;
  open_positions: number;
  total_invested: number;
  total_pnl: number;
  pending_signals: number;
}

export interface Position {
  id: number;
  condition_id: string;
  side: string;
  size: number;
  entry_price: number;
  current_price?: number;
  pnl: number;
  status: string;
  opened_at?: string;
}

export interface Outcome {
  team: string;
  yes_price: number;
  no_price: number;
  condition_id: string;
  volume: number;
  liquidity: number;
}

export interface MultiOutcomeEvent {
  event_id: string;
  title: string;
  slug: string;
  total_volume: number;
  total_liquidity: number;
  outcomes: Outcome[];
}

export interface VolumeTrendPoint {
  date: string;
  volume: number;
  liquidity: number;
  market_count: number;
}

export const api = {
  getMarkets: (league?: string) =>
    fetchJSON<Market[]>(`/markets/${league ? `?league=${league}` : ''}`),
  getSignals: (status?: string) =>
    fetchJSON<Signal[]>(`/signals/${status ? `?status=${status}` : ''}`),
  actionSignal: (id: number, action: string) =>
    fetchJSON<{ ok: boolean }>(`/signals/${id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    }),
  getReports: () => fetchJSON<AIReport[]>('/analysis/'),
  getReport: (conditionId: string) =>
    fetchJSON<AIReport | null>(`/analysis/${conditionId}`),
  getPortfolioSummary: () => fetchJSON<PortfolioSummary>('/portfolio/summary'),
  getPositions: () => fetchJSON<Position[]>('/portfolio/positions'),
  triggerScan: () => fetch(`${BASE}/trigger/scan`, { method: 'POST' }),
  triggerStrategies: () => fetch(`${BASE}/trigger/strategies`, { method: 'POST' }),
  getWCWinner: () => fetchJSON<MultiOutcomeEvent | null>('/worldcup/winner'),
  getWCQualifiers: () => fetchJSON<Outcome[]>('/worldcup/qualifiers'),
  getWCVolumeTrend: () => fetchJSON<VolumeTrendPoint[]>('/worldcup/volume-trend'),
};
