import type { Tone } from "../types/dashboard";

export function getValue(source: Record<string, unknown> | undefined, keys: string[]): unknown {
  if (!source) {
    return undefined;
  }
  return keys.map((key) => source[key]).find((value) => value !== undefined && value !== null);
}

export function getStateTone(stateStatus?: string): Tone {
  if (stateStatus === "OK") {
    return "good";
  }
  if (stateStatus === "PARTIAL") {
    return "warn";
  }
  if (stateStatus === "ERROR") {
    return "bad";
  }
  return "neutral";
}
