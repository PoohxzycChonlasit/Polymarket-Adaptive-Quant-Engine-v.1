"use client";

import { useState } from "react";
import { useSharedState, Ic, LiveDot, Ticker, Particles, SERVER_IP } from "@/lib/shared";
import { OverviewScreen, PositionsScreen, QuantScreen, LogScreen } from "@/lib/mobile-screens";
import { DesktopDashboard, DesktopPositions, DesktopAnalytics, DesktopLog } from "@/lib/desktop-screens";

/* ══════════════════════════════════
   MOBILE APP
══════════════════════════════════ */
function MobileApp() {
  const [tab, setTab] = useState("overview");
  const { equity, scan, countdown, now, balance, positions, trades, kpis } = useSharedState();

  const tabs = [
    { id: "overview",  emoji: "⚡", label: "Overview" },
    { id: "positions", emoji: "📍", label: "Positions" },
    { id: "quant",     emoji: "🧮", label: "Quant" },
    { id: "log",       emoji: "📋", label: "Log" },
  ];

  return (
    <div style={{ width: "100%", height: "100vh", background: "var(--bg)", position: "relative", overflow: "hidden", display: "flex", flexDirection: "column", color: "var(--t1)" }}>
      {/* STATUS BAR */}
      <div style={{ position: "relative", zIndex: 10, padding: "14px 18px 0", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: "linear-gradient(135deg,oklch(0.78 0.28 142),oklch(0.58 0.22 148))", display: "flex", alignItems: "center", justifyContent: "center", color: "#010a06", boxShadow: "0 0 20px var(--neon-glow)", animation: "float 3s ease infinite", flexShrink: 0 }}>
            <Ic.Zap />
          </div>
          <div>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--t1)", letterSpacing: "-0.01em", lineHeight: 1 }}>
              PolyTrade<span style={{ color: "var(--neon)" }}> Pro</span>
            </p>
            <p style={{ fontSize: 8, color: "var(--t3)", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", lineHeight: 1, marginTop: 2 }}>Quant Engine v3.6</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 5, background: "rgba(0,255,80,0.06)", border: "1px solid rgba(0,255,80,0.14)", borderRadius: 9, padding: "5px 10px" }}>
            <LiveDot size={5} />
            <span className="mono" style={{ fontSize: 9, fontWeight: 700, color: "var(--t2)" }}>{now}</span>
          </div>
        </div>
      </div>

      {/* TICKER */}
      <div style={{ position: "relative", zIndex: 10, marginTop: 8, flexShrink: 0 }}>
        <Ticker scan={scan} />
      </div>

      {/* TAB PROGRESS */}
      <div style={{ position: "relative", zIndex: 10, padding: "8px 16px 4px", flexShrink: 0, display: "flex", gap: 5 }}>
        {tabs.map(t => (
          <div key={t.id} onClick={() => setTab(t.id)} style={{ flex: 1, height: 2, borderRadius: 2, background: tab === t.id ? "var(--neon)" : "rgba(0,255,80,0.08)", cursor: "pointer", transition: "all .25s", boxShadow: tab === t.id ? "0 0 10px var(--neon)" : "none" }} />
        ))}
      </div>

      {/* CONTENT */}
      <div key={tab} style={{ flex: 1, position: "relative", zIndex: 5, overflow: "hidden", minHeight: 0 }}>
        {tab === "overview"  && <OverviewScreen equity={equity} scan={scan} countdown={countdown} now={now} balance={balance} kpis={kpis} trades={trades} />}
        {tab === "positions" && <PositionsScreen countdown={countdown} positions={positions} />}
        {tab === "quant"     && <QuantScreen kpis={kpis} />}
        {tab === "log"       && <LogScreen trades={trades} kpis={kpis} />}
      </div>

      {/* BOTTOM NAV */}
      <div style={{ position: "relative", zIndex: 10, padding: "6px 12px 18px", flexShrink: 0 }}>
        <div style={{ background: "rgba(0,10,4,0.82)", border: "1px solid rgba(0,255,80,0.12)", backdropFilter: "blur(40px) saturate(180%)", WebkitBackdropFilter: "blur(40px) saturate(180%)", borderRadius: 24, padding: "8px 6px", display: "flex", justifyContent: "space-around", boxShadow: "0 -4px 30px rgba(0,255,80,0.06),0 20px 60px rgba(0,0,0,0.6)" }}>
          {tabs.map(t => {
            const isActive = tab === t.id;
            return (
              <button key={t.id} id={`nav-${t.id}`} onClick={() => setTab(t.id)} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 2, background: isActive ? "rgba(0,255,80,0.10)" : "none", border: isActive ? "1px solid rgba(0,255,80,0.20)" : "1px solid transparent", cursor: "pointer", padding: "6px 0", borderRadius: 15, transition: "all .22s cubic-bezier(.16,1,.3,1)", position: "relative" }}>
                {isActive && <div style={{ position: "absolute", top: -1, left: "50%", transform: "translateX(-50%)", width: 20, height: 2, borderRadius: 1, background: "var(--neon)", boxShadow: "0 0 8px var(--neon)" }} />}
                <span style={{ fontSize: 18, filter: isActive ? "drop-shadow(0 0 8px var(--neon))" : "none", transition: "filter .22s ease" }}>{t.emoji}</span>
                <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.02em", color: isActive ? "var(--neon)" : "rgba(180,255,200,0.25)", transition: "color .22s ease" }}>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════
   DESKTOP APP
══════════════════════════════════ */
function DesktopApp() {
  const [page, setPage] = useState("dashboard");
  const { equity, scan, countdown, now, balance, positions, trades, kpis } = useSharedState();

  const navItems = [
    { id: "dashboard", icon: Ic.Activity, label: "Dashboard" },
    { id: "positions", icon: Ic.Layers,   label: "Positions" },
    { id: "analytics", icon: Ic.BarChart, label: "Analytics" },
    { id: "log",       icon: Ic.List,     label: "Trade Log" },
  ];

  return (
    <div style={{ width: "100%", height: "100vh", background: "var(--bg)", color: "var(--t1)", display: "flex", overflow: "hidden", position: "relative" }}>
      {/* BG */}
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 }}>
        <div style={{ position: "absolute", top: "-20%", left: "5%", width: "40%", height: "50%", borderRadius: "50%", background: "oklch(0.72 0.22 142 / 0.05)", filter: "blur(100px)", animation: "gpulse 7s ease infinite" }} />
        <div style={{ position: "absolute", bottom: "0", right: "10%", width: "35%", height: "40%", borderRadius: "50%", background: "oklch(0.58 0.18 148 / 0.04)", filter: "blur(80px)" }} />
        <Particles />
      </div>

      {/* SIDEBAR */}
      <div style={{ width: 220, flexShrink: 0, display: "flex", flexDirection: "column", padding: "24px 14px", position: "relative", zIndex: 10, borderRight: "1px solid rgba(0,255,80,0.08)" }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 32, padding: "0 6px" }}>
          <div style={{ width: 32, height: 32, borderRadius: 10, background: "linear-gradient(135deg,oklch(0.78 0.28 142),oklch(0.58 0.22 148))", display: "flex", alignItems: "center", justifyContent: "center", color: "#010a06", boxShadow: "0 4px 16px var(--neon-glow)", flexShrink: 0 }}>
            <Ic.Zap />
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--t1)", lineHeight: 1 }}>PolyTrade<span style={{ color: "var(--neon)" }}> Pro</span></p>
            <p style={{ fontSize: 9, color: "var(--t3)", fontWeight: 600, letterSpacing: "0.1em", lineHeight: 1, marginTop: 2 }}>v3.6</p>
          </div>
        </div>

        {/* Balance mini */}
        <div className="gc" style={{ padding: 14, marginBottom: 20, background: "linear-gradient(135deg,rgba(0,255,80,0.055) 0%,rgba(0,0,0,0) 100%)" }}>
          <p style={{ fontSize: 9, color: "var(--t3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Paper Balance</p>
          <p className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--t1)", letterSpacing: "-0.01em" }}>$50.97</p>
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 4 }}>
            <span style={{ color: "var(--neon)", fontSize: 10, fontWeight: 700, display: "flex" }}><Ic.TrendUp /></span>
            <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: "var(--neon)" }}>+$0.97 PnL</span>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1 }}>
          <p style={{ fontSize: 9, color: "var(--t3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6, padding: "0 6px" }}>Navigation</p>
          {navItems.map(n => {
            const active = page === n.id;
            return (
              <button key={n.id} id={`sidebar-${n.id}`} onClick={() => setPage(n.id)} className={`side-nav-btn ${active ? "active" : ""}`}>
                <span style={{ color: active ? "var(--neon)" : "rgba(0,255,80,0.25)", display: "flex" }}><n.icon /></span>
                <span style={{ fontSize: 13, fontWeight: active ? 700 : 500, color: active ? "var(--t1)" : "var(--t2)" }}>{n.label}</span>
                {active && <div style={{ marginLeft: "auto", width: 5, height: 5, borderRadius: "50%", background: "var(--neon)", boxShadow: "0 0 6px var(--neon)" }} />}
              </button>
            );
          })}
        </nav>

        {/* Bottom status */}
        <div style={{ marginTop: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 10px", background: "rgba(0,255,80,0.03)", border: "1px solid rgba(0,255,80,0.08)", borderRadius: 10 }}>
            <LiveDot /><span style={{ fontSize: 10, color: "var(--t2)", fontWeight: 600 }}>Engine Running</span>
          </div>
          <div style={{ marginTop: 8, padding: "0 4px" }}>
            <span style={{ fontSize: 11, color: "var(--t3)" }}>IP Address: </span>
            <span className="mono" style={{ fontSize: 11, color: "var(--t2)", fontWeight: 700 }}>{SERVER_IP}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 8, padding: "0 4px" }}>
            <div style={{ width: 24, height: 24, borderRadius: 7, background: "rgba(0,255,80,0.05)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--t3)" }}><Ic.Telegram /></div>
            <span style={{ fontSize: 11, color: "var(--t3)" }}>Telegram Connected</span>
          </div>
        </div>
      </div>

      {/* MAIN */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
        {/* Topbar */}
        <div style={{ height: 56, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px", borderBottom: "1px solid rgba(0,255,80,0.07)" }}>
          <div>
            <p style={{ fontSize: 16, fontWeight: 700, color: "var(--t1)" }}>{navItems.find(n => n.id === page)?.label}</p>
            <p style={{ fontSize: 11, color: "var(--t2)" }}>Polymarket 5-min BTC/ETH/SOL · Polygon L2</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(0,255,80,0.04)", border: "1px solid rgba(0,255,80,0.08)", borderRadius: 9, padding: "6px 12px" }}>
              <span style={{ fontSize: 10, color: "var(--t3)" }}>IP Address:</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--t2)", fontWeight: 700 }}>{SERVER_IP}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(0,255,80,0.04)", border: "1px solid rgba(0,255,80,0.08)", borderRadius: 9, padding: "6px 12px" }}>
              <LiveDot size={5} />
              <span className="mono" style={{ fontSize: 11, color: "var(--t2)" }}>Synced {now}</span>
            </div>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: "rgba(0,255,80,0.05)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--t2)", cursor: "pointer" }}><Ic.Bell /></div>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: "rgba(0,255,80,0.05)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--t2)", cursor: "pointer" }}><Ic.Settings /></div>
          </div>
        </div>

        {/* Ticker */}
        <Ticker scan={scan} />

        {/* Page */}
        <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
          {page === "dashboard" && <DesktopDashboard equity={equity} scan={scan} countdown={countdown} balance={balance} kpis={kpis} trades={trades} positions={positions} />}
          {page === "positions" && <DesktopPositions countdown={countdown} positions={positions} />}
          {page === "analytics" && <DesktopAnalytics kpis={kpis} />}
          {page === "log"       && <DesktopLog trades={trades} kpis={kpis} />}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════
   ROOT — Responsive
══════════════════════════════════ */
export default function HomePage() {
  return (
    <>
      {/* Mobile (≤768px) */}
      <div className="mobile-only">
        <MobileApp />
      </div>
      {/* Desktop (>768px) */}
      <div className="desktop-only">
        <DesktopApp />
      </div>
    </>
  );
}
