from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from competitions.models import Competition
from submissions.models import Submission

from .forms import build_score_form
from .models import (
    Assignment,
    Criterion,
    Evaluation,
    JudgingRound,
    Score,
    ScoreAudit,
)
from .services import (
    advancing_submission_ids,
    close_round_and_advance,
    round_rows,
    weights_are_valid,
)

# Approved defaults (plan Step 0): weighted total stored on Evaluation,
# leaderboard = average of totals, visible to admin always + others only
# when closed, editable until closed, blind judging OFF with flag ready.
BLIND_JUDGING = False


def _is_judge(user):
    return user.is_authenticated and (
        getattr(user, "role", None) in ("judge", "admin") or user.is_staff
    )


@login_required
def judge_dashboard(request):
    if not _is_judge(request.user):
        return HttpResponseForbidden("Judges only.")
    qs = (
        Assignment.objects.select_related(
            "submission__team__competition", "judge"
        )
        .prefetch_related("evaluation")
        .order_by("-created_at")
    )
    if not (request.user.role == "admin" or request.user.is_staff):
        qs = qs.filter(judge=request.user)
    return render(
        request,
        "evaluations/dashboard.html",
        {"assignments": qs, "blind": BLIND_JUDGING},
    )
@login_required
def score_submission(request, assignment_id):
    if not _is_judge(request.user):
        return HttpResponseForbidden("Judges only.")
    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "submission__team__competition", "submission__team"
        ),
        id=assignment_id,
    )
    if (
        assignment.judge_id != request.user.id
        and not request.user.is_staff
        and request.user.role != "admin"
    ):
        return HttpResponseForbidden("Not your assigned submission.")

    competition = assignment.submission.competition
    if competition.status == Competition.Status.CLOSED:
        messages.error(request, "Judging is closed — scores are locked.")
        return redirect("judge_dashboard")
    if competition.status != Competition.Status.JUDGING:
        messages.error(request, "Scoring is only allowed while judging.")
        return redirect("judge_dashboard")

    criteria = list(Criterion.objects.filter(competition=competition))
    if not criteria:
        messages.error(request, "No rubric defined for this competition.")
        return redirect("judge_dashboard")
    if not weights_are_valid(competition):
        messages.error(
            request,
            "Rubric weights do not sum to 100 — ask an admin to fix "
            "the rubric before scoring.",
        )
        return redirect("judge_dashboard")

    evaluation = getattr(assignment, "evaluation", None)
    existing = {}
    existing_reasons = {}
    if evaluation is not None:
        for s in evaluation.scores.all():
            existing[s.criterion_id] = s.value
            existing_reasons[s.criterion_id] = s.comment

    FormClass = build_score_form(criteria)
    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            with transaction.atomic():
                if evaluation is None:
                    evaluation = Evaluation.objects.create(
                        assignment=assignment,
                        comments=form.cleaned_data.get("comments", ""),
                    )
                else:
                    evaluation.comments = form.cleaned_data.get("comments", "")
                    evaluation.save(update_fields=["comments", "updated_at"])
                for criterion in criteria:
                    value = form.cleaned_data[f"criterion_{criterion.id}"]
                    reason = form.cleaned_data.get(
                        f"reason_{criterion.id}", ""
                    )
                    old_score = Score.objects.filter(
                        evaluation=evaluation, criterion=criterion
                    ).first()
                    score, _ = Score.objects.update_or_create(
                        evaluation=evaluation,
                        criterion=criterion,
                        defaults={"value": value, "comment": reason},
                    )
                    score.full_clean()
                    score.save()
                    if old_score is None or (
                        old_score.value != score.value
                        or old_score.comment != score.comment
                    ):
                        ScoreAudit.objects.create(
                            score=score,
                            changed_by=request.user,
                            old_value=(
                                old_score.value if old_score else None
                            ),
                            new_value=score.value,
                            old_comment=(
                                old_score.comment if old_score else ""
                            ),
                            new_comment=score.comment,
                        )
                evaluation.recompute_total()
                if assignment.status != Assignment.Status.DONE:
                    assignment.status = Assignment.Status.DONE
                    assignment.save(update_fields=["status"])
            messages.success(request, "Scores saved.")
            return redirect("judge_dashboard")
    else:
        initial = {f"criterion_{c.id}": existing.get(c.id) for c in criteria}
        initial.update(
            {f"reason_{c.id}": existing_reasons.get(c.id, "") for c in criteria}
        )
        initial["comments"] = evaluation.comments if evaluation else ""
        form = FormClass(initial=initial)
        if assignment.status == Assignment.Status.ASSIGNED:
            assignment.status = Assignment.Status.IN_PROGRESS
            assignment.save(update_fields=["status"])

    context = {
        "assignment": assignment,
        "submission": assignment.submission,
        "competition": competition,
        "criteria": criteria,
        "form": form,
        "evaluation": evaluation,
        "blind": BLIND_JUDGING,
    }
    if BLIND_JUDGING:
        context.pop("submission", None)
    return render(request, "evaluations/score.html", context)


@login_required
def submission_detail(request, submission_id):
    """Admin drill-down: judges × criteria with marks and reasons."""
    if not (request.user.is_staff or request.user.role == "admin"):
        return HttpResponseForbidden("Admins only.")
    submission = get_object_or_404(
        Submission.objects.select_related("team__competition", "team"),
        id=submission_id,
    )
    competition = submission.competition
    criteria = list(Criterion.objects.filter(competition=competition))
    assignments = (
        Assignment.objects.filter(submission=submission)
        .select_related("judge")
        .prefetch_related("evaluation__scores__criterion")
        .order_by("judge__username")
    )
    grid = []
    for assignment in assignments:
        evaluation = getattr(assignment, "evaluation", None)
        by_criterion = {}
        if evaluation is not None:
            for score in evaluation.scores.all():
                by_criterion[score.criterion_id] = score
        grid.append(
            {
                "assignment": assignment,
                "evaluation": evaluation,
                "by_criterion": by_criterion,
            }
        )
    return render(
        request,
        "evaluations/submission_detail.html",
        {
            "submission": submission,
            "competition": competition,
            "criteria": criteria,
            "grid": grid,
            "blind": BLIND_JUDGING,
        },
    )


@login_required
def leaderboard(request):
    competition_id = request.GET.get("competition")
    competitions = Competition.objects.order_by("-created_at")
    competition = None
    if competition_id:
        competition = get_object_or_404(Competition, id=competition_id)
    else:
        competition = competitions.first()

    rounds = []
    judging_round = None
    advancers = []
    rows = []
    published = True
    if competition is not None:
        is_admin = (
            request.user.is_staff or getattr(request.user, "role", "") == "admin"
        )
        if competition.status != Competition.Status.CLOSED and not is_admin:
            messages.error(request, "Results publish after judging closes.")
            published = False
        else:
            rounds = list(competition.rounds.all())
            round_id = request.GET.get("round")
            if round_id:
                judging_round = get_object_or_404(
                    JudgingRound, id=round_id, competition=competition
                )
            rows = round_rows(competition, judging_round)
            if is_admin and judging_round is not None:
                advancers = advancing_submission_ids(
                    competition, judging_round
                )
    return render(
        request,
        "evaluations/leaderboard.html",
        {
            "competitions": competitions,
            "competition": competition,
            "rounds": rounds,
            "judging_round": judging_round,
            "advancers": advancers,
            "rows": rows,
            "published": published,
            "blind": BLIND_JUDGING,
        },
    )


def _is_admin(user):
    return user.is_staff or getattr(user, "role", "") == "admin"


@login_required
def advance_round(request, round_id):
    """Admin: close a round and carry its top-N into the next round."""
    judging_round = get_object_or_404(JudgingRound, id=round_id)
    if not _is_admin(request.user):
        return HttpResponseForbidden("Admins only.")
    if request.method != "POST":
        return redirect(
            f"{reverse('leaderboard')}?competition="
            f"{judging_round.competition_id}&round={judging_round.id}"
        )
    if judging_round.cutoff_top_n is None:
        messages.error(request, "Set a top-N cutoff on the round first.")
    else:
        nxt, created = close_round_and_advance(judging_round)
        messages.success(
            request,
            f"{judging_round.name} closed — {created} assignments created "
            f"in {nxt.name}.",
        )
    return redirect(
        f"{reverse('leaderboard')}?competition="
        f"{judging_round.competition_id}"
    )


