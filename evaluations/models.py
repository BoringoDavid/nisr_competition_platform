from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from competitions.models import Competition
from submissions.models import Submission


class Criterion(models.Model):
    """Rubric item belonging to one competition (admin-editable).

    ``weight`` is a percentage share of the total (all weights for one
    competition must sum to 100). Each score is out of ``max_score``.
    """

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="criteria"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    max_score = models.PositiveIntegerField(default=10)
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage share of the total (weights must sum to 100).",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "name"],
                name="unique_criterion_name_per_competition",
            ),
        ]

    def __str__(self):
        return f"{self.competition.name} — {self.name} (max {self.max_score})"

    def clean(self):
        super().clean()
        errors = {}
        if self.max_score is not None and self.max_score <= 0:
            errors["max_score"] = "Maximum score must be greater than zero."
        if self.weight is not None and (
            self.weight < 0 or self.weight > 100
        ):
            errors["weight"] = "Weight must be a percentage between 0 and 100."
        if errors:
            raise ValidationError(errors)


class Assignment(models.Model):
    """Routes one submission to one judge. Created by staff in admin."""

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="assignments"
    )
    judge = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="judge_assignments",
    )
    # Null = round 1 (default for data created before rounds existed).
    judging_round = models.ForeignKey(
        "JudgingRound",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ASSIGNED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # One judge scores one submission once PER ROUND, so phased
            # judging (semi-final, final) can re-assign the same pair.
            models.UniqueConstraint(
                fields=["submission", "judge", "judging_round"],
                name="unique_assignment_per_round",
            ),
        ]

    def __str__(self):
        return f"{self.submission} → {self.judge.username} [{self.status}]"

    def clean(self):
        super().clean()
        # DB uniques treat NULL rounds as distinct; block duplicates in
        # Python too so round-less (round 1) assignments stay unique.
        qs = Assignment.objects.filter(
            submission=self.submission,
            judge=self.judge,
            judging_round=self.judging_round,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                "This judge is already assigned to this submission "
                "in this round."
            )


class Evaluation(models.Model):
    """One judge's overall evaluation for one assignment (1:1)."""

    assignment = models.OneToOneField(
        Assignment, on_delete=models.CASCADE, related_name="evaluation"
    )
    comments = models.TextField(blank=True)
    total = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Evaluation of {self.assignment} (total {self.total})"

    def recompute_total(self, save=True):
        """Percentage total out of 100.

        Each criterion contributes (value / max_score) * weight, where
        weights are percentage shares summing to 100. Rounded to 2 dp.
        """
        from decimal import Decimal, ROUND_HALF_UP

        total = Decimal("0")
        for score in self.scores.select_related("criterion").all():
            max_score = Decimal(score.criterion.max_score)
            if max_score <= 0:
                continue
            total += (Decimal(score.value) / max_score) * Decimal(
                score.criterion.weight
            )
        self.total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if save:
            self.save(update_fields=["total", "updated_at"])
        return self.total


class Score(models.Model):
    """Per-criterion score inside an evaluation."""

    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name="scores"
    )
    criterion = models.ForeignKey(
        Criterion, on_delete=models.PROTECT, related_name="scores"
    )
    value = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    # Judge's written reason for THIS mark (the "why" behind each score).
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "criterion"],
                name="unique_score_per_evaluation_criterion",
            ),
            models.CheckConstraint(
                check=Q(value__gte=0),
                name="score_value_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.evaluation_id}/{self.criterion.name} = {self.value}"

    def clean(self):
        super().clean()
        if self.criterion_id and self.criterion.max_score is not None:
            if self.value is not None and self.value > self.criterion.max_score:
                raise ValidationError(
                    {
                        "value": f"Score cannot exceed {self.criterion.max_score} "
                        f"for '{self.criterion.name}'."
                    }
                )




class ScoreAudit(models.Model):
    """Who changed a score, old → new value, when. Never edited by hand."""

    score = models.ForeignKey(
        Score, on_delete=models.CASCADE, related_name="audits"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="score_audits",
    )
    old_value = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    new_value = models.DecimalField(max_digits=5, decimal_places=2)
    old_comment = models.TextField(blank=True)
    new_comment = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"Audit {self.score_id}: {self.old_value} → {self.new_value}"


class JudgingRound(models.Model):
    """One phase of judging. Top-N advance; history carries over.

    Round 1 is the default: existing assignments belong to round 1 until
    staff create later rounds. Only current-round assignments are scored;
    earlier rounds stay as history for the drill-down page.
    """

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ACTIVE = "active", "Active"
        DONE = "done", "Done"

    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="rounds"
    )
    name = models.CharField(max_length=100, default="Round 1")
    order = models.PositiveIntegerField(default=1)
    # Top-N submissions advance to the next round (None = no cutoff set).
    cutoff_top_n = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPCOMING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["competition", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "order"],
                name="unique_round_order_per_competition",
            ),
        ]

    def __str__(self):
        return f"{self.competition.name} — {self.name} [{self.status}]"
