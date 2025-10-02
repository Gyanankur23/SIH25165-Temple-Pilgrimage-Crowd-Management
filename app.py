import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import IsolationForest
import smtplib
from email.mime.text import MIMEText
from io import BytesIO

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Temple Crowd Pulse Dashboard", layout="wide")
TEMPLES = ["Somnath", "Dwarka", "Ambaji", "Pavagadh"]
DATA_FILE = "temple_pulse.csv"
ALERT_EMAIL = "your-alert-email@example.com"  # Replace with actual recipient

# -------------------- DATA INIT --------------------
def load_data():
    try:
        return pd.read_csv(DATA_FILE)
    except:
        return pd.DataFrame(columns=[
            "timestamp", "temple", "visitor_count", "top_requests",
            "queue_time", "payment_modes", "crowd_index"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# -------------------- ALERT FUNCTION --------------------
def send_alert_email(subject, body):
    sender = "your-sender-email@example.com"
    password = "your-email-password"  # Use secrets.toml in production
    recipient = ALERT_EMAIL

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        st.success(" Alert email sent successfully!")
    except Exception as e:
        st.error(f" Failed to send alert: {e}")

# -------------------- SIDEBAR --------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [" Submit Pulse", " Temple Dashboard", " Alerts", " Pilgrim View", " Export", " Recent Submissions"])

# -------------------- PAGE 1: SUBMISSION FORM --------------------
if page == " Submit Pulse":
    st.title(" Submit Daily Temple Pulse")
    with st.form("pulse_form"):
        temple = st.selectbox("Temple", TEMPLES)
        visitor_count = st.number_input("Visitor Count", min_value=0)
        top_requests = st.text_input("Top Requests / Services")
        queue_time = st.number_input("Average Queue Time (minutes)", min_value=0)
        payment_modes = st.multiselect("Payment Breakdown", ["Cash", "Card", "UPI", "Wallet"])
        crowd_index = st.slider("Crowd Index (0 = Empty, 10 = Overwhelmed)", 0, 10)
        submitted = st.form_submit_button("Submit")

    if submitted:
        data = load_data()
        new_entry = pd.DataFrame([{
            "timestamp": datetime.datetime.now(),
            "temple": temple,
            "visitor_count": visitor_count,
            "top_requests": top_requests,
            "queue_time": queue_time,
            "payment_modes": ",".join(payment_modes),
            "crowd_index": crowd_index
        }])
        updated_data = pd.concat([data, new_entry], ignore_index=True)
        save_data(updated_data)
        st.success("✅ Data submitted successfully!")
        st.experimental_rerun()

# -------------------- PAGE 2: DASHBOARD --------------------
elif page == " Temple Dashboard":
    st.title(" Temple-Wise Crowd Dashboard")
    data = load_data()
    temple = st.selectbox("Select Temple", TEMPLES)
    filtered = data[data["temple"] == temple]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Crowd Index", round(filtered["crowd_index"].mean(), 2))
        st.metric("Average Queue Time", round(filtered["queue_time"].mean(), 2))
    with col2:
        fig = px.histogram(filtered, x="timestamp", y="visitor_count", title="Visitor Count Over Time")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(" Crowd Heatmap")
    if not filtered.empty:
        m = folium.Map(location=[22.5, 71.5], zoom_start=6, control_scale=True)
        for _, row in filtered.iterrows():
            lat = np.random.uniform(21, 24)
            lon = np.random.uniform(70, 74)
            folium.CircleMarker(
                location=[lat, lon],
                radius=row["crowd_index"],
                popup=f"{row['temple']} ({row['crowd_index']})",
                color="red",
                fill=True
            ).add_to(m)
        st_folium(m, width=700)

# -------------------- PAGE 3: ALERTS --------------------
elif page == " Alerts":
    st.title(" Real-Time Crowd & Anomaly Alerts")
    data = load_data()
    if len(data) < 10:
        st.warning("Not enough data for anomaly detection.")
    else:
        model = IsolationForest(contamination=0.1)
        features = data[["visitor_count", "queue_time", "crowd_index"]]
        data["anomaly"] = model.fit_predict(features)
        alerts = data[data["anomaly"] == -1]

        for _, row in alerts.iterrows():
            alert_msg = f"⚠️ Alert: Unusual activity at {row['temple']} — Crowd Index {row['crowd_index']}, Queue Time {row['queue_time']} mins"
            st.error(alert_msg)
            send_alert_email(
                subject=f"Alert: Crowd anomaly at {row['temple']}",
                body=alert_msg
            )

# -------------------- PAGE 4: PILGRIM VIEW --------------------
elif page == " Pilgrim View":
    st.title(" Pilgrim Pulse — Check Crowd Levels")
    data = load_data()
    temple = st.selectbox("Your Temple", TEMPLES)
    latest = data[data["temple"] == temple].sort_values("timestamp", ascending=False).head(1)

    if latest.empty:
        st.info("No recent data available for your selection.")
    else:
        row = latest.iloc[0]
        st.metric("Crowd Index", row["crowd_index"])
        st.metric("Queue Time", f"{row['queue_time']} mins")
        st.write(f"Top Requests: {row['top_requests']}")
        st.write(f"Payment Modes: {row['payment_modes']}")

# -------------------- PAGE 5: EXPORT --------------------
elif page == " Export":
    st.title(" Export Data for Temple Authorities")
    data = load_data()
    export_format = st.radio("Choose Format", ["CSV", "Excel"])
    if export_format == "CSV":
        st.download_button("Download CSV", data.to_csv(index=False), file_name="temple_pulse.csv")
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            data.to_excel(writer, index=False, sheet_name='TemplePulse')
        st.download_button("Download Excel", output.getvalue(), file_name="temple_pulse.xlsx")

# -------------------- PAGE 6: RECENT SUBMISSIONS --------------------
elif page == " Recent Submissions":
    st.title(" Recent Pulse Submissions")
    data = load_data()
    st.dataframe(data.sort_values("timestamp", ascending=False).head(20))

# -------------------- FOOTER --------------------
st.markdown("---")
st.caption("Built for Temple Governance • Privacy-Safe • Scalable • Open Source")
