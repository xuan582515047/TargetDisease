# Continuous PharmAgents workflow

User-approved scope: small molecules; faithful paper-oriented execution; one project/run spans target discovery, lead identification, lead optimization and preclinical candidate (PCC) evaluation. Automatic mode runs through; permission mode pauses at target and lead selection only. Select three leads, five optimization rounds per path, fixed original lead with accumulated feedback. Include baseline when choosing one best per path, deduplicate final candidates. End after PCC with an evidence-based report, including no qualifying candidate if applicable. No clinical efficacy claims.

Deployment choice is deferred. Keep the existing FastAPI/SQLAlchemy/Next.js application. Preserve legacy records. New runs use a versioned checkpoint document and a durable database-backed worker queue, avoiding credentials in queue payloads. Persist each expensive result before advancing. Worker restart resumes persisted checkpoints. Scientific inference must not be simulated: unconfigured tools pause with an actionable error; actual calculation errors fail visibly. Scientific artifacts stay under a run-owned persistent directory.

External pretrained checkpoints/data are not bundled in this repository. Implement and document scientific adapters and validate contracts locally; distinguish orchestration tests from actual GPU inference validation.
