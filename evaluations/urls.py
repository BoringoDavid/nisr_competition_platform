from django.urls import path

from . import views

urlpatterns = [
    path("", views.judge_dashboard, name="judge_dashboard"),
    path(
        "<int:assignment_id>/score/",
        views.score_submission,
        name="score_submission",
    ),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path(
        "submission/<int:submission_id>/",
        views.submission_detail,
        name="submission_detail",
    ),
    path(
        "round/<int:round_id>/advance/",
        views.advance_round,
        name="advance_round",
    ),
]
