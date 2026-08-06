# LegiScan ingester — compliance spec (follow exactly; violations = suspended access)

Key stored in `defund-war-room/.legiscan_key` (gitignored). Loaded via file read or `LEGISCAN_KEY` env. Never in code/chat.

## Query budget
- Public key = **30,000 queries/month**, resets on the 1st. Cache aggressively.
- Always check JSON `"status"` == `"OK"` (else `"ERROR"`) and handle.

## Work loop (the compliant pattern)
1. **`getSearchRaw`** with our keyword queries (per state or national). Returns `bill_id + change_hash` cheaply — this is the periodic driver.
   - Keyword set: abortion, "reproductive health", mifepristone/misoprostol, Medicaid "prohibited entity"/defund, "Title X"/"family planning", Comstock, "fetal personhood"/personhood, EMTALA, "gestational".
2. Compare each `change_hash` to stored value. **Same hash = same data → use local cache, spend nothing.**
3. Only on **new/changed** hash: call `getBill` (metadata+status), and `getBillText` (doc via `doc_id` from getBill) if text needed.
4. Repeat daily. A targeted daily sweep stays far under 30k.

## Hashes (they said "use them. No. Really." x3)
- `change_hash + bill_id` for bill data.
- `dataset_hash + session_id` for any dataset archive — **failure to diff = suspended access.**
- Store + compare before every spend.

## Caching
- Persist all JSON locally (SQLite or JSON files) for replayability.
- Base64 blobs (texts/datasets) decoded once, never re-downloaded.

## Hard rules
- **NO scraping legiscan.com front-end** (API only) — suspension.
- **NO multiple public keys** — suspension.
- **CC BY 4.0**: attribute "LegiScan LLC" + link legiscan.com in any derivative output/report.
- Respect the free public service.

## Routing into the War Room
Each new/changed matching bill → a Signal routed to a threat (fed_defund / state_exclusion / fda_mife / titlex / comstock / emtala / personhood), SLOW lane (bills at introduction = long lead). Apply the no-backfill-state weight for red/rural states. Precision gate: require a repro-relevant token in title/description before routing (same discipline as the FR feed).
