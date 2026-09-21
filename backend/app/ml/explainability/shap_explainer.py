"""SHAP explainability helpers for ML workflows."""

import numpy as np
import shap


def _clean_feature_name(
    feature_name: str
) -> str:
    return feature_name.split(
        "__",
        1
    )[-1]


class ChurnExplainer:

    def __init__(
        self,
        model
    ):

        self.model = model

        self.explainer = (
            shap.TreeExplainer(
                model
            )
        )


    def explain(
        self,
        processed_data
    ):
        if hasattr(
            processed_data,
            "toarray"
        ):
            processed_data = processed_data.toarray()

        shap_values = (
            self.explainer(
                processed_data
            )
        )

        return shap_values


    def top_factors(
        self,
        processed_data,
        feature_names,
        top_n: int = 3
    ) -> list[dict[str, float | str]]:
        shap_values = self.explain(
            processed_data
        )

        values = getattr(
            shap_values,
            "values",
            shap_values
        )

        if isinstance(
            values,
            list
        ):
            values = (
                values[1]
                if len(values) > 1
                else values[0]
            )

        values = np.asarray(
            values
        )

        if values.ndim == 3:
            class_index = (
                1
                if values.shape[-1] > 1
                else 0
            )
            values = values[:, :, class_index]

        row_values = values[0]
        feature_names = list(
            feature_names
        )

        factor_count = min(
            len(row_values),
            len(feature_names)
        )

        top_indices = np.argsort(
            np.abs(
                row_values[:factor_count]
            )
        )[::-1][:top_n]

        return [
            {
                "feature": _clean_feature_name(
                    str(feature_names[index])
                ),
                "impact": float(
                    row_values[index]
                ),
            }
            for index in top_indices
        ]
