# Fair Adverse Impact Dashboard

A Streamlit dashboard for reviewing selection outcomes across applicant groups. It
loads `FAIR_Synthetic_Applicant_Data_2.csv` by default and lets you replace it with
another CSV from the sidebar.

## Run locally

1. Install the requirements:

   ```sh
   pip install -r requirements.txt
   ```

2. Start the dashboard:

   ```sh
   streamlit run streamlit_app.py
   ```

## Dashboard controls

- Choose a group/protected-attribute column and a decision/outcome column.
- Choose which outcome value counts as favorable and which group is the reference.
- For datasets with a `qualified` column, optionally restrict the analysis to one
  qualified value. This changes the analysis population and denominator.
- Replace the bundled dataset by uploading a CSV in the sidebar.
- Open the **Resources** page in the Streamlit navigation to access the original
  [FAIR calculator](https://orgtools.shinyapps.io/FAIR/).

The supplied synthetic applicant dataset contains `gender`, `race_ethnicity`,
`age_group`, `minority_group`, `qualified`, and `selected` fields. The dashboard
defaults to comparing `race_ethnicity` groups using `selected = 1`.

## Metrics and limitations

Selection rate is favorable outcomes divided by rows with non-missing group and
outcome values. The adverse impact ratio is a group's selection rate divided by
the selected reference group's rate. Ratios below 0.80 are flagged for review;
the reference group is selected by default as the group with the highest observed
rate, but can be changed.

The 0.80 benchmark is a screening rule of thumb, not a legal conclusion or proof
of fairness. The dashboard does not account for sample size, statistical
uncertainty, job-related factors, or applicable legal requirements. Interpret
results in context.
