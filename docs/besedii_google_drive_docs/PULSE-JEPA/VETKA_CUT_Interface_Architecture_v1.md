**VETKA CUT**

Interface Architecture & Functional Specification

For cinema professionals. By filmmakers, for filmmakers.

v1.0 \| 2026-03-14 \| Данила Гулин + Claude Opus 4.6

0\. Architectural principles: the constitution

**CUT не ищет единственно верный монтаж. CUT исследует множество допустимых монтажей под разные цели, аудитории и контексты.**

This is the foundational principle. Not one film --- a space of versions. Not one correct edit --- a set of valid trajectories through a graph of possibilities. Everything below serves this principle.

0.1 Two-circuit architecture

The system has two layers that work together but are NOT the same thing:

  -------------- ------------------------------------------------------------------------------------------------------------ -------------------------------------------------------------------------------------------------------------
                 **Circuit A: symbolic / editorial**                                                                          **Circuit B: learnable / predictive**

  What it is     Human-designed coordinate system                                                                             Learned world model

  Contains       DAG, scenes, storylines, versions, McKee triangle, Camelot wheel, pendulum, favorite moments, edit history   JEPA latent space, prediction error, visual rhythm, learned similarity, transition priors, scene clustering

  Why needed     Control, explainability, versioning, deliberate artistic decisions                                           Discovering patterns humans miss, adapting to style/epoch/audience, handling what rules can\'t describe

  Who controls   Editor (human) --- always final authority                                                                    System (AI) --- proposes, never decides

  Failure mode   Too rigid --- becomes a formula that kills creativity                                                        Too opaque --- makes decisions nobody can explain or override
  -------------- ------------------------------------------------------------------------------------------------------------ -------------------------------------------------------------------------------------------------------------

0.2 Bridge layer: where the two circuits meet

Between Circuit A and Circuit B sits a bridge. It translates in both directions: **learned states → editable concepts** (JEPA detects visual rhythm → PULSE expresses it as BPM on Camelot wheel). And: **editorial constraints → search over variants** (editor sets McKee triangle position + target mood → system searches JEPA latent space for matching edits).

  -------------------------- --------------------------------- ------------------------------------- ----------------------------------------------------------------------------
  **Direction**              **From**                          **To**                                **Example**

  Perception → Concepts      JEPA prediction error peaks       BPM markers on timeline (blue dots)   V-JEPA2 sees unexpected motion → visual beat marker appears

  Perception → Suggestions   JEPA scene similarity             Candidate clips in source browser     Script says \'rain at night\' → JEPA finds matching footage

  Constraints → Search       McKee triangle + Camelot target   Optimized edit sequence               Editor says \'archplot thriller in 8A\' → PULSE searches for best assembly

  Feedback → Learning        Favorite markers + chosen edits   Updated transition priors             Editor keeps picking certain cut types → JEPA learns preference
  -------------------------- --------------------------------- ------------------------------------- ----------------------------------------------------------------------------

0.3 The nine principles

**1. No single correct montage.** Multiple valid versions coexist. A children\'s version, a director\'s cut, a fan edit, a single-character cut --- all are trajectories through the same DAG. CUT enables exploration, not prescription.

**2. Editor is always sovereign.** JEPA proposes. PULSE suggests. Critics evaluate. But the human editor has absolute override. No AI decision is irreversible. Every auto-edit creates a new timeline --- the original is sacred.

**3. Symbolic layer provides coordinates.** Camelot, McKee, pendulum, scale matrix --- these are the coordinate system, not the truth. Like latitude/longitude: useful for navigation, but the territory is richer than the map.

**4. Learned layer provides perception.** JEPA sees what rules cannot describe: unexpected strong transitions, style-specific patterns, audience-specific responses. It extends the symbolic layer, not replaces it.

**5. The bridge is bidirectional.** Learned states become editable concepts (BPM markers, similarity scores). Editorial constraints become search queries over latent space. Neither layer works alone.

**6. Favorite markers are collective memory.** When viewers/editors mark favorite moments, they create weak supervision. Over time, the system learns what resonates --- not as a formula, but as a distribution of taste. This is MYCELIUM for aesthetics.

**7. Versions are first-class citizens.** Every timeline is a version. Versions branch from the DAG like git branches. They can be compared, merged, forked. Auto-montage always creates a new branch. The project is the graph of all versions.

**8. The formula must evolve.** When a montage pattern becomes predictable, it stops working. The symbolic layer (scale matrix, genre calibration) must be continuously refined. JEPA\'s learned layer adapts automatically. The human curates the symbolic layer --- this is the eternal craft.

**9. Music is in the montage, montage is in the music.** PULSE is the conductor that hears rhythm in everything: in script events (white BPM), in visual motion (blue BPM), in audio (green BPM). Three rhythms on one wheel. Synesthesia through vectors.

1\. Design philosophy

**Final Cut 7.0.3, not Final Cut X.** Every window is detachable, resizable, dockable. Multiple timelines visible simultaneously. The user decides the layout --- we provide the panels. Like a Swedish wardrobe: any shelf, any height, any combination.

**RULE: NO standard UI library buttons. Only custom monochrome SVG icons --- minimal, clean, black-and-white. No color in controls, no gradients, no 3D effects.**

**RULE: Every panel can be a tab inside another panel OR a standalone floating window. User drags to detach, drops to dock. Layout saves per project.**

**RULE: PULSE auto-edits ALWAYS create a new timeline. Never overwrite existing montage. Versioning: {project-name}\_cut-{NN}. Old timelines are read-only archives.**

**RULE: DAG is a universal view mode. Any panel that shows structure (project, timeline, effects) can switch to DAG view. Only monitors (playback) are exempt.**

2\. Panel catalog: seven core panels

VETKA CUT consists of seven panel types. Each can exist as a tab, a docked panel, or a floating window. Default layout described in section 3.

2.1 Script panel

  ---------------- -----------------------------------------------------------------------------------------------------------------
  **Property**     **Value**

  Axis             Y = time (vertical, chat-like). 1 line ≈ 1 minute (Courier 12pt standard)

  Content          Screenplay text OR auto-transcript + AI scene descriptions (documentary mode)

  Interaction      Click line → source monitor shows linked material, DAG highlights clusters, playhead syncs

  Playback         Play button scrolls text like teleprompter. Where no material linked --- shows text on black in Program Monitor

  BPM display      Three colored dots: green (audio 124bpm), blue (visual 96bpm), white (script 108 events/page)

  Markers          Script events auto-marked as white BPM dots on timeline. Manual markers also supported

  DAG mode         Available --- shows script as directed graph of scenes/beats with narrative edges

  Documentary      No screenplay? Import media → auto-transcribe → generate scene descriptions → becomes script
  ---------------- -----------------------------------------------------------------------------------------------------------------

2.2 DAG project panel

  ---------------- ---------------------------------------------------------------------------------------------------------------
  **Property**     **Value**

  Axis             Y = time in MCC/VETKA style (bottom=start, top=latest). Horizontal for large trees

  Content          Material organized by clusters: Characters, Locations, Takes/Dubs, Music, SFX, Graphics

  Interaction      Click node → source monitor shows asset, script highlights where used. Bidirectional linking

  Linked state     Nodes connected to active script line glow blue. Unlinked = neutral gray

  DAG mode         Native --- this IS a DAG. Directed edges show dependencies (character appears in scene, take covers location)

  Merge            Root project nodes from different sources merge naturally --- multiple shoots, stock footage, archive

  Lore clusters    Character lore, location history, prop details --- attached to DAG nodes as metadata. Click to expand
  ---------------- ---------------------------------------------------------------------------------------------------------------

2.3 Program monitor

  ---------------- -----------------------------------------------------------------------------------
  **Property**     **Value**

  Position         Right side (cinema standard). Fixed --- not convertible to DAG

  Content          Montage result playback. Shows assembled timeline output

  Overlay          Story Space 3D as floating mini-panel in corner (vectorscope mode). Toggle on/off

  Transport        Standard: play, pause, JKL shuttle, frame step. Timecode display

  Markers          Favorite-time markers shown as colored dots on scrubber bar
  ---------------- -----------------------------------------------------------------------------------

2.4 Source monitor

  ------------------ ------------------------------------------------------------------------------------------------------
  **Property**       **Value**

  Position           Right side below program monitor (or side-by-side in dual monitor setup). Fixed --- not DAG

  Content            Raw material preview. Selected from DAG project or script link

  Inspector          Below video: PULSE analysis --- Camelot key, scale, pendulum, dramatic_function, energy_profile, BPM

  In/Out             Set in/out points for three-point editing. Standard NLE workflow

  Favorite markers   Time-specific markers (not whole-clip likes). Exportable as SRT. Convertible to standard markers
  ------------------ ------------------------------------------------------------------------------------------------------

2.5 Timeline panel

  -------------------- -------------------------------------------------------------------------------------------------------------------------------
  **Property**         **Value**

  Axis                 X = time (left to right, horizontal). Classic NLE layout

  Tracks               V1, V2\... (blue), A1, A2\... (green). Unlimited tracks

  BPM track            Special track at bottom: green dots = audio beats, blue = visual cuts, white = script events, orange = all-sync (strong beat)

  Standard markers     Top of timeline (Premiere-style). Colors assignable. Favorite-time markers get dedicated color

  Multiple timelines   Tab bar at top: Main, cut-01, cut-02\... Click + to create. PULSE edits always create new tab

  Simultaneous view    Any timeline tab can be detached to separate window. View 2+ timelines at once (FCP 7 style)

  DAG mode             Available --- switches to node-based timeline (scenes as nodes, edges as transitions). Like DaVinci Fusion node graph

  Versioning           Auto-naming: {project}\_cut-{NN}. Old versions become read-only. Current = writable
  -------------------- -------------------------------------------------------------------------------------------------------------------------------

2.6 Story Space 3D panel

  ---------------- -------------------------------------------------------------------------------------------------------
  **Property**     **Value**

  Role             Analytical --- vectorscope for narrative. NOT a working surface

  Axes             Horizontal plane = Camelot wheel (key, mood). Vertical = McKee triangle (form). BPM = pulse at center

  Display          Current scene position as glowing dot. Film trajectory as path. Energy critics as color

  Default          Floating mini-panel inside Program Monitor corner. Can be detached to full panel

  Interaction      Rotate/tilt with mouse. Click on scene dot → syncs all panels to that scene
  ---------------- -------------------------------------------------------------------------------------------------------

2.7 Effects / node graph panel

  ---------------- --------------------------------------------------------------------------------------
  **Property**     **Value**

  Role             Node-based effects pipeline (like DaVinci Fusion nodes)

  DAG mode         Native --- this IS a node graph. Input → processing → output

  Nodes            Color correction, transitions, PULSE-driven effects, audio mix, text overlays

  Progressive      Start simple (cut-only), add nodes as needed. Complexity grows with user, not forced
  ---------------- --------------------------------------------------------------------------------------

3\. Default layout

Three-column layout with timeline strip at bottom. All panels resizable. Drag borders to resize (Swedish wardrobe principle).

  --------------------------- ---------------------------------- --------------------------------------------------
  **Position**                **Panel**                          **Size (default)**

  Left column                 Script (tab) / DAG project (tab)   220px width, full height minus timeline

  Center                      Program monitor                    Fills remaining width, 60% height

  Right column top            Source monitor                     280px width, 50% height

  Right column bottom         Inspector (PULSE data)             280px width, 50% height

  Bottom strip                Timeline (full width)              Full width, 180px height

  Floating (inside Program)   Story Space 3D mini                120x80px, bottom-right corner of Program Monitor
  --------------------------- ---------------------------------- --------------------------------------------------

Any panel can be dragged out to become a floating window. Any floating window can be docked back. Layout persists per project file.

4\. Axis conventions

Two time axes coexist in the system. They are not conflicting --- they serve different purposes:

  ------------------------- ---------------- ------------------------- -------------------------------------------------------------------------
  **Panel**                 **Time axis**    **Direction**             **Why**

  Script                    Y (vertical)     Bottom=00:00, Top=end     Chat-like reading flow. Natural for text. Matches MCC/VETKA tree

  DAG project               Y (vertical)     Bottom=root, Top=leaves   Tree grows up. Same as VETKA 3D Knowledge Graph. Merge at root

  Timeline                  X (horizontal)   Left=00:00, Right=end     Cinema standard. Horizontal screens. Video flows left→right

  DAG timeline (alt view)   X (horizontal)   Left=start, Right=end     Same content as timeline, but scenes as DAG nodes with transition edges

  Story Space 3D            No time axis     3D rotation               Analytical. Time is encoded as trajectory path, not axis
  ------------------------- ---------------- ------------------------- -------------------------------------------------------------------------

**Key insight:** DAG project uses Y-time (vertical, like VETKA/MCC) because project panels are typically narrow and tall. Timeline uses X-time (horizontal) because editing screens are wide. Both represent the same temporal data --- they are views, not models. The model is the DAG.

5\. BPM system: three rhythms

5.1 Three BPM sources

  ---------------- -------------------------------- --------------------------------------------------------------------------------------- -------------------------
  **BPM source**   **Color**                        **Origin**                                                                              **On timeline**

  Audio BPM        Green (NLE standard for audio)   PULSE librosa analysis of music/audio track                                             Green dots on BPM track

  Visual BPM       Blue (NLE standard for video)    V-JEPA2 prediction error peaks OR FFmpeg scene detection                                Blue dots on BPM track

  Script BPM       White (neutral, text)            Event density per page. 1 page = 60 sec. Events = stage directions + dialogue changes   White dots on BPM track
  ---------------- -------------------------------- --------------------------------------------------------------------------------------- -------------------------

5.2 Sync indicator

When all three BPM sources coincide within a tolerance window (±2 frames default), an orange dot appears --- this is a strong beat, the strongest possible edit point. PULSE auto-montage places cuts preferentially at these sync points.

BPM indicators also appear in the Script panel as three colored dots showing current tempo values. The center of Story Space 3D pulses at the dominant BPM rate.

5.3 Script BPM calculation

script_bpm = (event_count_in_page / 1.0) \* 60 // events per minute

// event = new stage direction, new character speaks, CUT TO, scene header

// Courier 12pt: 1 page ≈ 55 lines ≈ 60 seconds screen time

Dense dialogue page (many short exchanges) = high script BPM. Long descriptive passage = low script BPM. Action lines with many cuts written = very high script BPM.

6\. Marker system

  ---------------------- --------------------------- ----------------------------------- ------------------------------------------------------ --------------------
  **Marker type**        **Position**                **Color**                           **Purpose**                                            **Export**

  Standard marker        Top of timeline ruler       User-assigned (any)                 General purpose --- scene breaks, notes, TODOs         Premiere XML, EDL

  BPM marker             Bottom BPM track            Green/Blue/White/Orange             Auto-generated by PULSE. Indicates rhythmic events     pulse_markers.json

  Favorite-time marker   On clip in source monitor   Dedicated color (user picks once)   Mark specific moment in raw footage (not whole clip)   SRT file

  PULSE scene marker     Script panel + timeline     Amber                               Auto-generated scene boundaries from script analysis   pulse_scenes.json
  ---------------------- --------------------------- ----------------------------------- ------------------------------------------------------ --------------------

**Favorite-time markers** are the key differentiator from other NLE. Users mark specific moments (not whole clips) in source material. These export as SRT (standard subtitle format) for portability. They can be batch-converted to standard timeline markers. Auto-montage by favorites: PULSE takes all favorite markers, determines in/out points around each (by detecting natural boundaries), and assembles a cut in a new timeline.

**RULE: Favorite markers are SRT-exportable. Standard markers are Premiere XML / EDL exportable. BPM markers are internal JSON. All types visible simultaneously on timeline.**

7\. PULSE auto-montage workflow

7.1 Safety rule

**RULE: PULSE auto-montage and PULSE-assisted edits ALWAYS create a new timeline tab. Name: {project}\_cut-{NN+1}. The previous timeline becomes read-only. NEVER overwrite existing work.**

7.2 Three auto-montage modes

  ------------------- ----------------------------------- --------------------------------------------------------------------------------------------- ----------------------------------------------
  **Mode**            **Input**                           **Process**                                                                                   **Output**

  Favorite assembly   Favorite-time markers from source   PULSE finds natural in/out boundaries around each marker, orders by script or time            New timeline with selected moments assembled

  Script-driven       Script text + linked material       PULSE matches script scenes to material via JEPA similarity, places cuts at BPM sync points   New timeline following script structure

  Music-driven        Music track + video material        PULSE analyzes music BPM/key/energy, matches video clips to music sections via Camelot/mood   New timeline synced to music rhythm
  ------------------- ----------------------------------- --------------------------------------------------------------------------------------------- ----------------------------------------------

7.3 Agent visualization

During auto-montage, the DAG project panel shows agent activity: which scenes are being analyzed (pulsing nodes), which material is being compared (edges lighting up), which decisions have been made (nodes turn green). The Story Space 3D shows the evolving trajectory in real-time as scenes are placed.

8\. DAG as universal view mode

DAG is not just for the project panel. It is a view mode available in most panels:

  ---------------- --------------------------------------------------------------------------------------- ----------------------------------------------------------
  **Panel**        **DAG view shows**                                                                      **When useful**

  Script           Scene graph --- scenes as nodes, narrative flow as edges, subplot branches              Visualizing parallel storylines, story structure

  DAG project      Material tree --- assets clustered by type, linked to scenes                            Always (this is native DAG)

  Timeline         Scene-level DAG --- each scene is a node, transitions are edges (like DaVinci Fusion)   High-level overview of edit structure, reordering scenes

  Effects          Node graph --- processing pipeline with inputs/outputs                                  Color grading chains, audio processing, compositing

  Story Space 3D   3D DAG --- McKee triangle + Camelot wheel with film trajectory                          Analytical overview of dramatic structure
  ---------------- --------------------------------------------------------------------------------------- ----------------------------------------------------------

**RULE: Monitors (Program + Source) are the only panels that CANNOT switch to DAG. They are playback surfaces, always video/audio output.**

**DAG project uses Y-time (vertical)** because project panels are typically narrow/tall in the layout. **DAG timeline uses X-time (horizontal)** because timeline panels are wide. Same underlying DAG model, different visual projection. Toggle button switches between linear and DAG view in timeline panel.

9\. Panel synchronization

All panels are synchronized through a central playhead and selection state:

  ------------------------ ------------------ ---------------------------- ---------------------- ---------------------- ----------------------- ---------------------- --------------------------
  **Action**               **Script**         **DAG project**              **Timeline**           **Program monitor**    **Source monitor**      **Story Space**        **Inspector**

  Click script line        Highlights         Shows linked nodes           Moves playhead         Shows result at time   Shows linked material   Moves to scene point   Shows PULSE data

  Click DAG node           Highlights usage   Selects node                 No change              No change              Shows asset             No change              Shows node metadata

  Move timeline playhead   Scrolls to time    Highlights active clusters   Playhead moves         Plays frame            No change               Updates position       Updates for current clip

  Click Story Space dot    Scrolls to scene   Highlights scene cluster     Moves to scene start   Plays scene            No change               Highlights dot         Shows scene PULSE data

  Play transport           Auto-scrolls       Pulses active nodes          Playhead advances      Plays video            No change               Dot moves along path   Updates continuously
  ------------------------ ------------------ ---------------------------- ---------------------- ---------------------- ----------------------- ---------------------- --------------------------

10\. Project file structure

{project-name}/

project.vetka-cut.json // Master project file

script/

screenplay.md // Source screenplay or auto-transcript

script_analysis.json // PULSE scene breakdown, BPM events

media/ // Linked (not copied) media paths

timelines/

{name}\_cut-00.json // First assembly

{name}\_cut-01.json // PULSE auto-montage v1

{name}\_cut-02.json // Manual refinement

markers/

favorites.srt // Favorite-time markers (SRT format)

pulse_bpm.json // BPM analysis markers

pulse_scenes.json // Scene boundary markers

standard.json // User-placed standard markers

pulse/

score.json // PULSE partition for this project

cinema_matrix_overrides.json // Project-specific scale/genre tuning

triangle_position.json // McKee calibration for this project

dag/

project_graph.json // DAG structure (nodes, edges, clusters)

layout_state.json // Panel positions, sizes, dock state

export/

premiere.xml // FCP XML / Premiere export

edl/ // EDL files per timeline

11\. Visual design rules

  ------------------- ---------------------------------------------------------------------------------------------------------------
  **Rule**            **Specification**

  Background          Dark theme only. Black (#0D0D0D) primary, Dark gray (#1A1A1A) panels, (#252525) surfaces

  Text                White (#E0E0E0) primary, Gray (#888) secondary, DimGray (#555) disabled

  Icons               Custom SVG only. Monochrome (white on dark). 16x16 default, 24x24 toolbar. No fill, stroke only. 1.5px stroke

  Borders             0.5px solid #333. Panel dividers = 2px drag-handle (#222)

  Colors (semantic)   Video tracks = #85B7EB (blue). Audio tracks = #5DCAA5 (green). BPM markers by source color

  Buttons             No standard library. Custom: transparent bg, 0.5px border #444, hover bg #333, active scale(0.98)

  Font                Monospace for timecode/numbers (JetBrains Mono). Sans-serif for labels (Inter or system)

  Corners             4px radius on panels, 2px on buttons/inputs, 0 on timeline elements

  No gradients        Flat fills only. No shadows. No glow. No blur. Professional, not flashy

  Scrollbars          Thin (6px), dark, auto-hide. Never bright or system-default
  ------------------- ---------------------------------------------------------------------------------------------------------------

12\. User scenarios

12.1 Logging + sync (documentary)

1\. Import media folder → auto-scan, generate thumbnails, detect scene cuts (FFmpeg + V-JEPA2).

2\. Auto-transcribe all audio (Whisper) → generates script panel content.

3\. PULSE analyzes: BPM (audio + visual + script density), Camelot key, energy profile.

4\. User watches in source monitor, marks favorite moments (time-specific, not clip-level).

5\. DAG project auto-organizes: clusters by speaker, by location (from transcript/visual analysis).

6\. Favorites export as SRT for backup/sharing.

12.2 Auto-montage by favorites

1\. User has marked 30 favorite moments across raw footage.

2\. Clicks \'PULSE: assemble favorites\' → new timeline tab created: {name}\_cut-01.

3\. PULSE determines in/out around each favorite (natural sentence boundaries from transcript).

4\. Orders by script timeline or by PULSE energy curve (user choice).

5\. Places cuts at BPM sync points. Adds handles for fine-tuning.

6\. Old timeline untouched. User reviews in new tab.

12.3 PULSE JEPA full montage

1\. Script loaded (or generated from transcript). PULSE runs full analysis: scene breakdown, dramatic_function, pendulum, Camelot path.

2\. JEPA similarity search matches script scenes to available material in DAG project.

3\. Music track analyzed: BPM, key, energy curve, Camelot code.

4\. PULSE conductor creates score: for each scene --- camelot_key, scale, pendulum, energy, counterpoint flag.

5\. Energy critics evaluate proposed edit. Triangle calibration (McKee) adjusts weights per genre.

6\. New timeline created with full assembly. Agent activity visible on DAG (pulsing nodes).

7\. Story Space 3D shows trajectory in real-time during assembly.

8\. User reviews, adjusts in new timeline. Original untouched.

12.4 Professional manual edit

1\. All panels available. Script left, monitors right, timeline bottom --- classic NLE.

2\. Three-point editing: select in/out in source monitor, drop to timeline.

3\. PULSE runs passive analysis: BPM markers appear on timeline, Story Space updates.

4\. Inspector shows PULSE data for each clip but does NOT auto-edit.

5\. User can request PULSE suggestions: \'suggest next cut point\' → highlights sync points.

6\. At any point, user can fork to PULSE auto-montage → creates new timeline, original safe.

13\. Technical dependencies

  -------------------- ----------------------------------------- ------------------------------------------------------------------
  **Component**        **Technology**                            **Notes**

  Desktop shell        Tauri (Rust + WebView)                    Native menus, window management, file system access

  Frontend             React + TypeScript                        Panels as components, drag-dock via react-dnd or custom

  DAG visualization    ReactFlow (xyflow)                        Already used in MYCELIUM. Extend for timeline DAG mode

  3D Knowledge Graph   Three.js                                  Existing VETKA 3D. Story Space 3D reuses renderer

  Timeline             Custom canvas component                   HTML5 Canvas for performance. Not DOM-based tracks

  Video playback       HTML5 video + WebCodecs                   Frame-accurate seeking, timecode overlay

  PULSE backend        Python FastAPI (port 5001)                pulse_conductor, energy_critics, script_analyzer, camelot_engine

  JEPA runtime         Python + HTTP bridge (port 8099)          jepa_integrator, jepa_runtime, jepa_to_qdrant

  Audio analysis       librosa (Python) + WebAudio (frontend)    BPM, key, onset detection

  Transcription        Whisper (local or API)                    Auto-transcript for documentary workflow

  Scene detection      FFmpeg + V-JEPA2                          Scene cuts, visual BPM extraction

  Export               FCP XML (xmeml v4) + EDL + SRT            adobe-xml-converter skill already exists

  Storage              Qdrant (vectors) + JSON (project state)   vetka_media_embeddings collection for JEPA similarity
  -------------------- ----------------------------------------- ------------------------------------------------------------------

14\. Summary for Coder

Seven panels. Two monitors (fixed). Five switchable panels with DAG mode. Layout like FCP 7: everything detachable, resizable, dockable. Dark theme, custom SVG icons only.

Three BPM sources (audio green, video blue, script white) converge as orange strong-beat markers. PULSE auto-edits always create new timeline --- never overwrite. Favorites as SRT. Standard markers as Premiere XML.

DAG project = Y-time (vertical). DAG timeline = X-time (horizontal). Same model, different projections. Story Space 3D = vectorscope (analytical, not working surface).

Script is the spine. Material links to script. Timeline is the result. PULSE is the conductor. JEPA is the perception. Critics evaluate. McKee triangle calibrates.

**Build order: Script panel + Timeline + Monitors (MVP). Then DAG project. Then PULSE integration. Then Story Space. Then Effects nodes.**
