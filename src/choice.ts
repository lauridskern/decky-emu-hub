/**
 * Telling ROM-Store that the emulator for a console changed.
 *
 * Both plugins run in the same Steam page, so a DOM event on `window` reaches
 * ROM-Store's frontend without either plugin knowing whether the other is
 * installed. ROM-Store (src/index.tsx) listens for this event name and runs
 * its Steam sync, which re-points the game shortcuts it manages to the
 * launcher Steam ROM Manager's parsers now name. Keep the name and the detail
 * shape in step with ROM-Store.
 */
export const CHOICE_EVENT = "emuhub:emulator-choice";

export interface ChoiceDetail {
  console: string;
  emulator: string;
  auto?: boolean;
}

export function announceChoice(detail: ChoiceDetail): void {
  try {
    window.dispatchEvent(new CustomEvent<ChoiceDetail>(CHOICE_EVENT, { detail }));
  } catch {
    /* nothing listens: ROM-Store is not installed */
  }
}
