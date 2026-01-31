# -------------------------------------------------
# EDA on DOHMH + IoT merged dataset (from Jan 2015 or later)
# -------------------------------------------------

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scipy import stats

# Set visualization style
sns.set(style="whitegrid", palette="muted", font_scale=1.1)

# Create folder for saving plots
os.makedirs("plots", exist_ok=True)

# -------------------------------------------------
# 1. Load Dataset
# -------------------------------------------------
df = pd.read_csv("merged_inspection_iot_data_full.csv", low_memory=False)

print("Dataset shape:", df.shape)
print("\nColumns:", df.columns.tolist())

# -------------------------------------------------
# 2. Data Overview
# -------------------------------------------------
print("\nMissing values per column:")
print(df.isnull().sum())

print("\nBasic statistics (numeric only):")
print(df.describe())

# -------------------------------------------------
# 3. Inspection Score & Grade Distribution
# -------------------------------------------------
plt.figure(figsize=(8,5))
sns.histplot(df['SCORE'].dropna(), bins=30, kde=True, color="skyblue")
plt.title("Distribution of Inspection Scores")
plt.xlabel("Score")
plt.ylabel("Count")
plt.savefig("plots/inspection_score_distribution.png")
plt.show()

plt.figure(figsize=(6,4))
sns.countplot(x="GRADE", data=df, order=df['GRADE'].dropna().unique())
plt.title("Distribution of Restaurant Grades")
plt.savefig("plots/grade_distribution.png")
plt.show()

# -------------------------------------------------
# 4. Violation Patterns
# -------------------------------------------------
if "VIOLATION CODE" in df.columns:
    top_violations = df['VIOLATION CODE'].value_counts().head(10)
    plt.figure(figsize=(10,6))
    sns.barplot(x=top_violations.values, y=top_violations.index, 
                palette="viridis", hue=None, legend=False)
    plt.title("Top 10 Most Frequent Violation Codes")
    plt.xlabel("Count")
    plt.ylabel("Violation Code")
    plt.savefig("plots/top10_violations.png")
    plt.show()

# -------------------------------------------------
# 5. IoT Sensor Variables
# -------------------------------------------------
iot_vars = ["Temperature_F","Humidity_percent","Air_Quality_Index","Surface_Score"]

df[iot_vars].hist(bins=20, figsize=(10,8), color="lightcoral")
plt.suptitle("Distribution of IoT Sensor Readings")
plt.savefig("plots/iot_distributions.png")
plt.show()

# -------------------------------------------------
# 6. IoT vs Inspection Outcomes
# -------------------------------------------------
plt.figure(figsize=(8,6))
sns.boxplot(x="Risk_Flag", y="SCORE", data=df, order=["normal","warning","high"])
plt.title("Inspection Scores by IoT Risk Category")
plt.savefig("plots/score_by_riskflag.png")
plt.show()

plt.figure(figsize=(10,8))
corr = df[iot_vars + ["SCORE"]].corr()
sns.heatmap(corr, annot=True, cmap="coolwarm", center=0)
plt.title("Correlation: IoT Variables vs Inspection Score")
plt.savefig("plots/iot_correlation_heatmap.png")
plt.show()

# -------------------------------------------------
# 7. Borough-Level Analysis
# -------------------------------------------------
plt.figure(figsize=(8,5))
sns.countplot(x="BORO", hue="GRADE", data=df, order=df['BORO'].value_counts().index)
plt.title("Grades by Borough")
plt.legend(title="Grade")
plt.savefig("plots/grades_by_borough.png")
plt.show()

# -------------------------------------------------
# 8. Temporal Analysis - Inspections (Smart Date)
# -------------------------------------------------
df['INSPECTION DATE'] = pd.to_datetime(df['INSPECTION DATE'], errors="coerce")
df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors="coerce")

first_date = df['INSPECTION DATE'].min()
cutoff_date = pd.to_datetime("2022-01-01")
start_date = max(first_date, cutoff_date)

print("Earliest inspection date:", first_date)
print("Using start date for plots:", start_date)

df_filtered = df[df['INSPECTION DATE'] >= start_date].copy()

df_filtered.loc[:, 'Inspection_Year'] = df_filtered['INSPECTION DATE'].dt.year
df_filtered.loc[:, 'Inspection_Month'] = df_filtered['INSPECTION DATE'].dt.to_period('M')

# Monthly inspection counts
monthly_counts = df_filtered.groupby('Inspection_Month')['CAMIS'].count()
monthly_counts.plot(kind="line", marker="o", figsize=(12,5), color="purple")
plt.title(f"Monthly Trend of Inspections (from {start_date:%b %Y})")
plt.xlabel("Month")
plt.ylabel("Number of Inspections")
plt.savefig("plots/inspections_trend.png")
plt.show()

# Monthly average scores
monthly_scores = df_filtered.groupby('Inspection_Month')['SCORE'].mean()
monthly_scores.plot(kind="line", marker="o", figsize=(12,5), color="darkred")
plt.title(f"Average Inspection Score by Month (from {start_date:%b %Y})")
plt.xlabel("Month")
plt.ylabel("Average Score")
plt.savefig("plots/avg_score_by_month.png")
plt.show()

# -------------------------------------------------
# 9. Temporal Analysis - IoT Readings (Aligned with Start Date)
# -------------------------------------------------
df_filtered_iot = df[df['Timestamp'] >= start_date].copy()

df_filtered_iot.loc[:, 'IoT_Date'] = df_filtered_iot['Timestamp'].dt.date
df_filtered_iot.loc[:, 'IoT_Hour'] = df_filtered_iot['Timestamp'].dt.hour

# Daily averages
daily_iot = df_filtered_iot.groupby('IoT_Date')[iot_vars].mean()
daily_iot.plot(figsize=(12,8), subplots=True,
               title=["Daily Avg Temperature","Daily Avg Humidity","Daily Avg Air Quality","Daily Avg Surface Score"])
plt.tight_layout()
plt.savefig("plots/daily_iot_trends.png")
plt.show()

# Hourly patterns
plt.figure(figsize=(10,6))
sns.lineplot(x="IoT_Hour", y="Temperature_F", data=df_filtered_iot, errorbar=None, label="Temperature")
sns.lineplot(x="IoT_Hour", y="Humidity_percent", data=df_filtered_iot, errorbar=None, label="Humidity")
plt.title(f"Hourly IoT Patterns (Temperature & Humidity, from {start_date:%b %Y})")
plt.xlabel("Hour of Day")
plt.ylabel("Average Value")
plt.legend()
plt.savefig("plots/hourly_iot_patterns.png")
plt.show()

# -------------------------------------------------
# 10. Export Summary Tables
# -------------------------------------------------
summary = {}
summary['grade_counts'] = df['GRADE'].value_counts(dropna=False)
if "VIOLATION CODE" in df.columns:
    summary['top_violations'] = df['VIOLATION CODE'].value_counts().head(10)
summary['monthly_avg_scores'] = monthly_scores
summary['monthly_counts'] = monthly_counts
summary['daily_iot'] = daily_iot

with pd.ExcelWriter("EDA_Summary.xlsx") as writer:
    for name, table in summary.items():
        if isinstance(table, pd.Series):
            table.to_frame().to_excel(writer, sheet_name=name)
        else:
            table.to_excel(writer, sheet_name=name)

print("\n✅ Export complete! Summary tables saved as 'EDA_Summary.xlsx'")

# -------------------------------------------------
# 11. Statistical Analysis Report
# -------------------------------------------------
report_lines = []
report_lines.append("STATISTICAL ANALYSIS REPORT")
report_lines.append("="*40)
report_lines.append(f"Start Date for Analysis: {start_date:%b %Y}")
report_lines.append(f"Total Records: {len(df)}")
report_lines.append(f"Filtered Records (after {start_date:%b %Y}): {len(df_filtered)}\n")

report_lines.append("Grade Distribution (counts):")
report_lines.append(str(summary['grade_counts'].to_string()))
report_lines.append("")

report_lines.append("Inspection Score Summary (after filtering):")
report_lines.append(str(df_filtered['SCORE'].describe().to_string()))
report_lines.append("")

report_lines.append("IoT Sensor Summary Statistics (after filtering):")
report_lines.append(str(df_filtered_iot[iot_vars].describe().to_string()))
report_lines.append("")

report_lines.append("Correlation Matrix (IoT vs Score):")
report_lines.append(str(corr.to_string()))
report_lines.append("")

risk_groups = df_filtered[['Risk_Flag','SCORE']].dropna()
if not risk_groups.empty:
    normal_scores = risk_groups[risk_groups['Risk_Flag']=="normal"]['SCORE']
    high_scores = risk_groups[risk_groups['Risk_Flag']=="high"]['SCORE']
    if len(normal_scores) > 30 and len(high_scores) > 30:
        t_stat, p_val = stats.ttest_ind(normal_scores, high_scores, equal_var=False)
        report_lines.append("Hypothesis Test: Do high-risk restaurants have higher inspection scores?")
        report_lines.append(f"T-statistic = {t_stat:.3f}, P-value = {p_val:.5f}")
        report_lines.append("Result: " + ("Significant difference (reject null hypothesis)." if p_val < 0.05 else "No significant difference (fail to reject null)."))
        report_lines.append("")

with open("Statistical_Report.txt", "w") as f:
    f.write("\n".join(report_lines))

print("✅ Statistical report saved as 'Statistical_Report.txt'")
