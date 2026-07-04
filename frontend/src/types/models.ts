/** Mirrors backend/app/api/v1/schemas/*.py response shapes. Decimals and
 * dates cross the wire as strings; components parse them at render time. */

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "user" | "admin";
  auth_provider: "local" | "google";
  email_verified: boolean;
}

export interface Company {
  id: string;
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  country: string;
  currency: string;
  market_cap: string | null;
  logo_url: string;
  description: string;
}

/** A live vendor search hit — not yet in our DB when `tracked` is false. */
export interface SymbolMatch {
  symbol: string;
  name: string;
  exchange: string;
  tracked: boolean;
}

export interface PriceBar {
  ts: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface TechnicalSignals {
  golden_cross: boolean;
  death_cross: boolean;
  breakout: boolean;
  breakdown: boolean;
  volume_spike: boolean;
  patterns: string[];
}

export interface Technicals {
  computed_at: string;
  ema_20: string | null;
  ema_50: string | null;
  ema_200: string | null;
  rsi_14: string | null;
  macd: string | null;
  macd_signal: string | null;
  macd_hist: string | null;
  atr_14: string | null;
  vwap: string | null;
  bb_upper: string | null;
  bb_mid: string | null;
  bb_lower: string | null;
  trend: "strong_up" | "up" | "neutral" | "down" | "strong_down";
  signals: TechnicalSignals;
  support: { price: string; strength: number }[];
  resistance: { price: string; strength: number }[];
}

export interface Fundamentals {
  period: string;
  fiscal_date: string;
  revenue: string | null;
  revenue_growth_yoy: string | null;
  net_income: string | null;
  eps: string | null;
  eps_growth_yoy: string | null;
  total_debt: string | null;
  debt_to_equity: string | null;
  free_cash_flow: string | null;
  operating_cash_flow: string | null;
  roe: string | null;
  roa: string | null;
  pe: string | null;
  peg: string | null;
  gross_margin: string | null;
  operating_margin: string | null;
  net_margin: string | null;
  institutional_ownership_pct: string | null;
  dividend_yield: string | null;
  dividend_payout_ratio: string | null;
}

export interface NewsItem {
  id: string;
  source: string;
  url: string;
  title: string;
  published_at: string | null;
  sentiment: number | null;
  importance: number | null;
  summary: string | null;
  risks: string[];
  opportunities: string[];
}

export interface ReportSection {
  text: string;
  sources: string[];
}

export interface ResearchReport {
  id: string;
  generated_by: string;
  ai_provider: string;
  ai_model: string;
  summary: string;
  sections: Record<string, ReportSection>;
  version: number;
  created_at: string;
}

export interface ScoreBreakdown {
  news: number;
  technicals: number;
  fundamentals: number;
  momentum: number;
  institutional: number;
  risk: number;
  macro: number;
}

export type RecommendationAction = "strong_buy" | "buy" | "hold" | "reduce" | "avoid";

export interface Recommendation {
  id: string;
  symbol: string;
  action: RecommendationAction;
  current_price: string;
  entry_zone_low: string;
  entry_zone_high: string;
  stop_loss: string;
  take_profit_1: string;
  take_profit_2: string;
  take_profit_3: string;
  holding_period: "swing" | "short" | "medium" | "long";
  confidence: number;
  risk_reward: string;
  pros: string[];
  cons: string[];
  explanation: string;
  uncertainty_note: string;
  master_score: number;
  score_breakdown: ScoreBreakdown | null;
  status: "active" | "expired" | "superseded";
  created_at: string;
}

export interface Prediction {
  id: string;
  horizon: "1d" | "7d" | "30d" | "90d";
  expected_direction: "up" | "down" | "sideways";
  expected_range_low: string;
  expected_range_high: string;
  confidence: number;
  price_at_prediction: string;
  predicted_at: string;
}

export interface MarketOverview {
  market_trend: string;
  fear_greed: number;
  vix: number | null;
  oil: number | null;
  gold: number | null;
  btc: number | null;
  narrative: string;
  risks: string[];
  outlook: string;
}

export interface SectorTrend {
  sector: string;
  trend: string;
}

export interface Mover {
  symbol: string;
  name: string;
  price: string;
  change_pct: string;
  currency: string;
}

export interface MarketEvent {
  event_type: string;
  title: string;
  scheduled_at: string;
  company_symbol: string | null;
  importance: number;
  payload: Record<string, unknown>;
}

export interface Opportunity {
  symbol: string;
  company_name: string;
  reasons: string[];
  confidence: number;
  catalysts: string[];
  risk: string;
  entry_zone_low: string;
  entry_zone_high: string;
}

export interface Portfolio {
  id: string;
  name: string;
  base_currency: string;
  cash_balance: string;
  transaction_count: number;
}

export interface PortfolioHolding {
  symbol: string;
  sector: string;
  quantity: string;
  avg_cost: string;
  price: string;
  market_value: string;
  unrealized_pnl: string;
  unrealized_pnl_pct: number;
}

export interface PortfolioAnalytics {
  total_value: string;
  cash_balance: string;
  unrealized_pnl: string;
  unrealized_pnl_pct: number;
  allocation_pct: Record<string, number>;
  sector_exposure_pct: Record<string, number>;
  diversification_score: number;
  risk_score: number;
  health_grade: "A" | "B" | "C" | "D" | "F";
  rebalancing_suggestions: string[];
  holdings: PortfolioHolding[];
}

export interface Watchlist {
  id: string;
  name: string;
  is_default: boolean;
  symbols: string[];
}

export type AlertType =
  | "sentiment_shift"
  | "breakout"
  | "support_break"
  | "resistance_break"
  | "volume_spike"
  | "analyst_upgrade"
  | "confidence_change"
  | "price_target";

export interface Alert {
  id: string;
  symbol: string;
  alert_type: AlertType;
  condition: Record<string, unknown>;
  is_active: boolean;
  cooldown_minutes: number;
  last_triggered_at: string | null;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

export interface LeaderboardEntry {
  sector: string;
  horizon: string;
  rolling_accuracy: number;
  sample_size: number;
}

export interface AdminStats {
  total_users: number;
  active_alerts: number;
  total_recommendations: number;
  ai_spend_usd: number;
}

export interface AIUsageEntry {
  provider: string;
  model: string;
  agent: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  created_at: string | null;
}

export interface AdminSettings {
  ai_provider: string;
  ai_fallback_providers: string[];
  score_weights: Record<string, number>;
}
