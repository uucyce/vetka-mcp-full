# Group Chat Flow Diagram

## Complete Message Flow with OpenRouter Integration

```mermaid
graph TD
    A["Socket.IO: group_message"] -->|Line 529| B["Parse Message"]
    B -->|541-550| C["Extract: group_id, sender_id, content, @mentions"]

    C -->|600-614| D{"Check @mentions"}
    D -->|MCP agents| E["notify_mcp_agents()"]
    E -->|emit mcp_mention| F["Browser/Claude Code extensions"]
    D -->|Group agents| G["Continue routing"]

    G -->|Line 665| H["select_responding_agents()"]

    H -->|Line 201-214| I{"Reply routing?"}
    I -->|Yes| J["Route to original agent"]
    I -->|No| K{"@mentions?"}

    K -->|Yes| L["Select mentioned agents"]
    K -->|No| M{"Smart reply decay?"}

    M -->|Yes, decay < 1| N["Use last_responder"]
    M -->|No| O["SMART keyword selection"]

    O -->|PM keywords| P["Select PM"]
    O -->|Dev keywords| Q["Select Dev"]
    O -->|QA keywords| R["Select QA"]
    O -->|Architect keywords| S["Select Architect"]

    J --> T["Get participant data"]
    L --> T
    N --> T
    P --> T
    Q --> T
    R --> T
    S --> T

    T -->|Line 716-717| U["Extract model_id, role"]
    U -->|Line 721-737| V["Map Role → AgentType"]

    V -->|MARKER_94.6| W["PM→'PM', Dev→'Dev'<br/>QA→'QA', Architect→'Architect'"]

    W -->|Line 800-810| X["call_agent()"]
    X -->|agent_type, model_id, prompt| Y["orchestrator.call_agent()"]

    Y -->|Line 2242-2331| Z["Validate agent_type"]
    Z -->|Line 2300-2305| AA["Check manual model override"]

    AA -->|Override exists| AB["Set model_routing manual"]
    AA -->|No override| AC["Use auto routing"]

    AB --> AD["_run_agent_with_elisya_async()"]
    AC --> AD

    AD -->|Line 1215| AE["Reframe context with Elisya"]
    AE -->|Line 1235-1257| AF{"Manual override?"}

    AF -->|Yes| AG["ProviderRegistry.detect_provider()"]
    AF -->|No| AH["_get_routing_for_task()"]

    AG -->|Line 1244| AI["Detect provider from model_id"]
    AH --> AJ["Get auto routing"]

    AI -->|Check result| AK{"Provider is XAI?"}
    AK -->|Yes| AL["Check APIKeyService.get_key('xai')"]
    AK -->|No| AM["Use detected provider"]

    AL -->|Key exists| AN["Use XAI provider"]
    AL -->|Key missing| AO["Fallback to OpenRouter"]

    AN --> AP["Inject API key to environment"]
    AJ --> AP
    AM --> AP
    AO --> AP

    AP -->|Line 1023| AQ["call_model_v2()"]
    AQ -->|model, provider, tools| AR["LLM Call"]

    AR -->|Success| AS["Response received"]
    AR -->|XaiKeysExhausted| AT["Catch exception"]
    AR -->|404/429/quota| AU["Catch exception"]

    AT -->|Line 1026-1037| AV["Retry with OpenRouter"]
    AU -->|Line 1038-1050| AW["Retry with OpenRouter"]

    AV -->|Convert model| AX["'grok-2' → 'x-ai/grok-2'"]
    AW --> AX

    AX -->|provider=OPENROUTER| AY["call_model_v2 retry"]
    AY -->|tools=None| AZ["LLM Call (fallback)"]

    AZ -->|Response received| AS

    AS -->|Line 833| BA["Store in group_chat_manager"]
    BA -->|Line 842-860| BB["Emit group_stream_end"]
    BB -->|Socket.IO| BC["Frontend receives response"]

    style A fill:#e1f5ff
    style X fill:#fff3e0
    style AD fill:#f3e5f5
    style AQ fill:#e8f5e9
    style AV fill:#fce4ec
    style BC fill:#e1f5ff
```

---

## Provider Detection Logic

```mermaid
graph LR
    A["model_id<br/>e.g. 'openai/gpt-4'"] -->|ProviderRegistry.detect_provider| B{"Parse model_id"}

    B -->|"openai/*"| C["Provider.OPENAI"]
    B -->|"gpt-*"| C
    B -->|"anthropic/*"| D["Provider.ANTHROPIC"]
    B -->|"claude-*"| D
    B -->|"google/*"| E["Provider.GOOGLE"]
    B -->|"gemini/*"| E
    B -->|"ollama/*"| F["Provider.OLLAMA"]
    B -->|"x-ai/*"| G["Provider.XAI"]
    B -->|"grok-*"| G
    B -->|"openrouter/*"| H["Provider.OPENROUTER"]
    B -->|"default"| H

    C --> I["Detected Provider"]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I

    I -->|Check XAI| J{"provider == 'xai'?"}
    J -->|Yes| K{"Has XAI key?"}
    K -->|No| L["Use OPENROUTER"]
    K -->|Yes| M["Use XAI"]
    J -->|No| N["Use detected provider"]

    L --> O["Final Provider"]
    M --> O
    N --> O

    style A fill:#e3f2fd
    style I fill:#fff9c4
    style O fill:#c8e6c9
```

---

## Fallback Trigger Tree

```mermaid
graph TD
    A["call_model_v2()"] -->|Success| B["Response received"]
    A -->|Exception| C{"Exception type?"}

    C -->|XaiKeysExhausted| D["All XAI keys exhausted"]
    C -->|error string contains| E{"Pattern match?"}

    E -->|'429'| F["Rate limit"]
    E -->|'404'| G["Model not found"]
    E -->|'quota'| H["Quota exceeded"]
    E -->|'rate limit'| F
    E -->|No match| I["Other error"]

    D --> J["FALLBACK: OpenRouter"]
    F --> J
    G --> J
    H --> J
    I --> K["Re-raise exception"]

    J -->|Line 1030-1037| L["Convert model:<br/>grok-2 → x-ai/grok-2"]
    L -->|provider=OPENROUTER| M["call_model_v2 retry"]
    M -->|tools=None| N["Retry call"]

    N -->|Success| B
    N -->|Failure| K

    K -->|Line 957| O["Emit error event"]
    O -->|Socket.IO| P["Frontend error"]

    B -->|Line 843| Q["Emit group_stream_end"]
    Q -->|Socket.IO| R["Frontend success"]

    style A fill:#e0f2f1
    style J fill:#ffebee
    style B fill:#c8e6c9
    style R fill:#c8e6c9
    style K fill:#ffccbc
    style P fill:#ffccbc
```

---

## Parallel Dev+QA Execution

```mermaid
graph TD
    A["participants_to_respond<br/>includes Dev, QA"] -->|Line 700| B["While loop: max 10 agents"]

    B -->|First iteration| C["Dev is first in queue"]
    C -->|Line 800-810| D["call_agent(Dev, ...)"]
    D -->|await _run_agent_with_elisya_async| E["Dev execution"]
    E -->|Provider detection| F["Get Dev's provider"]
    F -->|call_model_v2| G["Dev LLM call"]

    G -->|Check response| H["Parse Dev output"]
    H -->|Line 829| I["Store in previous_outputs"]
    I -->|Line 899-954| J{"Check @mentions in Dev response"}

    J -->|@QA mentioned| K["Add QA to queue<br/>Line 951"]
    J -->|No mentions| L["Continue with next agent"]

    B -->|Second iteration| M["Process next agent"]
    M -->|Could be QA from mention| N{"QA in queue?"}

    N -->|Yes| O["call_agent(QA, ...)"]
    N -->|No| P["End of queue"]

    O -->|await _run_agent_with_elisya_async| Q["QA execution"]

    Q -->|Parallel: Both run if<br/>both in queue| R["Can overlap with Dev<br/>if managed correctly"]

    G -->|Completes| H2["Dev done"]
    Q -->|Completes| I2["QA done"]

    H2 --> S["Dev output in previous_outputs"]
    I2 --> T["QA output in previous_outputs"]

    S --> U["Chain context for next agent<br/>Line 775-779"]
    T --> U

    U --> V["Response sent to group<br/>Line 842-860"]

    style A fill:#e1f5fe
    style K fill:#fff9c4
    style R fill:#ffe0b2
    style V fill:#c8e6c9
```

---

## Role Selection Priority

```mermaid
graph TD
    A["User message received"] --> B["select_responding_agents()"]

    B -->|1. reply_to_id?| C{"Is reply to agent?"}
    C -->|Yes| D["Route to original agent<br/>Line 201-214"]
    C -->|No| E["Continue to next check"]

    E -->|2. @mentions?| F{"Any @mentions?"}
    F -->|Yes| G["Match against participants<br/>Line 221-260"]
    G -->|Found| H["Return mentioned agents"]
    G -->|Not found| I["Return empty<br/>Phase 80.27"]

    F -->|No| J["Continue to next check"]

    J -->|3. Smart reply decay?<br/>Phase 80.28| K{"is_agent_sender?<br/>decay < 2?"}
    K -->|Yes| L["Return last_responder"]
    K -->|No| M["Continue to next check"]

    M -->|4. Commands?| N{"/solo /team /round?"}
    N -->|/solo| O["First non-observer agent"]
    N -->|/team| P["All non-observer agents"]
    N -->|/round| Q["Sorted by role order"]
    N -->|No| R["Continue to next check"]

    R -->|5. SMART keywords| S["Score message for keywords"]
    S -->|PM keywords| T["Select PM agents<br/>Line 322-326"]
    S -->|Dev keywords| U["Select Dev agents"]
    S -->|QA keywords| V["Select QA agents"]
    S -->|Architect keywords| W["Select Architect agents"]
    S -->|Scored| X["Return highest scorers"]
    S -->|No score| Y["Continue to default"]

    Y -->|6. Default| Z{"Participants?"}
    Z -->|Has admin| AA["Return admin<br/>Line 351"]
    Z -->|No admin| AB["Return first worker<br/>Line 353"]
    Z -->|Empty| AC["Return empty"]

    D --> AE["Response ready"]
    H --> AE
    I --> AE
    L --> AE
    O --> AE
    P --> AE
    Q --> AE
    X --> AE
    AA --> AE
    AB --> AE
    AC --> AE

    AE --> AF["Send to agents"]

    style B fill:#e3f2fd
    style D fill:#fff9c4
    style H fill:#c8e6c9
    style X fill:#ffe0b2
    style AA fill:#f8bbd0
```

---

## OpenRouter Integration Points

```mermaid
graph LR
    subgraph "Entry Layer"
        A["group_message_handler.py"]
    end

    subgraph "Routing Layer"
        B["group_chat_manager.py<br/>select_responding_agents()"]
    end

    subgraph "Orchestration Layer"
        C["orchestrator_with_elisya.py<br/>call_agent()"]
    end

    subgraph "Provider Detection"
        D["ProviderRegistry<br/>detect_provider()"]
    end

    subgraph "Execution Layer"
        E["call_model_v2()"]
    end

    subgraph "Fallback Layer"
        F["OpenRouter Fallback<br/>on XAI/404/429"]
    end

    A -->|Agent selection| B
    B -->|Agent dispatch| C
    C -->|Per-role detection| D
    D -->|Explicit provider| E
    E -->|Success| G["Response to group"]
    E -->|Exception| F
    F -->|Retry| E

    H["✅ OpenRouter at all layers"]

    style D fill:#fff176
    style E fill:#81c784
    style F fill:#ef5350
    style G fill:#64b5f6
```

---

## Phase 80.28: Smart Reply Decay

```mermaid
graph TD
    A["User sends message to group"] --> B{"last_responder_id<br/>set?"}

    B -->|No| C["Use standard selection<br/>keyword/command/default"]
    B -->|Yes| D{"decay < 1?"}

    D -->|Yes| E["Route to last_responder<br/>for conversation continuity<br/>Line 283-289"]
    D -->|No| F["Reset smart reply<br/>use standard selection"]

    E --> G["last_responder responds"]
    F --> H["Next agent selected<br/>by standard method"]

    G -->|Line 864| I["Agent sends response"]
    H --> I

    I --> J["Update group object:"]
    J -->|Line 864| K["last_responder_id = agent_id"]
    J -->|Line 865-866| L["last_responder_decay = 0<br/>RESET!"]

    L --> M["Next user message"]

    M -->|decay starts at 0| N{"User sends followup?"}
    N -->|Yes| O["decay += 1<br/>Line 592"]
    O --> P["decay = 1, so decay < 1 is false"]
    P --> Q["Standard selection triggers"]

    style E fill:#fff9c4
    style K fill:#c8e6c9
    style L fill:#c8e6c9
    style Q fill:#ffccbc
```
