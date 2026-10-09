from django.db.models import Avg, Count, Q, Sum

from submissions.models import Submission

from .models import Assignment, Criterion, JudgingRound


def competition_weight_sum(competition):
    """Total of criterion weights for one competition (target: 100)."""
    result = Criterion.objects.filter(competition=competition).aggregate(
        total=Sum("weight")
    )["total"]
    return result or 0


def weights_are_valid(competition):
    """Weights must sum to exactly 100 for percentage scoring."""
    from decimal import Decimal

    return competition_weight_sum(competition) == Decimal("100")


def round_rows(competition, judging_round=None):
    """Submissions of one competition with round-scoped average totals.

    Sorted best-first: scored rows by descending average then earliest
    submission; unscored rows last. ``judging_round=None`` aggregates
    across all rounds (overall standing).
    """
    round_filter = Q()
    if judging_round is not None:
        round_filter = Q(assignments__judging_round=judging_round)
    rows = list(
        Submission.objects.filter(competition=competition)
        .select_related("team")
        .annotate(
            avg_total=Avg(
                "assignments__evaluation__total", filter=round_filter
            ),
            judge_count=Count(
                "assignments__evaluation",
                filter=round_filter,
                distinct=True,
            ),
        )
        .order_by("submitted_at")
    )
    rows.sort(
        key=lambda r: (
            r.avg_total is None,
            -(r.avg_total or 0),
            r.submitted_at,
        )
    )
    return rows


def advancing_submission_ids(competition, judging_round):
    """Top-N submission ids by round average (the teams that pass on).

    Returns [] when there is no round or no cutoff set on the round.
    Unscored submissions never advance.
    """
    if judging_round is None or judging_round.cutoff_top_n is None:
        return []
    scored = [
        r
        for r in round_rows(competition, judging_round)
        if r.avg_total is not None
    ]
    return [r.id for r in scored[: judging_round.cutoff_top_n]]


def close_round_and_advance(judging_round, next_name=None):
    """Close a round and carry the top-N into a new active round.

    Creates the next round (order + 1, ACTIVE) and assigns each
    advancing submission to the same judges as the closing round, so
    history carries over and the new round starts ready to score.
    Returns (next_round, assignments_created).
    """
    competition = judging_round.competition
    advancers = advancing_submission_ids(competition, judging_round)
    judge_ids = list(
        Assignment.objects.filter(judging_round=judging_round)
        .values_list("judge_id", flat=True)
        .distinct()
    )
    next_order = (judging_round.order or 0) + 1
    nxt, _ = JudgingRound.objects.get_or_create(
        competition=competition,
        order=next_order,
        defaults={
            "name": next_name or f"Round {next_order}",
            "status": JudgingRound.Status.ACTIVE,
        },
    )
    created = 0
    for sub_id in advancers:
        for judge_id in judge_ids:
            _, was_created = Assignment.objects.get_or_create(
                submission_id=sub_id,
                judge_id=judge_id,
                judging_round=nxt,
            )
            created += 1 if was_created else 0
    judging_round.status = JudgingRound.Status.DONE
    judging_round.save(update_fields=["status"])
    return nxt, created
