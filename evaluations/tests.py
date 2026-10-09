from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from competitions.models import Competition, Team
from submissions.models import Submission

from .models import Assignment, Criterion, Evaluation, JudgingRound, Score
from .services import (
    advancing_submission_ids,
    close_round_and_advance,
    round_rows,
)

User = get_user_model()


def make_competition(status="judging", track="hackathon"):
    now = timezone.now()
    return Competition.objects.create(
        name="Test Cup",
        track=track,
        description="desc",
        registration_deadline=now - timezone.timedelta(days=2),
        submission_deadline=now + timezone.timedelta(days=2),
        status=status,
    )


def make_team(comp, leader, name="Team A"):
    team = Team.objects.create(name=name, competition=comp, leader=leader)
    team.members.add(leader)
    return team


class EvaluationModelTests(TestCase):
    def setUp(self):
        self.judge = User.objects.create_user(
            username="judge1", password="pw", role=User.Role.JUDGE
        )
        self.leader = User.objects.create_user(username="lead1", password="pw")
        self.comp = make_competition()
        self.c1 = Criterion.objects.create(
            competition=self.comp, name="Impact", max_score=10, weight=40
        )
        self.team = make_team(self.comp, self.leader)
        self.sub = Submission.objects.create(
            team=self.team,
            competition=self.comp,
            github_link="https://example.com/repo",
            agree_ip=True,
        )

    def test_unique_assignment_pair(self):
        Assignment.objects.create(submission=self.sub, judge=self.judge)
        with self.assertRaises(ValidationError):
            dup = Assignment(submission=self.sub, judge=self.judge)
            dup.full_clean()

    def test_percentage_total(self):
        c2 = Criterion.objects.create(
            competition=self.comp, name="Design", max_score=10, weight=60
        )
        a = Assignment.objects.create(submission=self.sub, judge=self.judge)
        ev = Evaluation.objects.create(assignment=a)
        Score.objects.create(evaluation=ev, criterion=self.c1, value=8)
        Score.objects.create(evaluation=ev, criterion=c2, value=5)
        # 8/10*40 + 5/10*60 = 32 + 30 = 62
        self.assertEqual(ev.recompute_total(), Decimal("62.00"))

    def test_criterion_max_zero_rejected(self):
        bad = Criterion(
            competition=self.comp, name="Bad", max_score=0, weight=10
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_criterion_weight_range(self):
        bad = Criterion(
            competition=self.comp, name="Bad", max_score=10, weight=150
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_score_above_max_rejected(self):
        a = Assignment.objects.create(submission=self.sub, judge=self.judge)
        ev = Evaluation.objects.create(assignment=a)
        s = Score(evaluation=ev, criterion=self.c1, value=99)
        with self.assertRaises(ValidationError):
            s.full_clean()


class EvaluationViewTests(TestCase):
    def setUp(self):
        self.judge = User.objects.create_user(
            username="judge1", password="pw", role=User.Role.JUDGE
        )
        self.judge2 = User.objects.create_user(
            username="judge2", password="pw", role=User.Role.JUDGE
        )
        self.comp = make_competition()
        self.c1 = Criterion.objects.create(
            competition=self.comp, name="Impact", max_score=10, weight=100
        )
        self.leader = User.objects.create_user(username="lead1", password="pw")
        self.team = make_team(self.comp, self.leader)
        self.sub = Submission.objects.create(
            team=self.team,
            competition=self.comp,
            github_link="https://example.com/repo",
            agree_ip=True,
        )
        self.assignment = Assignment.objects.create(
            submission=self.sub, judge=self.judge
        )

    def test_dashboard_requires_judge(self):
        outsider = User.objects.create_user(username="out", password="pw")
        self.client.force_login(outsider)
        resp = self.client.get(reverse("judge_dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_judge_isolation(self):
        self.client.force_login(self.judge2)
        resp = self.client.get(
            reverse("score_submission", args=[self.assignment.id])
        )
        self.assertEqual(resp.status_code, 403)

    def test_score_post_saves_total(self):
        self.client.force_login(self.judge)
        url = reverse("score_submission", args=[self.assignment.id])
        resp = self.client.post(
            url,
            {
                f"criterion_{self.c1.id}": "7",
                f"reason_{self.c1.id}": "solid work",
                "comments": "good",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.DONE)
        # 7/10 * 100 = 70.00
        self.assertEqual(
            self.assignment.evaluation.total, Decimal("70.00")
        )
        score = self.assignment.evaluation.scores.get(criterion=self.c1)
        self.assertEqual(score.comment, "solid work")

    def test_scoring_blocked_when_not_judging(self):
        self.comp.status = Competition.Status.OPEN
        self.comp.save()
        self.client.force_login(self.judge)
        resp = self.client.get(
            reverse("score_submission", args=[self.assignment.id])
        )
        self.assertEqual(resp.status_code, 302)

    def test_leaderboard_hidden_before_closed(self):
        self.client.force_login(self.leader)
        resp = self.client.get(reverse("leaderboard"))
        self.assertContains(resp, "published only after")

    def test_leaderboard_order(self):
        leader2 = User.objects.create_user(username="lead2", password="pw")
        team2 = make_team(self.comp, leader2, name="Team B")
        sub2 = Submission.objects.create(
            team=team2,
            competition=self.comp,
            github_link="https://example.com/other",
            agree_ip=True,
        )
        a2 = Assignment.objects.create(submission=sub2, judge=self.judge)
        ev1 = Evaluation.objects.create(assignment=self.assignment)
        Score.objects.create(evaluation=ev1, criterion=self.c1, value=9)
        ev1.recompute_total()
        ev2 = Evaluation.objects.create(assignment=a2)
        Score.objects.create(evaluation=ev2, criterion=self.c1, value=4)
        ev2.recompute_total()
        self.comp.status = Competition.Status.CLOSED
        self.comp.save()
        admin = User.objects.create_user(
            username="adm", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        self.client.force_login(admin)
        resp = self.client.get(
            reverse("leaderboard") + f"?competition={self.comp.id}"
        )
        rows = list(resp.context["rows"])
        self.assertEqual(rows[0].team.name, "Team A")
        self.assertEqual(rows[1].team.name, "Team B")


    def test_low_mark_requires_reason(self):
        self.client.force_login(self.judge)
        url = reverse("score_submission", args=[self.assignment.id])
        resp = self.client.post(
            url,
            {
                f"criterion_{self.c1.id}": "2",
                f"reason_{self.c1.id}": "",
                "comments": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            Evaluation.objects.filter(assignment=self.assignment).exists()
        )

    def test_bad_weight_sum_blocks_scoring(self):
        Criterion.objects.create(
            competition=self.comp, name="Extra", max_score=10, weight=10
        )
        self.client.force_login(self.judge)
        resp = self.client.get(
            reverse("score_submission", args=[self.assignment.id])
        )
        self.assertEqual(resp.status_code, 302)

    def test_closed_locks_scoring(self):
        self.comp.status = Competition.Status.CLOSED
        self.comp.save()
        self.client.force_login(self.judge)
        resp = self.client.get(
            reverse("score_submission", args=[self.assignment.id])
        )
        self.assertEqual(resp.status_code, 302)

    def test_submission_detail_admin_only(self):
        url = reverse("submission_detail", args=[self.sub.id])
        self.client.force_login(self.leader)
        self.assertEqual(self.client.get(url).status_code, 403)
        admin = User.objects.create_user(
            username="adm2", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        self.client.force_login(admin)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("grid", resp.context)

    def test_audit_created_on_score(self):
        from .models import ScoreAudit

        self.client.force_login(self.judge)
        url = reverse("score_submission", args=[self.assignment.id])
        self.client.post(
            url,
            {
                f"criterion_{self.c1.id}": "8",
                f"reason_{self.c1.id}": "great impact",
                "comments": "",
            },
        )
        self.assertEqual(ScoreAudit.objects.count(), 1)
        audit = ScoreAudit.objects.first()
        self.assertEqual(audit.new_value, Decimal("8"))
        self.assertEqual(audit.changed_by, self.judge)

    def test_round_top_n_advance(self):
        rnd = JudgingRound.objects.create(
            competition=self.comp,
            name="Semi-final",
            order=1,
            cutoff_top_n=1,
            status=JudgingRound.Status.ACTIVE,
        )
        self.assertEqual(rnd.cutoff_top_n, 1)
        self.assignment.judging_round = rnd
        self.assignment.save()
        self.assertEqual(
            self.assignment.judging_round.competition, self.comp
        )

    def test_same_pair_can_score_in_two_rounds(self):
        from django.core.exceptions import ValidationError

        rnd2 = JudgingRound.objects.create(
            competition=self.comp, name="Final", order=2
        )
        Assignment.objects.create(submission=self.sub, judge=self.judge)
        # Same pair in a different round is allowed…
        ok = Assignment(
            submission=self.sub, judge=self.judge, judging_round=rnd2
        )
        ok.full_clean()  # must not raise
        # …but the exact same round twice is rejected.
        dup = Assignment(submission=self.sub, judge=self.judge)
        with self.assertRaises(ValidationError):
            dup.full_clean()

    def test_round_rows_and_advancers(self):
        rnd = JudgingRound.objects.create(
            competition=self.comp,
            name="Semi-final",
            order=1,
            cutoff_top_n=1,
            status=JudgingRound.Status.ACTIVE,
        )
        # Two submissions, one strong (9/10 → 90) one weak (4/10 → 40).
        strong_ev = Evaluation.objects.create(assignment=self.assignment)
        Score.objects.create(
            evaluation=strong_ev, criterion=self.c1, value=9
        )
        strong_ev.recompute_total()
        self.assignment.judging_round = rnd
        self.assignment.save()
        leader2 = User.objects.create_user(username="leadX", password="pw")
        team2 = make_team(self.comp, leader2, name="Team X")
        sub2 = Submission.objects.create(
            team=team2,
            competition=self.comp,
            github_link="https://example.com/x",
            agree_ip=True,
        )
        a2 = Assignment.objects.create(
            submission=sub2, judge=self.judge, judging_round=rnd
        )
        weak_ev = Evaluation.objects.create(assignment=a2)
        Score.objects.create(evaluation=weak_ev, criterion=self.c1, value=4)
        weak_ev.recompute_total()

        rows = round_rows(self.comp, rnd)
        self.assertEqual(rows[0].team.name, "Team A")
        self.assertEqual(rows[1].team.name, "Team X")
        self.assertEqual(
            advancing_submission_ids(self.comp, rnd), [self.sub.id]
        )

    def test_close_round_and_advance(self):
        rnd = JudgingRound.objects.create(
            competition=self.comp,
            name="Semi-final",
            order=1,
            cutoff_top_n=1,
            status=JudgingRound.Status.ACTIVE,
        )
        ev = Evaluation.objects.create(assignment=self.assignment)
        Score.objects.create(evaluation=ev, criterion=self.c1, value=9)
        ev.recompute_total()
        self.assignment.judging_round = rnd
        self.assignment.save()

        nxt, created = close_round_and_advance(rnd)
        self.assertEqual(nxt.order, 2)
        self.assertEqual(nxt.status, JudgingRound.Status.ACTIVE)
        self.assertEqual(created, 1)
        rnd.refresh_from_db()
        self.assertEqual(rnd.status, JudgingRound.Status.DONE)
        self.assertTrue(
            Assignment.objects.filter(
                submission=self.sub,
                judge=self.judge,
                judging_round=nxt,
            ).exists()
        )

    def test_advance_round_view_admin_only(self):
        rnd = JudgingRound.objects.create(
            competition=self.comp,
            name="Semi-final",
            order=1,
            cutoff_top_n=1,
            status=JudgingRound.Status.ACTIVE,
        )
        url = reverse("advance_round", args=[rnd.id])
        # Non-admin is refused…
        self.client.force_login(self.leader)
        self.assertEqual(self.client.post(url).status_code, 403)
        # …admin triggers close + carry-over.
        ev = Evaluation.objects.create(assignment=self.assignment)
        Score.objects.create(evaluation=ev, criterion=self.c1, value=9)
        ev.recompute_total()
        self.assignment.judging_round = rnd
        self.assignment.save()
        admin = User.objects.create_user(
            username="adm3", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        self.client.force_login(admin)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        rnd.refresh_from_db()
        self.assertEqual(rnd.status, JudgingRound.Status.DONE)

