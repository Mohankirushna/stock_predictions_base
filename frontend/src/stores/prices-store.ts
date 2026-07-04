import { create } from "zustand";

interface PriceTick {
  symbol: string;
  price: string;
  ts: string;
}

interface PricesState {
  bySymbol: Record<string, PriceTick>;
  applyTick: (tick: PriceTick) => void;
}

/** Latest live tick per symbol, fed by the /ws/prices channel. Company and
 * watchlist pages read from this store to flash price cells in realtime
 * without each owning its own socket connection. */
export const usePricesStore = create<PricesState>((set) => ({
  bySymbol: {},
  applyTick: (tick) =>
    set((state) => ({
      bySymbol: { ...state.bySymbol, [tick.symbol]: tick },
    })),
}));
