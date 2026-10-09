# Handoff — work outside `evaluations/` (for teammate)

> The evaluation build stays inside `evaluations/` only. Nothing below was
> changed by this build. This doc lists what your friend must add elsewhere
> so the judging flow works end to end. All paths are relative to the repo
> root (`nisr_competition_platform/`).

## 0. Current integration status (already wired)

| Item | File | Status |
|---|---|---|
| `evaluations/` URLs mounted at `/evaluations/` | `nisr_platform/urls.py:29` | ✅ Done — do not touch |
| `evaluations` in `INSTALLED_APPS` | `nisr_platform/settings.py:47` | ✅ Done |
| DB switch (MySQL default, `DB_ENGINE=sqlite` for tests, `DB_ENGINE=postgres` for Docker/server) | `nisr_platform/settings.py:93-126` | ✅ Done — friend on MySQL changes nothing |
| Judge identity (`User.role` = judge/admin) | `accounts/models.py` | ✅ Done |
| Scorable object (`Submission` + `Team` + `Competition.status`) | `submissions/models.py`, `competitions/models.py` | ✅ Done |

## 1. After login, judges must land somewhere useful (friend to add)

**File:** wherever the home/dashboard view lives (planned: `/` route, `LOGIN_REDIRECT_URL`).

- If `user.role == "judge"` → redirect to `/evaluations/` (judge dashboard).
- If `user.role == "admin"` or `user.is_staff` → admin landing with a link to `/evaluations/leaderboard/`.
- Competitors keep the existing landing.
- No changes needed inside `evaluations/` — `judge_dashboard` and `leaderboard` already enforce their own role checks.

## 2. Competition admin should show the rubric inline (friend to add)

**File:** `competitions/admin.py` (register `CompetitionAdmin` if missing).

- Add `from evaluations.models import Criterion, JudgingRound` and inline them:
  ```python
  from django.contrib import admin
  from evaluations.admin import CriterionInline  # already exists
  from evaluations.models import Competition, JudgingRound

  class JudgingRoundInline(admin.TabularInline):
      model = JudgingRound
      extra = 0
      fields = ["name", "order", "cutoff_top_n", "status"]

  @admin.register(Competition)
  class CompetitionAdmin(admin.ModelAdmin):
      list_display = ["name", "track", "status", "submission_deadline"]
      list_filter = ["track", "status"]
      inlines = [CriterionInline, JudgingRoundInline]
  ```
- Why: staff define the rubric (criteria + weights summing to 100) and the
  phases (rounds + top-N cutoff) on the competition page instead of hunting
  through three admin sections.

## 3. Status transitions (friend to confirm, no code required yet)

- `Competition.status`: `open` → `judging` → `closed` (already the model).
- Scoring is allowed only while `judging`; `closed` locks all scores;
  leaderboard is admin-only until `closed` (all enforced in `evaluations/views.py`).
- Rounds live inside `judging`: create `JudgingRound` rows
  (order 1, 2, …), set `cutoff_top_n` (e.g. 8), assign round 1 in
  `AssignmentAdmin`, then use the leaderboard's "Close round — advance top N"
  button to carry teams forward. History is kept automatically.

## 4. Email/notifications (friend to add, optional)

- `nisr_platform/settings.py:174-178` has a `MAILERS` typo (should be
  `EMAIL_BACKEND`) and console backend only. Nothing in `evaluations/`
  sends mail today.
- Suggested hooks (all in friend's files, not evaluations):
  - on judge assignment → email the judge a link to `/evaluations/`;
  - on round advance → email advancing teams;
  - on `closed` → email published-results link.

## 5. DB notes for the two developers

- Friend on MySQL: use `.env` as-is (`DB_HOST=127.0.0.1`, `DB_PORT=3307`).
  No code change. New migration to apply:
  `evaluations/migrations/0003_*` (per-round assignment unique).
- Docker/Postgres: `DB_ENGINE=postgres`, `DB_HOST=db`, `DB_PORT=5432`.
  Same migrations apply unchanged (no MySQL-specific SQL in evaluations).

## 6. How to verify after the friend's changes

```bash
python manage.py migrate
python manage.py test evaluations -v 1   # 21 tests, must be OK
```

1. Create competition (status `judging`), 2+ criteria with weights = 100,
   1 round with `cutoff_top_n=1`.
2. Create 2 teams + submissions, assign both to one judge.
3. Judge scores both at `/evaluations/<id>/score/` (low marks ≤ 40% need a reason).
4. Admin opens `/evaluations/leaderboard/?competition=<id>&round=<round_id>`,
   checks the judges×criteria drill-down links, presses the advance button.
5. New round appears with only the top team assigned; old scores intact.
