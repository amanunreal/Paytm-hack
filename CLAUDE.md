# Wapsi

Two people build this, A1 and A2, each with their own Claude. The sessions cannot see
each other, so this repo is how they stay in sync. `PLAN.md` is the source of truth.
If you do not know which teammate you are working with, ask once.

## Every task

1. `git pull --rebase`, then read the Tasks table in `PLAN.md`.
2. Pick the next `todo` task owned by your teammate. Never start a task that is not yours
   or that is already `doing`.
3. Claim it before writing code: set it to `doing`, commit, push. If the push is rejected,
   pull and check that nobody else claimed it.
4. Do the work and run the tests.
5. Set the task to `done`, commit, `git pull --rebase`, push.

## Boundaries

- Only edit files your teammate owns (see "Who owns what" in `PLAN.md`).
- Shared files need agreement from both people first. Tell your teammate to ask the
  other person, who is sitting next to them.
- Never break the API contract quietly. Agree the change, then update `PLAN.md` in the
  same commit.
- Record any decision that affects both people under Decisions in `PLAN.md`.

## Commits

- Small commits on `main` with plain messages.
- No Co-Authored-By lines and no Claude sign-off.
- Never commit `.env`, `data/` or keys.

## Rules from the plan

- The real agent never reads `ground_truth`.
- Waiver limits are enforced in the tool, never only in the prompt.
- No bank or IFSC details over voice.
- Keep it all-India: never scope data or logic to one city.
- `/api/reset` must always return a clean demo.

Run tests with `uv run python -m unittest discover -s tests -t .`
