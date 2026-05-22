import type { TrafficState } from "../types";

const labels: Record<TrafficState, string> = {
  green: "GREEN",
  yellow: "YELLOW",
  red: "RED",
  blue: "BLUE",
  gray: "GRAY",
};

interface TrafficLightProps {
  state?: TrafficState;
  label?: string;
}

export function TrafficLight({ state = "blue", label }: TrafficLightProps) {
  return (
    <span className={`traffic traffic-${state}`} aria-label={labels[state]}>
      <span className="traffic-dot" />
      {label ?? labels[state]}
    </span>
  );
}
