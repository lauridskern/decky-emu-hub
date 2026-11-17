/**
 * One copy of the backend's state for the page and the Quick Access panel.
 *
 * Nothing runs while idle: the state is fetched when something mounts, after
 * an action, and when the backend sends an event. Only while a job is queued
 * or running is it fetched again, once a second, and that stops by itself
 * as soon as the last job is done (AGENTS.md §10).
 */
import { getState, State } from "./api";

let current: State | null = null;
let error: string | null = null;
const listeners = new Set<() => void>();
let pollTimer: number | null = null;
let inflight: Promise<State | null> | null = null;

function notify() {
  listeners.forEach((listener) => listener());
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const snapshot = (): State | null => current;
export const lastError = (): string | null => error;

function schedule() {
  if (pollTimer !== null) return;
  if (!current?.busy || listeners.size === 0) return;
  pollTimer = window.setTimeout(() => {
    pollTimer = null;
    refresh().catch(() => undefined);
  }, 1000);
}

export function setState(next: State | null | undefined): void {
  if (!next) return;
  current = next;
  error = null;
  notify();
  schedule();
}

export function refresh(): Promise<State | null> {
  if (inflight) return inflight;
  inflight = getState()
    .then((next) => {
      setState(next);
      return next;
    })
    .catch((reason) => {
      error = String(reason);
      notify();
      return null;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}
