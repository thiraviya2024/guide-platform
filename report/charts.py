"""
Plotly clinical charts.
"""

from typing import Dict, Any

import plotly.graph_objects as go


STATUS_COLORS = {

    "optimal": "green",

    "normal": "green",

    "near optimal": "lightgreen",

    "borderline high": "orange",

    "high": "red",

    "very high": "darkred",

    "low": "red",

    "invalid": "gray",

    "out of range": "gray"
}


def create_lipid_charts(
    lipid_data: Dict[str, Dict[str, Any]]
) -> go.Figure:

    params = []
    values = []
    colors = []

    for parameter, info in lipid_data.items():

        if parameter in (
            "overall_risk",
            "risk_score"
        ):
            continue

        if not isinstance(info, dict):
            continue

        if "value" not in info:
            continue

        params.append(
            parameter.replace(
                "_",
                " "
            ).title()
        )

        values.append(
            info["value"]
        )

        status = str(
            info.get(
                "status",
                ""
            )
        ).lower()

        colors.append(
            STATUS_COLORS.get(
                status,
                "gray"
            )
        )

    fig = go.Figure()

    fig.add_trace(

        go.Bar(

            x=params,

            y=values,

            marker_color=colors,

            text=values,

            textposition="auto"
        )
    )

    fig.update_layout(

        title="Lipid Profile Analysis",

        xaxis_title="Parameter",

        yaxis_title="Value",

        height=500,

        template="plotly_white"
    )

    return fig