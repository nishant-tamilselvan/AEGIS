---
# Generated from aegis/skills/writing-style/SKILL.md by scripts/sync_platforms.py. Edit the source, not this file.
name: writing-style
description: 'Enforceable writing style guide for prose deliverables, backed by a 249-rule machine-readable rule file and a checker script. Use when writing or reviewing any document, report, business case, architecture artifact, briefing note, README, documentation page, user guide, training material, commit message, or PR description. Strips the constructions that make writing sound machine-generated: "not X, but Y" phrasing, em dashes, banned vocabulary, dead metaphors, sycophantic openers, listicle headings, personified abstractions, and rhetorical filler. Also use when the user asks to review, tighten, de-slop, or check the tone of existing text. Load it before drafting the first sentence, then run the checker before delivery.'
argument-hint: 'e.g. "check the executive briefing" or "de-slop this section"'
---

# Writing Style

Two things make up this skill. `references/banned.json` holds the word, phrase, and structure patterns, and it is the single source of truth for them. This file holds the judgment rules that a regular expression cannot express, plus the reviewer's checklist.

## Core Principle

Write in plain declarative language. Make a claim. Move on. Trust the reader to follow without rhetorical scaffolding.

If a sentence works only because of its rhythm, its symmetry, or the way it sounds when read aloud, it is the wrong sentence. Replace it with one that works because of what it says.

## Clarity for a mixed audience

Write so a thoughtful person who is not a specialist can follow it on the first read. Most readers are not engineers. Clear, friendly, explanatory sentences beat dense, impressive ones every time. These rules bind as tightly as the hard rules below. Density is its own kind of slop.

**One idea per sentence.** A sentence carries one point. If you are joining separate ideas, or a list of things, with commas, split it. A sentence the reader has to read twice has failed, however correct it is.

**Never cram a list into a sentence.** Three items is the most a sentence should hold. A longer list belongs in a table or a bulleted list. Do not stack the fields a tool records, the steps in a process, or the parts of a system inside one sentence as a wall of commas. Keep enumerations complete, and keep them in tables and lists.

**Lead with the plain point, then explain.** Open a paragraph with the simple thing you are saying, in ordinary words, and then explain it. Avoid abstract openers that personify the work or stall before the point. Name who does what instead.

**Short to medium, and varied.** Default to short and medium sentences. A long sentence is allowed when it develops one easy-to-follow thought. It is wrong when it stacks separate items or clauses. Read it aloud. If you run out of breath or lose the thread, split it.

**Explain the jargon or drop it.** The first time a technical term appears, give it in plain words. If a sentence only lands for a specialist, rewrite it so everyone else can follow.

**Be direct and friendly.** Address the reader and name the actor: "we," "our," "the tool," "you." Concrete nouns and real examples carry more than an abstract summary.

**The test.** Imagine handing the paragraph to a smart colleague outside technology. If it reads as white noise, or they cannot say back what it means, it is not finished, no matter how accurate or complete it is.

## The rule file

`references/banned.json` carries 249 patterns in seven groups. Read `_comment` at the top before editing it. Every rule there was tested against real documents, and a rule that flags correct writing does more harm than the slop it catches.

| Group | Count | What it holds |
| --- | --- | --- |
| `words_error` | 39 | Words that are always slop |
| `words_warn` | 74 | Words that depend on context |
| `phrases_error` | 62 | Filler, dead metaphors, signposts, wordy constructions |
| `phrases_warn` | 34 | Marketing tics, personified abstractions, jargon |
| `openers_error` | 4 | Sycophantic first lines |
| `structures_error` | 19 | Sentence and heading shapes that are always slop |
| `structures_warn` | 17 | Shapes that usually signal a rewrite |

Each rule carries a severity. An `error` is always slop, so fix it. A `warn` depends on context, so a person decides: keep the word when it carries real meaning, replace it when it is filler.

Do not restate the lists in a document or a prompt. Point at the file so the rules stay in one place.

## Numeric limits

The `limits` block sets thresholds the checker measures.

| Limit | Value | Meaning |
| --- | --- | --- |
| `em_dash_max` | 1 | At most one em dash or en dash per document. The prose rule below is stricter: aim for zero. |
| `sentence_words_warn` | 30 | A sentence of 30 words or more gets a warning |
| `sentence_words_error` | 40 | A sentence of 40 words or more fails |
| `cadence_min_sentences` | 8 | Cadence is measured only once a document has 8 sentences |
| `cadence_cv_floor` | 0.28 | Sentence lengths must vary. Below this the writing reads as flat. |
| `personification_per_1k` | 2.5 | At most 2.5 personified abstractions per thousand words |

## Hard Rules

<!-- sloplint-disable -->

### 1. No "this is not A, but B" constructions

This is the highest priority rule. The pattern is the single most reliable signal of machine-generated prose. It appears in many forms and all of them are forbidden.

Forbidden patterns:

- "This is not X. It is Y."
- "Not just X, but Y."
- "Not only X, but also Y."
- "X is not the goal. Y is."
- "This is more than X. It is Y."
- "It is not A, it is B."
- "This is not about X, it's about Y."

The fix: state what the thing is. Drop the negated half entirely.

| Forbidden | Correct |
| --- | --- |
| "This is not a communications campaign in search of a story. It is a campaign required by operational reality." | "This communications strategy is required by operational reality." |
| "Visible progress is not a nice to have, it is a survival requirement." | "Visible progress is a survival requirement." |
| "This is not a new tool. It is a replacement." | "The tool replaces the current intake form." |
| "It is not just a marketing relationship, it is technical." | "The relationship is operational and technical." |

If a contrast genuinely matters, make the contrast carry real information and give each side a complete sentence. Do not use the negation as flourish.

### 2. No em dashes or long dashes

Use commas, periods, parentheses, or colons instead. If a sentence relies on an em dash, it is usually two sentences trying to be one. Split them. The checker permits one per document as a tolerance. Write for zero.

### 3. No rhetorical tetracolons or parallel "is the X" listings

A tetracolon is a four-part parallel structure used for rhythm. Machine prose is full of them. They sound polished and say very little.

Forbidden:

- "The blueprint is the foundation. The ADR is the guardrail. The work package is the engine. The evidence is the durable outcome."
- "It is the reference, the document reviewers cite, the basis for the training series, and the credential the team carries."

The fix: write the same content as ordinary sentences. Use a list only when the items are genuinely a list of comparable things.

### 4. No cinematic short-sentence flourishes

Two or three short declarative sentences in a row, used for dramatic effect, is a tic. It reads as a movie trailer voice-over.

Forbidden:

- "X is leading. Other Y are watching."
- "The window is open. The leverage is real. The plan uses both."
- "The work is good. The results are real. The position is earned."

The fix: combine into a single sentence with normal cadence. If the rhythm matters more than the content, the content was thin.

### 5. No "is the moment" or "is where" rhetorical anchors

Forbidden:

- "This is the moment X becomes globally visible."
- "This is where the strategy comes together."
- "This is where our platform comes in."
- "This is the technical authority piece."

The fix: describe what the step delivers. "Step four delivers the first global feature placement."

### 6. Banned vocabulary

`references/banned.json` holds the list. A representative sample of the `error` words: delve, pivotal, groundbreaking, cutting-edge, game-changing, transformative, seamless, multifaceted, holistic, tapestry, paradigm, synergy, effortless, unlock, crystallize, state-of-the-art, world-class, best-in-class, next-generation.

A sample of the `warn` words, which a person judges in context: robust, comprehensive, innovative, crucial, essential, vital, significant, leverage, harness, utilize, facilitate, foster, empower, navigate, journey, landscape, realm, ecosystem, streamlined, overarching, actually.

Banned sentence openers: Moreover, Furthermore, Additionally, In essence, At its core, Fundamentally, In today's world.

Phrases to delete: "it's worth noting", "when it comes to", "at the end of the day", "one of the most important", "plays a crucial role", "cannot be overstated", "sheds light on", "paves the way", "dives into", "stands as a testament".

Wordy constructions with a one-word replacement: "due to the fact that" becomes "because", "at this point in time" becomes "now", "in the event that" becomes "if", "for the purpose of testing" becomes "to test", "in order to" becomes "to", "prior to" becomes "before".

### 7. No three-item lists used as rhetorical flourish

The rule of three is overused. If three items genuinely apply, list them. If two items apply and a third is being invented to complete the rhythm, use two.

### 8. No participial sentence-end flourishes

Avoid sentences that close with a comma plus a participle phrase summarising what came before. They almost always restate what the sentence already said.

Forbidden: "X has built the only operational answer in Y, demonstrating its leadership."

Also forbidden is the benefit chain: "The service reads the receipt automatically, streamlining intake and empowering staff."

The fix: end the sentence at the period. If the second clause adds real information, write it as its own sentence. If it does not, delete it.

### 9. No "ensure" when a direct verb works

"Ensure" is a hedge. Most sentences using it work better with a direct verb.

| Hedged | Direct |
| --- | --- |
| "Ensure the whitepaper anchors the story." | "Anchor the story on the whitepaper." |
| "Ensure that visibility is maintained." | "Maintain visibility." |

The rule file carries "ensure" as a `warn`, so a person decides. Keep it where a
requirement genuinely obliges someone to guarantee a result. Replace it everywhere else.

### 10. No vague intensifiers

Strike very, really, truly, deeply, profoundly, incredibly, extremely, particularly, notably, importantly. If a claim needs an intensifier to land, the claim is weak. Strengthen the claim instead.

### 11. No decorations

Leave emojis, icons, and other decorators out of documentation, code, README files, and user interfaces unless the user asks for them. They are an obvious tell.

### 12. AI smell

Keep documentation, code, reference material, testing guides, and training material clear, legible, and free of repetition. Speak completely on a topic without padding it. Cut sycophancy, including compliments directed at the user or the user's intelligence.

### 13. No sycophantic openers

Never open a document, a section, or a reply with praise for the question or with an offer to help.

Forbidden: "Great question." "Excellent point." "Certainly." "I'd be happy to." "What a fascinating problem."

The fix: answer. The reader knows you are helping because you are helping.

### 14. Do not personify documents, processes, or abstractions

An abstraction cannot hold a line, earn a place, or answer to anyone. These constructions read as literary padding around a plain statement, and the checker caps them at 2.5 per thousand words.

| Forbidden | Correct |
| --- | --- |
| "The register keeps the estimate honest." | "The register records the source of every figure." |
| "This section earns its place." | "This section carries the reconciliation table." |
| "The policy holds the line on scope." | "The policy forbids scope changes without steering committee approval." |
| "Every document answers to the style guide." | "We check every document against the style guide." |
| "The audit queue exists to catch medium risk cases." | "The audit queue samples medium risk cases." |

The same rule applies to processes acting as people. "Delay past March costs a full release" needs an actor: "If the team approves the design after March, the build misses the next release."

### 15. No listicle, teaser, or stock headings

Headings name their content. They do not tease it, count it, or dramatise it.

| Forbidden | Correct |
| --- | --- |
| "Three Ways That Change Everything" | "Three options for the boundary check" |
| "What You Need to Know" | "Eligibility rules" |
| "Why It Matters" | "Effect on the release schedule" |
| "Why This, Why Now" | "Timing of the next release" |
| "The Data, Explained" | "How the operations data was checked" |
| "Faster Intake, Cheaper Processing" | "Intake time and processing cost" |

### 16. No dead metaphors or metaphoric announcements

Forbidden: low-hanging fruit, move the needle, drive impact, connect the dots, the tip of the iceberg, raise the bar, double down, table stakes, boil the ocean, single pane of glass, north star, the last mile, front and centre, a force multiplier, tee up, mutually reinforcing.

Also forbidden is announcing significance instead of stating a fact: "this marks a new era", "a step change", "a turning point", "an inflection point", "sets the stage for", "opens the door to", "the first of its kind", "unlocks value".

The fix: say what changed and by how much.

### 17. No vague references or empty hedges

Forbidden: going forward, moving forward, in due course, as appropriate, where appropriate, at this stage, at this time, at this juncture, this workstream, this piece of work, this decision point.

The fix: name the date, the owner, or the condition. "From the next fiscal year" rather than "going forward". "Once the data sharing agreement is signed" rather than "in due course".

### 18. No canned conclusions or expletive openings

Do not close a section with "In conclusion", "In summary", "Ultimately", or "Overall". The reader has just read it.

Do not open a sentence with "There are several factors that" or "It is important to". Name the subject and give it a verb.

### 19. No bold-label bullets

A bullet that opens with a bold label and a colon is a formatting tic. Use a table when you have label and value pairs, and use prose when the items are not really a list.

Forbidden shape: a bullet beginning with a bold phrase followed by a colon, then the explanation.

The fix: a two-column table, or a bold label ending in a period, or plain sentences.

### 20. No unnamed appeals to evidence

"Research shows", "studies suggest", "the data indicates", and "evidence proves" all hide the source. Name it, or drop the claim. In a business case, cite the file and the figure.

<!-- sloplint-enable -->

## Voice and Cadence

**Default sentence length is medium.** Mix short and long. Avoid long runs of sentences of the same length. The checker measures this as a coefficient of variation and wants at least 0.28.

**Use the active voice.** "The team publishes the briefing" rather than "The briefing is published by the team."

**Name the actor.** Avoid agentless constructions where it matters who is doing the thing. A sentence that ends in a passive participle usually hides the actor.

**Use specific nouns and verbs.** Write "two contractor roles moved to the platform team" rather than a vague phrase about resources redirected toward an initiative.

**Numbers are concrete.** Use them when they are real. Round when rounding is honest. Do not use numbers as decoration.

**Trust the reader.** Do not over-explain implications. Do not foreshadow and do not recap.

## Structure

**Headings describe content, they do not signal importance.** "The Asks" rather than "Critical Strategic Asks."

**Bullets are for genuine lists.** Comparable items, parallel grammatical form, two or more entries that share a category. If the items are not a list, use prose.

**One idea per paragraph.** Open with the claim. Support it. Stop.

**End sections at the period.** Do not add a closing flourish that summarises the section.

## What this covers in AEGIS

Every document a person reads:

- the six business artifacts and the five technical ones under `docs/artifacts/<app>/`
- the ADRs under `architecture-decisions/`
- the `WP-*` work packages and their evidence notes
- the harness documentation, including this file
- commit messages and pull request descriptions

The executive briefing is the hardest case and the one that matters most. An executive
sponsor reads it rather than an engineer. Apply the mixed-audience rules above before the
hard rules.

Identifiers, template structure and cited `ENT-STD-*` standards count as content rather
than prose. Template structure means the section headings, the bold field labels and the
fixed wording that every artifact shares. Do not reword an id, a template element, or a
quoted standard to satisfy a style rule. Where the template and a rule disagree, the
template wins, and the fix belongs in the template rather than in one document.

Every template passes the checker, and a test keeps it that way. Artifacts scaffolded
before the templates were cleaned up can still carry em dashes in their titles and older
changelog lines. Leave those lines alone: they are history, not prose. Fix every error in
the prose you wrote.

## Checking a draft

Run the checker before delivery. It sits in this skill's `scripts/` folder, wherever
the skill is installed:

| Setup | Checker path |
| --- | --- |
| GitHub Copilot | `.github/skills/writing-style/scripts/sloplint.py` |
| Claude Code | `.claude/skills/writing-style/scripts/sloplint.py` |
| Claude Code plugin | `scripts/sloplint.py` in the plugin's `writing-style` skill folder |

```bash
python .github/skills/writing-style/scripts/sloplint.py docs/artifacts/<app>/executive-briefing.md
```

All copies behave identically. In the AEGIS repository they are generated: change the
source under `aegis/skills/writing-style/` and run `python scripts/sync_platforms.py`.

Useful flags: `--errors-only` hides the context-dependent warnings, and `--quiet` prints counts alone. The exit code is 1 when any error fires and 0 otherwise, so it works in a hook or a pre-commit step.

The checker joins hard-wrapped lines back into sentences before matching, so a rule that anchors to the end of a sentence sees the whole sentence rather than the wrap. It skips fenced code blocks, inline code spans, URLs, and YAML frontmatter. To quote forbidden writing on purpose, wrap it in `<!-- sloplint-disable -->` and `<!-- sloplint-enable -->` comments, as this file does around its own examples.

Warnings need a human. Read each one and decide. A clean run is not proof the writing is good, because the checker cannot see whether a paragraph says anything.

## The Reviewer's Checklist

Run the checker first, then read for the things it cannot measure.

1. Does any sentence use "not X, but Y" or "this is not A, it is B"? Strike it.
2. Does any sentence end with a comma and a participle phrase? Strike the trailing phrase.
3. Are there three or more short sentences in a row used for rhythm? Combine them.
4. Does the text contain a banned word from `references/banned.json`? Replace it.
5. Is there a tetracolon or four-part parallel listing for rhetorical effect? Convert to ordinary prose.
6. Is `ensure` used where a direct verb would work? Replace it.
7. Is there an em dash? Replace it with a comma, a period, or a parenthesis.
8. Does any sentence open with one of the banned connectives or abstract openers listed in rule 6? Cut the opener.
9. Does the closing sentence of a section restate what was just said? Cut it.
10. Are there intensifiers (very, deeply, truly, particularly)? Strike unless they carry real meaning.
11. Does any sentence stack more than three items, or several separate ideas, joined by commas? Split it, or move the list to a table or bullets.
12. Does a paragraph open with an abstract or self-referential topic sentence instead of the plain point? Rewrite the opener to say who does what.
13. Does any document, process, or abstraction act like a person? Give the sentence a real actor.
14. Does any heading tease, count, or dramatise instead of naming its content? Rename it.
15. Does any claim about evidence name its source? If not, cite it or cut it.
16. Could a smart non-specialist follow this on the first read? If not, simplify until they can.

## Quick Test

Read the draft aloud. If any sentence sounds like a movie trailer, a TED talk opening, or a LinkedIn post, rewrite it. The target voice is a competent senior official briefing a peer: direct, specific, declarative, unhurried.

Then read it again as someone outside technology. If a sentence is white noise to that reader, or they could not say back what it means, it is the wrong sentence. Clear and friendly beats dense and impressive.
