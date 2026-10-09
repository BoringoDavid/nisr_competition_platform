from django.contrib import admin
from django.db.models import Sum

from .models import Assignment, Criterion, Evaluation, JudgingRound, Score
from .models import ScoreAudit
from .services import competition_weight_sum


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 0
    fields = ["name", "description", "max_score", "weight", "order"]


class ScoreInline(admin.TabularInline):
    model = Score
    extra = 0
    fields = ["criterion", "value", "comment"]
    readonly_fields = []


class ScoreAuditInline(admin.TabularInline):
    model = ScoreAudit
    extra = 0
    fields = ["changed_by", "old_value", "new_value", "changed_at"]
    readonly_fields = ["changed_by", "old_value", "new_value", "changed_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Criterion)
class CriterionAdmin(admin.ModelAdmin):
    list_display = ["competition", "name", "max_score", "weight", "order"]
    list_filter = ["competition"]
    ordering = ["competition", "order"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        total = competition_weight_sum(obj.competition)
        if total != 100:
            self.message_user(
                request,
                f"Weights for {obj.competition.name} sum to {total}, "
                "not 100 — scoring is blocked until fixed.",
                level="WARNING",
            )


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["submission", "judge", "judging_round", "status", "created_at"]
    list_filter = ["status", "judging_round", "submission__competition"]
    search_fields = ["judge__username", "submission__team__name"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "judge":
            from django.contrib.auth import get_user_model

            User = get_user_model()
            kwargs["queryset"] = User.objects.filter(role=User.Role.JUDGE)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ["assignment", "total", "submitted_at", "updated_at"]
    readonly_fields = ["total", "submitted_at", "updated_at"]
    inlines = [ScoreInline]


@admin.register(JudgingRound)
class JudgingRoundAdmin(admin.ModelAdmin):
    list_display = ["competition", "name", "order", "cutoff_top_n", "status"]
    list_filter = ["competition", "status"]
    ordering = ["competition", "order"]


@admin.register(ScoreAudit)
class ScoreAuditAdmin(admin.ModelAdmin):
    list_display = ["score", "changed_by", "old_value", "new_value", "changed_at"]
    readonly_fields = ["score", "changed_by", "old_value", "new_value",
                       "old_comment", "new_comment", "changed_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

