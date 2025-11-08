#app.py backend code
import pandas as pd
from flask import Flask, jsonify

# ---------------------------
# 1️⃣ Load and Process Dataset
# ---------------------------
df = pd.read_csv("employee_performance_200.csv")

# Handle missing values
df.fillna(0, inplace=True)

# Derived metrics
df['Efficiency (%)'] = (df['ProjectsCompleted'] / df['ExperienceYears'].replace(0, 1)) * 10
df['Performance_Level'] = df['PerformanceScore'].apply(
    lambda x: 'High' if x >= 4.5 else 'Medium' if x >= 3.5 else 'Low'
)

# Save cleaned dataset
df.to_csv("processed_data.csv", index=False)
print("✅ Data cleaned and processed successfully!")

# ---------------------------
# 2️⃣ Compute Core Metrics
# ---------------------------
avg_perf = round(df['PerformanceScore'].mean(), 2)
avg_salary = round(df['MonthlySalary'].mean(), 2)
avg_attendance = round(df['AttendanceRate (%)'].mean(), 2)
top_performer = df.loc[df['PerformanceScore'].idxmax(), 'Name']
top_dept = df.groupby('Department')['PerformanceScore'].mean().idxmax()

# ---------------------------
# 3️⃣ Flask Backend Setup
# ---------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Performance Pulse Backend is Running Successfully!"

# ✅ Route 1: Get Processed Data
@app.route('/api/data')
def get_data():
    df = pd.read_csv('processed_data.csv')
    return jsonify(df.to_dict(orient='records'))

# ✅ Route 2: Get Summary Metrics (JSON API)
@app.route('/api/metrics')
def get_metrics():
    df = pd.read_csv('processed_data.csv')
    metrics = {
        "Average Performance Score": round(df['PerformanceScore'].mean(), 2),
        "Average Salary": round(df['MonthlySalary'].mean(), 2),
        "Average Attendance (%)": round(df['AttendanceRate (%)'].mean(), 2),
        "Top Performer": df.loc[df['PerformanceScore'].idxmax(), 'Name'],
        "Top Department": df.groupby('Department')['PerformanceScore'].mean().idxmax(),
        "High Performers Count": int((df['Performance_Level'] == 'High').sum()),
        "Total Employees": len(df)
    }
    return jsonify(metrics)

# ✅ Route 3: Department-Wise Average Scores
@app.route('/api/department')
def get_department_stats():
    df = pd.read_csv('processed_data.csv')
    dept_stats = (
        df.groupby('Department')['PerformanceScore']
        .mean()
        .round(2)
        .to_dict()
    )
    return jsonify(dept_stats)

# ---------------------------
# 4️⃣ Run the Server
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)