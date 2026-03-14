MARKER_163A.MYCO.MODE_A.VERIFY.REPORT.V1
LAYER: L4
DOMAIN: UI|CHAT|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08

## Synopsis
Verification report for narrow implementation of `MYCO Mode A` in VETKA main surface.

## Implemented
1. Deterministic MYCO rule layer in frontend only:
   - `client/src/components/myco/mycoModeATypes.ts`
   - `client/src/components/myco/mycoModeARules.ts`
   - `client/src/components/myco/useMycoModeA.ts`
   - `client/src/components/myco/MycoGuideLane.tsx`
2. Main-surface mount in `client/src/App.tsx`.
3. Search-state bridge in `client/src/components/search/UnifiedSearchBar.tsx`.
4. Chat-input silence bridge in `client/src/components/chat/ChatPanel.tsx`.
5. Source-level contract test:
   - `tests/test_phase163a_mode_a_contract.py`

## Verification
### Passed
- `pytest -q tests/test_phase163a_mode_a_contract.py`
  - result: source-contract suite green after key-onboarding extension

### Passed in live browser verify
- Runtime used:
  - backend API on `http://localhost:5001`
  - Vite frontend on `http://127.0.0.1:3001`
- Tooling:
  - Playwright CLI wrapper via local skill
- Checked scenarios:
  1. initial load on main surface
     - result: MYCO lane visible with idle/tree guidance
  2. node click leading into chat surface
     - result: hint switched to chat-oriented guidance
  3. typing in chat input
     - result: MYCO lane disappeared as expected
  4. disabled `cloud/` search context click
     - result: one fallback warning hint shown
  5. switch to `web/`
     - result: hint changed to web-search guidance
  6. switch to `file/`
     - result: hint changed to filesystem guidance
  7. typing in main search input
     - result: MYCO lane disappeared as expected
  8. open chat history
     - result: hint changed to history-oriented guidance
  9. open model directory / phonebook
     - result: hint changed to phonebook-oriented guidance
  10. open scanner panel
      - result: hint changed to scanner-oriented guidance
  11. enter team setup mode
      - result: hint changed to team-setup guidance
  12. switch `Directed -> Knowledge -> Media Edit` tree modes
      - result: hint changed with the selected mode and no longer lagged behind the last user switch
  13. switch search source to `web/`
      - result: hint included internet guidance and explicit `save page to VETKA` next step
  14. switch search mode inside search surface
      - result: hint reflected active `HYB/SEM/KEY/FILE`-style search behavior rather than generic search copy
  15. open external `video` artifact
      - result: hint changed to video-specific ingest + media-edit guidance
  16. open external `audio` artifact
      - result: hint changed to audio-specific ingest + waveform guidance
  17. open code artifact with chat closed, then open chat while artifact stays active
      - result: hint warned about direct code editing, exposed favorite-star action, and changed from `open chat first` to `pin into current chat context`
  18. enter team setup from chat header
      - result: hint explained that team composition is assembled through role slots plus the left phonebook/model directory
  19. open active group chat runtime fixture
      - result: hint changed to `Group chat` and explicitly mentioned `@mention` plus Team settings reopening the phonebook-driven composition path
  20. open web artifact from real search UI flow with stubbed web-search response
      - result: hint stayed visible on artifact surface and correctly switched from search guidance to `External web artifact`
  21. key onboarding and search-provider remediation
      - result: source-level contracts now cover first-run zero-key hints, Model Directory key refresh bridge, and Tavily-specific `web/` remediation logic
- Browser artifact:
  - targeted Playwright verify run executed against `http://127.0.0.1:3001`

### Not clean at project level
- `npm run build` in `client/`
  - failed due pre-existing TypeScript errors outside `Mode A`
  - impacted areas include:
    - `src/components/artifact/*`
    - `src/components/mcc/*`
    - `src/config/tauri.ts`
    - `src/hooks/useSocket.ts`
    - `src/hooks/useArtifactMutations.ts`

## Recon verdict
- Narrow Mode A implementation is in place at source level.
- Local contract test is green.
- Live browser verify confirms the main deterministic transitions.
- API key onboarding is now deterministic at source level: zero-key, missing Tavily key, and provider-failure branches are encoded in the rules layer without adding LLM dependency.
- Full frontend build cannot be used yet as acceptance gate because the repository already contains unrelated TS failures.

## Residual gaps
- `SAVE TO VETKA` browser fixture now reaches the real button click from a real search-result UI path, but `/api/artifacts/save-webpage` hangs and leaves the button in `SAVING...`; this is now a backend/runtime gap, not a MYCO-guidance gap.
- Full project TypeScript build is still blocked by unrelated existing errors outside `Mode A`.

## Next step
- Debug `/api/artifacts/save-webpage` runtime hang, then re-run the existing browser fixture to close the last web-save acceptance gap.
- Extend Playwright coverage to:
  - dismiss/no-duplicate behavior
  - pin-to-chat from artifact with explicit open/closed chat assertions
