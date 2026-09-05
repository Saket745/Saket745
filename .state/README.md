Runtime bookkeeping for the profile intelligence workflow — not meant to be
edited by hand.

- `last-event.json` — id of the most recently seen public GitHub event, plus
  the timestamp of the last full recalculation. Used to decide whether a
  scheduled tick can skip straight past the expensive phase.
- `lifetime-cache.json` — per-year contribution totals and calendars for
  every *completed* year of the account's history, so those years are never
  re-fetched. Only the current year is ever pulled live.

Both are created automatically on the first workflow run.
