# tabbed_dashboard_app.py frontend code
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from io import BytesIO
from textblob import TextBlob
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

API_URL = "http://127.0.0.1:5000"  # Flask backend

st.set_page_config(page_title="Performance Pulse Dashboard", layout="wide")
st.title("📊 Performance Pulse Dashboard")
st.markdown("HR Analytics — Real-time Employee Performance & Feedback Monitoring")

# ---------------------------
# Fetch Data
# ---------------------------
@st.cache_data(ttl=30)
def fetch_data():
    try:
        data_resp = requests.get(f"{API_URL}/api/data", timeout=4)
        metrics_resp = requests.get(f"{API_URL}/api/metrics", timeout=4)
        data_resp.raise_for_status()
        metrics_resp.raise_for_status()
        df = pd.DataFrame(data_resp.json())
        metrics = metrics_resp.json()
        return df, metrics, None
    except Exception as e:
        return None, None, str(e)

df, metrics, error = fetch_data()
if error:
    st.error("⚠️ Unable to connect to backend API. Please run Flask first.")
    st.caption(f"Debug: {error}")
    st.stop()

# ---------------------------
# Sentiment Analysis
# ---------------------------
if "Feedback" in df.columns:
    st.sidebar.info("💬 Feedback detected — sentiment analysis enabled.")
    df["SentimentScore"] = df["Feedback"].apply(lambda x: TextBlob(str(x)).sentiment.polarity)
    df["SentimentLabel"] = df["SentimentScore"].apply(
        lambda s: "Positive" if s > 0.2 else ("Negative" if s < -0.2 else "Neutral")
    )
else:
    df["SentimentScore"] = 0
    df["SentimentLabel"] = "N/A"

# ---------------------------
# Sidebar Filters
# ---------------------------
st.sidebar.header("🔍 Filters")
departments = ["All"] + sorted(df["Department"].unique())
selected_dept = st.sidebar.selectbox("Department", departments)

min_exp, max_exp = int(df["ExperienceYears"].min()), int(df["ExperienceYears"].max())
exp_range = st.sidebar.slider("Experience (years)", min_exp, max_exp, (min_exp, max_exp))

perf_range = st.sidebar.slider(
    "Performance Score Range",
    float(df["PerformanceScore"].min()),
    float(df["PerformanceScore"].max()),
    (float(df["PerformanceScore"].min()), float(df["PerformanceScore"].max()))
)

refresh = st.sidebar.button("🔄 Refresh Data")
if refresh:
    st.cache_data.clear()
    time.sleep(0.2)
    df, metrics, error = fetch_data()
    if error:
        st.error("⚠️ Could not refresh data.")
        st.stop()

# Apply filters
filtered = df.copy()
if selected_dept != "All":
    filtered = filtered[filtered["Department"] == selected_dept]
filtered = filtered[
    (filtered["ExperienceYears"] >= exp_range[0]) & 
    (filtered["ExperienceYears"] <= exp_range[1]) &
    (filtered["PerformanceScore"] >= perf_range[0]) & 
    (filtered["PerformanceScore"] <= perf_range[1])
]

# ---------------------------
# Export Function
# ---------------------------
def export_to_pdf(dataframe):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 770, "Performance Pulse Dashboard - Report")
    c.setFont("Helvetica", 10)
    c.drawString(50, 750, f"Department Filter: {selected_dept}")
    c.drawString(50, 735, f"Employees Shown: {len(dataframe)}")
    y = 710
    for _, row in dataframe.head(25).iterrows():
        c.drawString(50, y, f"{row['Name']} | {row['Department']} | Score: {row['PerformanceScore']:.2f} | Salary: ₹{int(row['MonthlySalary'])}")
        y -= 15
        if y < 50:
            c.showPage()
            y = 770
    c.save()
    buffer.seek(0)
    return buffer

st.sidebar.download_button("📥 Export Filtered CSV", data=filtered.to_csv(index=False).encode('utf-8'), file_name="filtered_data.csv", mime="text/csv")
pdf_buffer = export_to_pdf(filtered)
st.sidebar.download_button("📄 Export as PDF", data=pdf_buffer, file_name="performance_report.pdf", mime="application/pdf")

# ---------------------------
# Tabs for Layout
# ---------------------------
tabs = st.tabs(["Overview", "Department Analytics", "Top Performers", "Feedback"])

# ---------------------------
# Tab 1: Overview
# ---------------------------
with tabs[0]:
    st.subheader("📊 Key Metrics")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("⭐ Avg Performance", round(filtered["PerformanceScore"].mean(),2))
    k2.metric("💰 Avg Salary", f"₹{int(filtered['MonthlySalary'].mean()):,}")
    k3.metric("📅 Avg Attendance", f"{round(filtered['AttendanceRate (%)'].mean(),1)}%")
    k4.metric("👥 Employees", len(filtered))
    if "Feedback" in df.columns:
        avg_sentiment = filtered["SentimentScore"].mean()
        label = "😊 Positive" if avg_sentiment > 0.2 else ("😐 Neutral" if avg_sentiment > -0.2 else "😞 Negative")
        k5.metric("💬 Sentiment", label)
    
    st.divider()

    st.subheader("💰 Salary Distribution")
    fig_salary = px.histogram(filtered, x="MonthlySalary", nbins=30, color_discrete_sequence=["#636EFA"])
    st.plotly_chart(fig_salary, use_container_width=True)

    st.subheader("📈 Attendance vs Performance")
    fig_scatter = px.scatter(filtered, x="AttendanceRate (%)", y="PerformanceScore",
                             color="Department", size="ExperienceYears", hover_name="Name",
                             color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------
# Tab 2: Department Analytics
# ---------------------------
with tabs[1]:
    st.subheader("🏢 Department-wise Avg Performance")
    dept_df = filtered.groupby("Department")["PerformanceScore"].mean().round(2).reset_index()
    fig_dept = px.bar(dept_df, x="Department", y="PerformanceScore", text="PerformanceScore",
                      color="PerformanceScore", color_continuous_scale="Viridis",
                      title="Average Performance by Department")
    st.plotly_chart(fig_dept, use_container_width=True)

    st.subheader("🏆 Performance Levels by Department")
    perf_df = filtered.groupby(["Department","Performance_Level"]).size().reset_index(name="Count")
    fig_perf = px.bar(perf_df, x="Department", y="Count", color="Performance_Level",
                      text="Count", color_discrete_sequence=px.colors.qualitative.Safe,
                      title="High/Medium/Low Performance by Department")
    st.plotly_chart(fig_perf, use_container_width=True)

# ---------------------------
# Tab 3: Top Performers
# ---------------------------
with tabs[2]:
    st.subheader("🏅 Top 10 Performers")
    top10 = filtered.sort_values("PerformanceScore", ascending=False).head(10)
    fig_top10 = px.bar(top10, x="Name", y="PerformanceScore", color="Department",
                       text="PerformanceScore", color_discrete_sequence=px.colors.qualitative.Bold)
    st.plotly_chart(fig_top10, use_container_width=True)

    st.subheader("📝 Top Performers Table")
    st.dataframe(top10[["Name","Department","PerformanceScore","MonthlySalary","ExperienceYears"]])

# ---------------------------
# Tab 4: Feedback & Sentiment
# ---------------------------
with tabs[3]:
    if "Feedback" in df.columns:
        st.subheader("💬 Sentiment Distribution")
        sentiment_counts = filtered["SentimentLabel"].value_counts().reset_index()
        sentiment_counts.columns = ["Sentiment","Count"]
        fig_sent = px.pie(sentiment_counts, names="Sentiment", values="Count",
                          color="Sentiment", color_discrete_map={"Positive":"green","Neutral":"orange","Negative":"red"},
                          title="Overall Sentiment Distribution")
        st.plotly_chart(fig_sent, use_container_width=True)

        if st.checkbox("Show Raw Feedback"):
            st.dataframe(filtered[["Name","Department","Feedback","SentimentLabel"]].head(50))
    else:
        st.info("No feedback data available.")
    
st.caption("Data sourced from Flask backend | Includes sentiment analysis & export features")