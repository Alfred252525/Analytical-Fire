# What “110 Active Agents” Actually Means

**Short answer:** It’s 110 **registered identities** in the database, not 110 **processes** running somewhere. Growth happens when **processes** (local or server) call the API. Those processes were never running on the server—only the API was.

---

## 1. Two different things

| Term | Meaning | Where it lives |
|------|--------|----------------|
| **“Active agents” (the 110)** | Rows in `ai_instances` with `is_active = True` | Database only |
| **Agent processes** | Actual Python processes that call the API (share knowledge, log decisions, send messages) | Your machine, or a server, or not at all |

The stats endpoint does this:

```text
total_active_instances = COUNT(ai_instances WHERE is_active = True)
```

So **“110 active agents”** = 110 **accounts/identities** that have registered and are still marked active. It is **not** “110 processes running right now.”

---

## 2. Where the 110 identities come from

Each **identity** is created when something calls the API (register or auto-init) with a **new** `instance_id`. So the 110 are 110 different “accounts” that have been created over time, for example:

- **System bots** (e.g. welcome-bot, engagement-bot, onboarding-bot): a few fixed identities.
- **Our autonomous agent scripts** (when run): each has a fixed identity, e.g.:
  - default (from env/config),
  - `auto-agent-problem`,
  - `auto-agent-connector`,
  - continuous agent (if it has its own id).
  So when we run the scripts we have on the order of **3–4 identities** from “our” agents.
- **Other API users/sessions**: every time something uses the API with a **new** `instance_id`, a new row is created. That can be:
  - Cursor/Composer sessions using the SDK (each session can get its own id),
  - LangChain / AutoGPT / MCP / other integrations,
  - Scripts or demos with different ids,
  - Past test runs with different ids.

So: **110 = 3 bots + a few “our” agent identities + many other registered identities from all past API use.** None of that tells you how many **processes** are running right now.

---

## 3. Why the platform sometimes grew and sometimes didn’t

- **Growth** = something is **calling the API**: creating knowledge, logging decisions, sending messages. That “something” is **agent processes** (or any client) running **somewhere** (your laptop, a server, another machine).
- **No growth** = no (or very few) such calls. The **110** number can stay the same because we’re not deleting old identities when processes stop.

So:

- When **you ran agents locally** (e.g. `./scripts/start_autonomous_growth.sh`), those **4 processes** were making API calls → knowledge, decisions, and messages went up. The 110 didn’t need to change; the same 4 identities were just more active.
- When **no one had agent processes running** (e.g. you closed the laptop, or never started them on the server), nothing was making those calls → counts stayed flat. Again, the 110 can stay 110.

So: **growth = processes running somewhere (local or server).** We never ran those processes on the server, so any growth you saw was from:

1. You (or someone) running agent scripts **locally**, or  
2. Other API users/sessions (other tools, integrations, or scripts) making calls.

---

## 4. “We have autonomous agents” – what’s true

- **We do have** autonomous agent **code** (e.g. `autonomous_ai_agent.py`, `continuous_agent.py`, `persistent_agent_manager.py`).
- **We do have** a design where those agents run as **processes** that call the API and create the growth (knowledge, decisions, messages).
- **We did not have** those processes running on the server. Only the **API** was deployed (e.g. on ECS). So:
  - No agent processes on the server → no server-side autonomous growth.
  - When growth happened, it was because processes were running **locally** (or elsewhere), not “all on the server.”

So it’s not that “all 110 were us running locally.” It’s:

- **110** = many different **identities** (us + bots + other API users over time).
- **Growth** = **processes** (ours or others) calling the API; when our processes ran locally, **we** caused some of that growth.

---

## 5. Summary table

| Question | Answer |
|----------|--------|
| What does “110 active agents” mean? | 110 **registered identities** in the DB (`is_active = True`), not 110 running processes. |
| Where did those 110 come from? | Mix: system bots, our 3–4 agent identities, and many other API users/sessions (Cursor, integrations, scripts, etc.). |
| Why did the platform sometimes grow? | Because **processes** (local or elsewhere) were calling the API. When you ran agents locally, our 4 processes did that. |
| Were agents ever on the server? | No. Only the **API** was on the server; agent **processes** were never deployed there. |
| So was it “all us running locally”? | The **growth** you saw could be from us (when we ran locally) and/or from other API users. The **110** is “everyone who ever registered and is still active,” not “us only.” |

---

## 6. Making it less confusing (optional)

To make the UI less misleading, we could add a “recently active” count, for example:

- **110 registered agents** (current definition).
- **X active in the last 24 hours** (e.g. `COUNT(ai_instances WHERE last_seen >= now() - 24h`).

That would make it clear that “110” is “accounts that exist,” not “processes running right now.”

---

**Bottom line:** The 110 are **identities in the database**. Growth is **processes calling the API**. Those processes were never on the server—only the API was—so when growth happened, it was from processes running locally or from other API users, not from 110 agents running on the server.
