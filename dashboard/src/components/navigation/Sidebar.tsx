import { NavLink, useLocation } from "react-router-dom";

import { navItems } from "./navItems";

export function Sidebar() {
  const location = useLocation();

  const analyticsItems = [
    { label: "Replay", hash: "#replay" },
    { label: "Session", hash: "#session" },
    { label: "Regime", hash: "#regime" },
    { label: "Expectancy", hash: "#expectancy" },
    { label: "Backtest", hash: "#backtest" },
    { label: "Monte Carlo", hash: "#monte-carlo" },
  ];

  return (
    <aside className="w-full min-[1600px]:w-[180px] flex-shrink-0 bg-white border border-[#d9d9d9] rounded-lg p-3 sticky top-3 h-fit font-mono flex flex-col gap-3 min-[1600px]:gap-2 shadow-sm" aria-label="Dashboard navigation">
      <div>
        <div className="text-[12px] uppercase font-bold tracking-wider text-[#404040] mb-2 px-1.5 pb-2 border-b border-[#d9d9d9] hidden min-[1600px]:block">System Console</div>
        <nav className="flex flex-row min-[1600px]:flex-col gap-1 min-[1600px]:gap-0.5 flex-wrap">
          {navItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                `nav-link ${isActive ? "active " : ""}block text-[13px] py-2 px-3 rounded transition-all leading-tight ${
                  isActive
                    ? "bg-[#ececec] text-black font-bold border-l-4 border-black min-[1600px]:pl-2 pl-3"
                    : "text-[#404040] hover:text-black hover:bg-[#f5f5f5]"
                }`
              }
              end={item.path === "/"}
              key={item.path}
              to={item.path}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div>
        <div className="text-[12px] uppercase font-bold tracking-wider text-[#404040] mt-0 min-[1600px]:mt-4 mb-2 px-1.5 pb-2 border-b border-[#d9d9d9] hidden min-[1600px]:block">Research Suite</div>
        <nav className="flex flex-row min-[1600px]:flex-col gap-1 min-[1600px]:gap-0.5 flex-wrap">
          {analyticsItems.map((item) => {
            const path = `/research${item.hash}`;
            const isActive = location.pathname === "/research" && location.hash === item.hash;
            return (
              <NavLink
                className={
                  `nav-link ${isActive ? "active " : ""}block text-[13px] py-2 px-3 rounded transition-all leading-tight ${
                    isActive
                      ? "bg-[#ececec] text-black font-bold border-l-4 border-black min-[1600px]:pl-2 pl-3"
                      : "text-[#404040] hover:text-black hover:bg-[#f5f5f5]"
                  }`
                }
                key={item.hash}
                to={path}
              >
                <div className="flex items-center gap-1.5 justify-between min-w-[70px]">
                  <span>{item.label}</span>
                  <span className="text-[10px] text-[#666666] font-sans font-normal scale-90">plan</span>
                </div>
              </NavLink>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
