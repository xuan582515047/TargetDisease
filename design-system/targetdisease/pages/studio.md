# Research studio: structural redesign

Overrides the earlier authentication and workspace layout in MASTER.md.

## Skill evidence and selection

UI UX Pro Max was queried with `research workspace dashboard --design-system --variance 8 --density 6`. Its portfolio/brutalism match was rejected as inappropriate for an operational scientific tool. The narrower `SaaS analytics dashboard --design-system --density 6` returned Data-Dense Dashboard and technical sans/monospace typography. Its sales-oriented landing pattern was not adopted.

The explicit `bento grid --domain style` match returned Bento Box Grid: modular, asymmetric layouts with responsive card spans. The UX search `empty state action` returned guidance to pair empty states with a helpful next action. Form guidance requires clear labels and loading/success/error feedback. Existing FastAPI authentication and mutations are retained rather than replacing them merely to match a generic Next.js recommendation.

## Actual structural changes

- Authentication: full-height editorial split. An interactive three-chapter product explanation occupies the left; a quiet, light account area has login/register navigation and a narrow form on the right. Mobile puts the compact capability section before the form.
- Dashboard: a compact four-metric strip, asymmetric launch/readiness grid, task status filters and search, recent project links, contextual setup action. Real data drives every metric and state.
- Credentials: provider identity, a save/validate/research progression, separate editor and connection card, compact metadata and contextual controls instead of a one-row wide table, expandable setup help.
- Discovery: disease selection, research description, and review are distinct steps. Back navigation preserves inputs. Mechanism presets fill editable text. A research brief mirrors current input and explains expected outputs. Submission uses the original API payload and credential gate.

## Validation

Browser-tested real registration/login, chapter switching, wizard navigation and input preservation, missing-key submission guard, real save/remove of an isolated test credential, and a simulated validation failure. Populated task filtering/search and submission failures are tested with browser-only response fixtures, never presented as real research output. Checked 375, 768, 1024 and 1600 pixel layouts. Production build and lint of changed components pass.


## Current usability refinement (supersedes presentation-heavy layout)

User feedback: buttons and typography felt generated and unfamiliar. UI UX Pro Max `readable typography --domain ux` verified readable sizing, contrast and line length. The button hierarchy query did not yield a relevant hierarchy rule; conventional primary/secondary button hierarchy is an implementation decision, while retaining the skill's verified async submission feedback rule.

- Chinese system UI font stack; 14–16 px body and labels, 24–26 px page headings, 40 px desktop / 44 px mobile buttons. Technical IDs alone retain monospaced treatment.
- Dashboard prioritizes the task list in the first viewport. Remove the redundant promotional hero; model status and recent projects form a secondary column.
- Short action labels: 登录, 新建分析, 保存凭据. Remove decorative English section codes, exaggerated headings and padded numeric counters.
- Credentials use a two-column editor/help layout, removing the decorative provider panel. Preserve real save, validate and delete behavior.
- Flat white panels, modest 6–8 px radii, restrained borders, no decorative button glow.
- Mobile authentication shows the actual form promptly; product explanation is compact.
