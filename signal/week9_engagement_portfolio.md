# Signal Corps Week 9 Engagement Portfolio — Oracle Forge Final Submission

_For final submission Sat 2026-04-18, 20:00 UTC._
_Compiled 2026-04-18 by Kirubel Tewodros (Signal Corps, with Meseret Bolled)._

---

## Summary

Week 9 closed out the Oracle Forge external-engagement program with a deliberate shift from announcement-style broadcasts (Week 8 learning) to **substantive reply-threading, problem-class posts, and multi-round technical debate** under the accounts of practitioners adjacent to our problem space. The content thesis was constant across the week: every external post maps to a shipped failure mode in the team repo (`agent/`, `utils/`, `kb/corrections/`), and external validation is tracked by name, not by vanity metric.

We deliberately did **not** externalize benchmark pass@1 numbers. The team's internal self-constructed PG+Mongo suite (`eval/dab_pg_mongo_queries.json`) is 54 queries but only 6 unique paraphrases × 9; reporting a score against it would have been trivially disprovable. Saturday's real DataAgentBench run (`eval/results.json`, 2026-04-18T06:57 UTC, 2 yelp queries, pass@1 = 0.0) reinforced that the right story for the external channel is *problem classes*, not scores.

---

## Published Content — Week 9 (Apr 13 → Apr 18)

### Medium Articles (2 delivered — Kirubel)
| Date | Title | Link | Words |
|------|-------|------|-------|
| 2026-04-14 | Why Your AI Data Agent Silently Fails on Cross Database Queries (And You Don't Even Notice) | [medium.com](https://medium.com/@kirutew17654321) | 600+ |
| 2026-04-15 | Tested 21 Knowledge Base Documents on an 8B Model | [medium.com](https://medium.com/@kirutew17654321) | 600+ |

### LinkedIn (2 delivered — one each)
| Date | Author | Content |
|------|--------|---------|
| 2026-04-11 | Meseret | "The Silent Killer of AI Data Agents (And How We're Engineering Around It)" |
| Apr 14-15 | Meseret | "Testing 21 knowledge base documents on a small model revealed what needed fixing." |

### X — Reply-threaded placements + main-account broadcasts
- **Apr 13:** 5 reply-placements under larger accounts (@shipp_ai, @_avichawla, @himanshustwts, @sh_reya, @ashpreetbedi). **@matanzutta returned a verbatim thesis-restatement of the Domain Knowledge angle** — highest-signal external validation of the portfolio.
- **Apr 14:** 8 posts across 4 X Communities (AI Agents 14.7K, ML, AI/Python/Data, Open Source Contributors). 2 received practitioner replies (@jcubic, @anandrishv).
- **Apr 18 (post-midnight UTC):** 5 broadcasts from @kirubeltewodro2 covering architecture-gap framing + paraphrase-failure framing. (Reach not yet programmatically verified — X blocks scrapers.)

### Reddit — Posts & sustained multi-round threads (Week 9)

| Thread | Subreddit | Status | Engagement |
|---|---|---|---|
| [Cross database join keys are a silent failure mode](https://www.reddit.com/r/SQL/comments/1smzvar/) | r/SQL | Live | **22 comments, 5-round debate with u/B1zmark** ending in his one-line concede ("Cool, then do it :p"); also u/Wise-Jury-4037 substantive 3-round, u/Eleventhousand, u/Imaginary__Bar, u/SaintTimothy |
| [Why a model can look good on a quick test and still fail under repeated trials](https://www.reddit.com/r/learnmachinelearning/comments/1smzrav/) | r/learnmachinelearning | Live | **8 comments, 4-round with u/NarutoLLN** on Bayesian benchmarking + executable-correctness metrics; u/Soft_Cress_8870 cross-domain validation |
| [Our multi DB agent answered "how many customers" right and "count customers" wrong — why](https://www.reddit.com/r/SQL/comments/1soeoq5/) | r/SQL | Live (fresh) | 2 comments — u/trollied substantive pragmatic pushback ("write the SQL yourself") + our firm redirect (`ogva5a9`): conceded the kernel, reframed failure as router mis-dispatch vs LLM non-determinism |
| [Why would an agent answer the same question right with one wording and wrong with a paraphrase?](https://www.reddit.com/r/learnmachinelearning/comments/1so6rwb/) | r/learnmachinelearning | Live (fresh) | 2 comments (u/pab_guy dismissive → firm reply from us) |
| [Your AI agent is matching words, not understanding questions](https://www.reddit.com/r/learnmachinelearning/comments/1sonxrg/) | r/learnmachinelearning | Live (fresh, Meseret) | 4 comments (u/Cybyss substantive 2-round with Meseret; u/GraciousMule dismissive) |
| [Stop dumping docs into RAG and praying](https://www.reddit.com/r/LocalLLaMA/comments/1sm4s0y/) | r/LocalLLaMA | Live | Apr 15 deployment — baseline KB-compression argument |
| **[Your model might not be the problem, 13 KB docs might be](https://www.reddit.com/r/LocalLLaMA/comments/1sn19cl/)** | r/LocalLLaMA | **Post body removed by moderator** | 7 external comments remain visible including u/Corporate_Drone31 (3-round), u/AutomataManifold ("Evaluating your results is a superpower"); post reach excluded from totals |
| Earlier (Week 8 carry-over) | r/learnmachinelearning + r/LocalLLaMA | Live | DAB failure modes + KB injection 8B testing threads |

### Discord (substantive — not announcement)
| Server | Focus | Status |
|---|---|---|
| Hugging Face (`#general`) | KB injection + cross-DB joins | **5-message exchange with user H$Go (~57 min, Apr 14)** — H$Go independently arrived at "fuzzy AI matching" pattern = our Correction Layer. Externally-discovered convergence. Apr 18 follow-up deployed. |
| EleutherAI | Evaluation methodology | Apr 18 substantive message deployed |
| LlamaIndex | Multi-DB routing | Apr 18 substantive message deployed |
| Cohort Discord | First-mover help | 1+ intervention — DAB setup + practitioner-manual triage |

---

## Notable External Validation (evidence-linked, named)

### 1. @matanzutta — X, 2026-04-13 (highest-signal)
Non-coordinated practitioner restated our Domain Knowledge thesis verbatim in response to a reply-thread under @ashpreetbedi's Dash v2 post. Confirms the framing transfers outside the cohort. [Tweet.](https://x.com/matanzutta/status/2043620994544239077)

### 2. u/NarutoLLN — r/learnmachinelearning, 2026-04-16 → 17 (4-round technical)
Pushed repeatedly on pass@1 sampling → Bayesian benchmarking → LLM-as-judge vs executable correctness. We held the argument ground in executable-correctness territory; NarutoLLN upvoted the rebuttal (`ogp11mv` +2). Active practitioner-grade conversation, not a one-liner exchange.

### 3. u/This-You-2737 — r/learnmachinelearning, 2026-04-14
Recommended Great Expectations + Scaylor Orchestrate for join-failure tooling. Substantive tooling exchange.

### 4. u/Corporate_Drone31 — r/LocalLLaMA (before moderator removal), 2026-04-16 → 17
*"That's a very TDD approach to engineering LLM agents. I like it."* 3-round exchange on 8B batch workflows and staged extract → normalize → validate → answer patterns.

### 5. u/AutomataManifold — r/LocalLLaMA (before moderator removal)
*"Evaluating your results is a superpower. A sadly underrated superpower."* — single-line but quotable.

### 6. H$Go — Hugging Face Discord, 2026-04-14
Independently arrived at "fuzzy AI matching" framing that maps directly onto our Correction Layer. External convergence without push from us.

### 7. u/B1zmark — r/SQL, 2026-04-16 → 17 (contested, resolved)
5-round debate; pushed hard on "fuzzy matching is the only option for cross-store joins." We rebutted by distinguishing deterministic format-rule normalization (`f"CUST-{id}"`) from fuzzy matching, cited PG-INT → Mongo-CUST-string as a named correction pattern (14/14 Telecom + Healthcare). B1zmark's final word was `"Cool, then do it :p"` — effectively concedes substance. Thread resting.

### 8. u/Cybyss — r/learnmachinelearning, 2026-04-18 (Meseret companion post)
Substantive practitioner engagement; follow-up conceded *"the whole field of agentic development is such a wild west."*

---

## Honest Flags for Submission Review

1. **r/LocalLLaMA `1sn19cl` post body removed by moderator.** 7 inbound comments remain auditable. Post reach excluded from Week 9 totals.
2. **Small-account broadcast limit acknowledged.** Main-account X broadcasts (@kirubeltewodro2) continue to underperform reply-threaded placements. We continue to broadcast for link-equity but do not count it as primary engagement signal.
3. **Benchmark pass@1 intentionally not externalized.** The team's self-constructed 54-query PG+Mongo suite is 6 paraphrases × 9, so an internally-reported 1.0 on that suite would be trivially disprovable. Saturday's honest 2-query DAB run returned pass@1=0.0. We did not post either number externally.
4. **u/trollied inbound on `1soeoq5` handled.** Substantive pragmatic pushback ("write the SQL yourself") → firm reply `ogva5a9` (2026-04-18 09:26 UTC) conceded the kernel and reframed the failure as symbolic-router mis-dispatch, not LLM non-determinism.
5. **B1zmark thread ended with snark, not capitulation.** We do not frame `"Cool, then do it :p"` as a "win" externally; logged as "concedes substance, thread resting."
6. **X + Discord reach for Apr 18 posts not programmatically verified.** Both platforms block scrapers without auth; manual verification owed for final metrics.

---

## Intelligence Impact on Team Build (Week 9)

| Source | Insight | How the team used it |
|---|---|---|
| u/NarutoLLN (r/lML) | Bayesian benchmarking + executable-correctness as primary reliability signal | Confirmed the team's pivot away from unsupported pass@1 claims; aligned with Saturday's honest eval run posting `pass@1=0.0` on 2 yelp queries rather than reporting the fabricated 1.0. |
| H$Go (HF Discord) | Independent "fuzzy AI matching" convergence | Reinforced that the Correction Layer pattern is not idiosyncratic — it's a community-discovered pattern we happen to have implemented. |
| u/B1zmark (r/SQL) | Strict-schema-or-fail pushback | Sharpened our framing of deterministic vs heuristic normalization in `utils/` (`routing_policy.py`, `schema_bundle.py`) — useful specifically in Gemechis's Apr 18 architecture overhaul. |
| Karpathy wiki/markdown thesis | Structured docs > raw prose for retrieval | Direct input to Mikias's 21/21 KB injection test outcome; carried into `kb/domain/` table-first format. |
| u/matt-k-wong (r/LocalLLaMA, Week 8) | Structured docs transfer model-size-agnostically | Validated `kb/domain/` table + Q&A format choice kept through Week 9. |

---

## Resource Acquisition Status (Week 9)

| Resource | Status | Notes |
|---|---|---|
| OpenRouter API credits | **Active** — Apr 18 repo audit confirms `OpenRouterRoutingReasoner` is the only routing path (no Groq fallback, raises `LLMRoutingFailed` on miss) | Credits held through submission window |
| Cloudflare Workers | Not requested | No deployment surface in scope for final submission |
| Compute for SQLite/DuckDB eval | Partial | 2-query DAB run completed Apr 18 on yelp; full 54-query + multi-DB scope-out is post-submission |

---

## Repo Contributions (Kirubel, Week 9)

- `signal/engagement_log.md` — continuous Week 9 updates: Apr 14 burst (8 X community posts, 6 Reddit replies, HF Discord), Apr 15 Medium B + Reddit r/LocalLLaMA deployment, Apr 16–17 multi-round Reddit debates (B1zmark, NarutoLLN, Wise-Jury-4037, Corporate_Drone31, SaintTimothy), Apr 18 new posts (1soeoq5, 1so6rwb) and inbound (pab_guy, trollied, Meseret's 1sonxrg companion).
- `signal/community_participation_log.md` — mirrored all above with intelligence framing.
- `signal/resource_acquisition.md` — Week 9 updates for interim (OpenRouter + compute state).
- `signal/week8_engagement_portfolio.md` — interim-submission artifact (Apr 14).
- `signal/week9_engagement_portfolio.md` — this file (final-submission artifact).

---

## Week 9 Deliverable Checklist vs Spec

| Deliverable | Spec Requirement | Status |
|---|---|---|
| X threads (min 2/week) | 2+ per week | ✅ **5 reply-placements Apr 13 + 8 X Community posts Apr 14 + 5 broadcasts Apr 18** (13+ total Week 9) |
| LinkedIn/Medium article | 1 per SC member, 600+ words | ✅ Kirubel 2/2 Medium (Apr 14, Apr 15); Meseret 2/2 LinkedIn (Apr 11, Apr 14-15) |
| Daily Slack posts | 4-bullet team status | ✅ Apr 13–18 covered; team-wide framing (Drivers + IOs + SC) |
| Community participation log | Daily updated, evidence-linked | ✅ Current through Apr 18 (this commit) |
| Resource acquisition report | Ongoing | ✅ Current |
| Reddit/Discord substantive comments | Minimum 1 | ✅ **8 Reddit threads with inbound engagement + 3 Discord servers active + 1 cohort Discord first-mover help** |
| External engagement summary | End of Week 9 | ✅ This file |

---

## Post-Submission Verification Owed

- Manual X engagement check for Apr 18 @kirubeltewodro2 broadcasts (5 tweets)
- Manual Discord reply check across HF / EleutherAI / LlamaIndex posts
- Final reach tally to be appended to this file once auth-blocked platforms are reviewed

---
_End of Week 9 Engagement Portfolio._
