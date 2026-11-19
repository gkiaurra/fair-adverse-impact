import math
from pathlib import Path

import pandas as pd
import streamlit as st


DEFAULT_DATA_PATH = (
    Path(__file__).parent / "data" / "FAIR_Synthetic_Applicant_Data_2.csv"
)

st.set_page_config(
    page_title="FAIR Hiring Dashboard",
    page_icon="⚖️",
    layout="wide",
)


def calculate_adverse_impact(
    data: pd.DataFrame,
    group_column: str,
    outcome_column: str,
    favorable_value: object,
    reference_group: object,
) -> pd.DataFrame:
    """Calculate selection rates and ratios for non-missing group/outcome rows."""
    analysis = data[[group_column, outcome_column]].dropna().copy()
    analysis["_favorable"] = analysis[outcome_column].eq(favorable_value)

    summary = (
        analysis.groupby(group_column, sort=False)["_favorable"]
        .agg(eligible="size", selected="sum", selection_rate="mean")
        .reset_index()
        .rename(columns={group_column: "Group"})
    )
    reference_rate = summary.loc[
        summary["Group"].eq(reference_group), "selection_rate"
    ].iloc[0]

    summary["Rate difference (pp)"] = (
        summary["selection_rate"] - reference_rate
    ) * 100
    summary["Impact ratio"] = math.nan
    if reference_rate > 0:
        summary["Impact ratio"] = summary["selection_rate"] / reference_rate
    else:
        summary.loc[summary["Group"].eq(reference_group), "Impact ratio"] = 1.0
    summary["Below 0.80"] = (
        summary["Group"].ne(reference_group)
        & summary["Impact ratio"].lt(0.8)
    )
    return summary


st.title("Fair Adverse Impact Dashboard")
st.markdown(
    "Explore outcome rates across groups in a CSV dataset. Choose the group "
    "and outcome fields, define the favorable outcome, and select a reference group."
)
st.caption(
    "Screening aid only: the 0.80 impact-ratio benchmark is a common rule of "
    "thumb, not a legal conclusion or proof of fairness."
)

with st.sidebar:
    st.header("Dataset")
    uploaded_file = st.file_uploader(
        "Replace the default dataset (optional CSV upload)", type="csv"
    )

if uploaded_file is None:
    data = pd.read_csv(DEFAULT_DATA_PATH)
    data_source = DEFAULT_DATA_PATH.name
else:
    try:
        data = pd.read_csv(uploaded_file)
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        st.error(f"Could not read the uploaded CSV: {error}")
        st.stop()
    data_source = uploaded_file.name

if data.empty:
    st.error("The uploaded CSV has a header but no data rows.")
    st.stop()
if len(data.columns) < 2:
    st.error("The CSV must contain at least two columns: a group and an outcome.")
    st.stop()

with st.sidebar:
    st.header("Analysis settings")
    group_column_options = data.columns.tolist()
    default_group = (
        "race_ethnicity" if "race_ethnicity" in group_column_options else group_column_options[0]
    )
    group_column = st.selectbox(
        "Group / protected attribute",
        group_column_options,
        index=group_column_options.index(default_group),
    )
    outcome_columns = [column for column in data.columns if column != group_column]
    default_outcome = "selected" if "selected" in outcome_columns else outcome_columns[0]
    outcome_column = st.selectbox(
        "Decision / outcome",
        outcome_columns,
        index=outcome_columns.index(default_outcome),
    )

    analyze_qualified_only = False
    qualified_value = None
    if "qualified" in data.columns:
        qualified_values = data["qualified"].dropna().unique().tolist()
        if qualified_values:
            analyze_qualified_only = st.checkbox(
                "Analyze qualified applicants only",
                value=False,
                help="Optional cohort filter; changing the denominator can change the results.",
            )
            if analyze_qualified_only:
                preferred_qualified_values = [1, "1", True, "Yes", "yes"]
                qualified_index = next(
                    (
                        qualified_values.index(value)
                        for value in preferred_qualified_values
                        if value in qualified_values
                    ),
                    0,
                )
                qualified_value = st.selectbox(
                    "Qualified value", qualified_values, index=qualified_index
                )

analysis_data = data
if analyze_qualified_only:
    analysis_data = data.loc[data["qualified"].eq(qualified_value)]

analysis_rows = analysis_data[[group_column, outcome_column]].dropna()
group_values = analysis_rows[group_column].unique().tolist()
outcome_values = analysis_rows[outcome_column].unique().tolist()
if not group_values:
    st.error("No rows have both a group value and an outcome value.")
    st.stop()
if not outcome_values:
    st.error("No non-missing outcome values are available for this analysis.")
    st.stop()

with st.sidebar:
    preferred_outcomes = [1, "1", True, "Yes", "yes", "Hired", "hired"]
    favorable_index = next(
        (
            outcome_values.index(value)
            for value in preferred_outcomes
            if value in outcome_values
        ),
        0,
    )
    favorable_value = st.selectbox(
        "Favorable outcome value",
        outcome_values,
        index=favorable_index,
        format_func=str,
        help="For example, select 'Yes' or 'Hired' when that represents a favorable decision.",
    )
    reference_rates = (
        analysis_rows.assign(
            _favorable=analysis_rows[outcome_column].eq(favorable_value)
        )
        .groupby(group_column, sort=False)["_favorable"]
        .mean()
    )
    default_reference = reference_rates.idxmax()
    reference_group = st.selectbox(
        "Reference group",
        group_values,
        index=group_values.index(default_reference),
        format_func=str,
        help="Impact ratios compare each other group's selection rate to this group's rate.",
    )

results = calculate_adverse_impact(
    analysis_data,
    group_column,
    outcome_column,
    favorable_value,
    reference_group,
)
if results.empty:
    st.error("No rows have both a group value and an outcome value.")
    st.stop()

reference_result = results.loc[results["Group"].eq(reference_group)].iloc[0]
flagged_count = int(results["Below 0.80"].sum())
included_rows = int(results["eligible"].sum())

metric_columns = st.columns(4)
metric_columns[0].metric("Rows in CSV", f"{len(data):,}")
metric_columns[1].metric("Rows analyzed", f"{included_rows:,}")
metric_columns[2].metric(
    "Reference selection rate", f"{reference_result['selection_rate']:.1%}"
)
metric_columns[3].metric("Groups below 0.80", f"{flagged_count:,}")

st.subheader("Selection rates by group")
st.caption(f"Dataset: {data_source}")
chart_data = results.sort_values("selection_rate").set_index("Group")[
    ["selection_rate"]
]
st.bar_chart(chart_data)

st.subheader("Group comparison")
display_results = results.rename(
    columns={
        "eligible": "Eligible rows",
        "selected": "Favorable outcomes",
        "selection_rate": "Selection rate",
        "Rate difference (pp)": "Rate difference (percentage points)",
        "Impact ratio": "Adverse impact ratio",
        "Below 0.80": "Below 0.80 benchmark",
    }
)
st.dataframe(
    display_results.style.format(
        {
            "Selection rate": "{:.1%}",
            "Rate difference (percentage points)": "{:+.1f}",
            "Adverse impact ratio": "{:.2f}",
        },
        na_rep="N/A",
    ),
    width="stretch",
    hide_index=True,
)

if reference_result["selection_rate"] == 0:
    st.warning(
        "The reference group has a 0% selection rate, so impact ratios for "
        "other groups are undefined. Choose a different reference group if appropriate."
    )
elif flagged_count:
    st.warning(
        f"{flagged_count} group(s) have an observed selection rate below 80% of "
        "the selected reference group's rate. Review the underlying context and data."
    )
else:
    st.success("No non-reference group falls below the 0.80 screening benchmark.")

with st.expander("About this calculation"):
    st.markdown(
        """
        - **Selection rate:** favorable outcomes divided by rows with non-missing
          group and outcome values.
        - **Adverse impact ratio:** a group's selection rate divided by the selected
          reference group's selection rate.
        - **0.80 benchmark:** ratios below 0.80 are flagged for review. This
          screening result does not account for sample size, job-related factors,
          statistical uncertainty, or applicable legal requirements.
        """
    )

with st.expander("Preview uploaded data"):
    st.dataframe(data.head(100), width="stretch")
    if len(data) > 100:
        st.caption("Showing the first 100 rows.")
