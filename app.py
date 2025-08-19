
from flask import Flask, render_template
import threading, time, json, requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
sent_alarms = set()
cleared_alarms = set()
all_alarms = []

def load_urls():
    with open("urls.json") as f:
        return json.load(f)

def send_alert(message):
    token = "7288605319:AAFOhRPXge5PA3SbB3Oy-97o6MerZTWvqVw"
    chat_id = "1405885003"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print("Telegram Error:", e)

def fetch_alarms():
    global all_alarms
    urls = load_urls()
    current_alarms = []
    for entry in urls:
        name = entry["name"]
        url = entry["url"]
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr")[1:]

            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 10:
                    alarm_id = cols[0].text.strip()
                    start = cols[1].text.strip()
                    end = cols[2].text.strip()
                    olt = cols[3].text.strip()
                    message = cols[4].text.strip()
                    ip = cols[5].text.strip()
                    severity = cols[6].text.strip()
                    ack = cols[7].text.strip()
                    action = cols[8].text.strip()
                    area = cols[9].text.strip()

                    try:
                        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            start_dt = datetime.strptime(start, "%d/%m/%Y %H:%M")
                        except:
                            start_dt = None

                    if start:
                        if not end:
                            if alarm_id not in sent_alarms:
                                send_alert(
                                    f"🚨 <b>ALARM BARU</b>\n"
                                    f"OLT: {olt}\n"
                                    f"Message: {message}\n"
                                    f"Severity: {severity}\n"
                                    f"Start: {start}\n"
                                    f"IP: {ip}\n"
                                    f"Area: {area}"
                                )
                                sent_alarms.add(alarm_id)

                            current_alarms.append({
                                "id": alarm_id,
                                "olt": olt,
                                "start": start,
                                "start_dt": start_dt,
                                "message": message,
                                "severity": severity,
                                "ip": ip,
                                "area": area
                            })
                        else:
                            if alarm_id in sent_alarms and alarm_id not in cleared_alarms:
                                send_alert(
                                    f"✅ <b>ALARM SELESAI</b>\n"
                                    f"OLT: {olt}\n"
                                    f"Message: {message}\n"
                                    f"End: {end}\n"
                                    f"IP: {ip}\n"
                                    f"Area: {area}"
                                )
                                cleared_alarms.add(alarm_id)
        except Exception as e:
            print("Fetch Error:", e)
    all_alarms = current_alarms

def background_job():
    while True:
        print("⏳ Fetching alarms...")
        fetch_alarms()
        time.sleep(300)

@app.route("/")
def index():
    sorted_alarms = sorted(all_alarms, key=lambda x: x.get("start_dt") or datetime.min, reverse=True)
    return render_template("index.html", alarms=sorted_alarms)

if __name__ == "__main__":
    thread = threading.Thread(target=background_job, daemon=True)
    thread.start()
    app.run(debug=False)
