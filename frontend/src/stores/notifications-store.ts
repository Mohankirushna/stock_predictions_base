import { create } from "zustand";

import type { Notification } from "@/types/models";

interface NotificationsState {
  items: Notification[];
  unreadCount: number;
  push: (n: Notification) => void;
  setAll: (items: Notification[]) => void;
  markAllRead: () => void;
}

export const useNotificationsStore = create<NotificationsState>((set) => ({
  items: [],
  unreadCount: 0,
  push: (n) =>
    set((state) => ({
      items: [n, ...state.items].slice(0, 100),
      unreadCount: state.unreadCount + 1,
    })),
  setAll: (items) => set({ items, unreadCount: items.filter((i) => !i.read_at).length }),
  markAllRead: () =>
    set((state) => ({
      items: state.items.map((i) => ({ ...i, read_at: i.read_at ?? new Date().toISOString() })),
      unreadCount: 0,
    })),
}));
