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
st.set_page_config(page_title="NexaAudit – Temple Crowd Dashboard", layout="wide")
TEMPLES = ["Somnath", "Dwarka", "Ambaji", "Pavagadh"]
DATA_FILE = "temple_pulse.csv"
ALERT_EMAIL = "temple-alert@example.com"  # Replace with actual recipient

# -------------------- DATA INIT --------------------
def load_data():
    try:
        return pd.read_csv(DATA_FILE)
    except:
        return pd.DataFrame(columns=[
            "timestamp", "temple", "zone", "visitor_count", "queue_time",
            "top_services", "payment_modes", "crowd_index", "peak_hour_flag"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# -------------------- ALERT FUNCTION --------------------
def send_alert_email(subject, body):
    sender = "nexaaudit-alert@example.com"
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
        st.success("Alert dispatched to temple authorities.")
    except Exception as e:
        st.error(f"Failed to send alert: {e}")

# -------------------- SIDEBAR --------------------
st.sidebar.title("Temple Navigation")
page = st.sidebar.radio("Choose View", [
    "Submit Pilgrim Pulse", "Temple Overview", "Crowd Alerts",
    "Pilgrim Info", "Export Records", "Recent Logs"
])

# -------------------- PAGE 1: SUBMISSION FORM --------------------
if page == "Submit Pilgrim Pulse":
    st.title("Submit Daily Temple Pulse")
    with st.form("pulse_form"):
        temple = st.selectbox("Temple Site", TEMPLES)
        zone = st.text_input("Service Zone (e.g., Entry Gate, Prasad Counter)")
        visitor_count = st.number_input("Visitor Count", min_value=0)
        queue_time = st.number_input("Average Queue Time (minutes)", min_value=0)
        top_services = st.text_input("Top Services / Requests")
        payment_modes = st.multiselect("Payment Modes", ["Cash", "Card", "UPI", "Wallet"])
        crowd_index = st.slider("Crowd Index (0 = Empty, 10 = Overwhelmed)", 0, 10)
        peak_hour_flag = st.checkbox("Is this during peak hours?")
        submitted = st.form_submit_button("Submit Pulse")

    if submitted:
        data = load_data()
        new_entry = pd.DataFrame([{
            "timestamp": datetime.datetime.now(),
            "temple": temple,
            "zone": zone,
            "visitor_count": visitor_count,
            "queue_time": queue_time,
            "top_services": top_services,
            "payment_modes": ",".join(payment_modes),
            "crowd_index": crowd_index,
            "peak_hour_flag": peak_hour_flag
        }])
        updated_data = pd.concat([data, new_entry], ignore_index=True)
        save_data(updated_data)
        st.success("Pulse submitted successfully.")
        st.experimental_rerun()

# -------------------- PAGE 2: TEMPLE OVERVIEW --------------------
elif page == "Temple Overview":
    st.title("Temple-Wise Crowd Overview")
    data = load_data()
    temple = st.selectbox("Select Temple", TEMPLES)
    filtered = data[data["temple"] == temple]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Crowd Index", round(filtered["crowd_index"].mean(), 2))
        st.metric("Average Queue Time", round(filtered["queue_time"].mean(), 2))
    with col2:
        fig = px.bar(filtered, x="zone", y="visitor_count", color="zone", title="Zone-Wise Visitor Count")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Crowd Heatmap")
    if not filtered.empty:
        m = folium.Map(location=[22.5, 71.5], zoom_start=6)
        for _, row in filtered.iterrows():
            lat = np.random.uniform(21, 24)
            lon = np.random.uniform(70, 74)
            folium.CircleMarker(
                location=[lat, lon],
                radius=row["crowd_index"],
                popup=f"{row['temple']} – {row['zone']} ({row['crowd_index']})",
                color="darkred",
                fill=True
            ).add_to(m)
        st_folium(m, width=700)

# -------------------- PAGE 3: CROWD ALERTS --------------------
elif page == "Crowd Alerts":
    st.title("Real-Time Crowd and Safety Alerts")
    data = load_data()
    if len(data) < 10:
        st.warning("Insufficient data for anomaly detection.")
    else:
        model = IsolationForest(contamination=0.1)
        features = data[["visitor_count", "queue_time", "crowd_index"]]
        data["anomaly"] = model.fit_predict(features)
        alerts = data[data["anomaly"] == -1]

        for _, row in alerts.iterrows():
            alert_msg = f"Alert: Unusual crowd at {row['temple']} – {row['zone']} | Index {row['crowd_index']}, Queue {row['queue_time']} mins"
            st.error(alert_msg)
            send_alert_email(
                subject=f"Temple Alert – {row['temple']} Zone: {row['zone']}",
                body=alert_msg
            )

# -------------------- PAGE 4: PILGRIM INFO --------------------
elif page == "Pilgrim Info":
    st.title("Pilgrim Crowd Snapshot")
    data = load_data()
    temple = st.selectbox("Temple", TEMPLES)
    latest = data[data["temple"] == temple].sort_values("timestamp", ascending=False).head(1)

    if latest.empty:
        st.info("No recent data available for this temple.")
    else:
        row = latest.iloc[0]
        st.metric("Crowd Index", row["crowd_index"])
        st.metric("Queue Time", f"{row['queue_time']} mins")
        st.write(f"Top Services: {row['top_services']}")
        st.write(f"Payment Modes: {row['payment_modes']}")
        if row["peak_hour_flag"]:
            st.warning("Peak hour detected – expect delays.")

# -------------------- PAGE 5: EXPORT RECORDS --------------------
elif page == "Export Records":
    st.title("Export Temple Pulse Records")
    data = load_data()
    export_format = st.radio("Choose Format", ["CSV", "Excel"])
    if export_format == "CSV":
        st.download_button("Download CSV", data.to_csv(index=False), file_name="temple_pulse.csv")
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            data.to_excel(writer, index=False, sheet_name='TemplePulse')
        st.download_button("Download Excel", output.getvalue(), file_name="temple_pulse.xlsx")

# -------------------- PAGE 6: RECENT LOGS --------------------
elif page == "Recent Logs":
    st.title("Recent Pulse Logs")
    data = load_data()
    st.dataframe(data.sort_values("timestamp", ascending=False).head(20))

# -------------------- FOOTER --------------------
st.markdown("---")
st.caption("Built for Temple Governance • Privacy-Safe • Scalable • Open Source")
