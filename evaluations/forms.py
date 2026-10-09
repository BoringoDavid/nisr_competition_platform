from django import forms

# A mark at or below this fraction of max_score must include a reason.
LOW_MARK_FRACTION = 0.4


def build_score_form(criteria):
    """Build a dynamic form: one mark + one reason per rubric criterion."""
    fields = {}
    for criterion in criteria:
        fields[f"criterion_{criterion.id}"] = forms.DecimalField(
            label=f"{criterion.name} (max {criterion.max_score}, "
            f"{criterion.weight}%)",
            help_text=criterion.description,
            min_value=0,
            max_value=criterion.max_score,
            max_digits=5,
            decimal_places=2,
            required=True,
        )
        fields[f"reason_{criterion.id}"] = forms.CharField(
            label=f"Why this mark for {criterion.name}?",
            widget=forms.Textarea(attrs={"rows": 2}),
            required=False,
        )
    fields["comments"] = forms.CharField(
        label="Overall comments",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )

    def _clean_scores(self):
        cleaned = forms.Form.clean(self)
        for criterion in criteria:
            mark = cleaned.get(f"criterion_{criterion.id}")
            reason = (cleaned.get(f"reason_{criterion.id}") or "").strip()
            if mark is not None and criterion.max_score:
                threshold = float(criterion.max_score) * LOW_MARK_FRACTION
                if float(mark) <= threshold and not reason:
                    self.add_error(
                        f"reason_{criterion.id}",
                        "A reason is required for a low mark "
                        f"(≤ {threshold:g}/{criterion.max_score}).",
                    )
        return cleaned

    return type(
        "DynamicScoreForm",
        (forms.Form,),
        {**fields, "clean": _clean_scores},
    )
