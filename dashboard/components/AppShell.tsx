"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import Sidebar from "./Sidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      {/* mobile top bar */}
      <div className="fixed inset-x-0 top-0 z-30 flex items-center gap-3 border-b border-border-soft bg-background-alt/90 px-4 py-3 backdrop-blur-sm lg:hidden">
        <button
          onClick={() => setOpen(true)}
          aria-label="Open navigation"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-soft text-foreground"
        >
          <Menu size={16} />
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-accent to-accent-2 font-mono-tight text-xs font-bold text-white">
            BX
          </div>
          <span className="font-mono-tight text-sm font-bold text-foreground">BOOTX</span>
        </div>
      </div>

      {/* backdrop */}
      {open && (
        <button
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
        />
      )}

      {/* sidebar: static on desktop, sliding drawer on mobile */}
      <div
        className={`fixed inset-y-0 left-0 z-50 transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="relative h-full">
          <button
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
            className="absolute right-3 top-6 flex h-7 w-7 items-center justify-center rounded-lg border border-border-soft text-muted lg:hidden"
          >
            <X size={14} />
          </button>
          <Sidebar onNavigate={() => setOpen(false)} />
        </div>
      </div>

      <main className="min-w-0 flex-1 px-4 pb-8 pt-20 sm:px-6 lg:px-8 lg:pt-7">{children}</main>
    </div>
  );
}
