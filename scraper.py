import requests
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- NASTAVENÍ ---
API_BASE_URL = "https://www.cinemacity.cz/cz/data-api-service/v1/quickbook/10101"
CINEMA_ID = "1052"
STATE_FILE = "previous_times.json"

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

def send_email(new_events):
    msg_body = "Byly nalezeny nove casy promitani v 70mm formatu!\n\n"
    
    for film_name, times in new_events.items():
        msg_body += f"Film: {film_name}\n"
        for time in sorted(times):
            msg_body += f"   - {time}\n"
        msg_body += "\n"
        
    msg_body += "Rychle kupuj listky na Flora IMAX!"
    
    msg = MIMEText(msg_body, 'plain', 'utf-8')
    msg['Subject'] = 'Nove listky na Dunu 70mm!'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

def get_available_dates():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    future_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
    url = f"{API_BASE_URL}/dates/in-cinema/{CINEMA_ID}/until/{future_date}?attr=&lang=cs_CZ"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("body", {}).get("dates", [])
    except Exception as e:
        print(f"Chyba při stahování dostupných dat: {e}")
        return []

def get_current_events():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    found_events = set()
    limit_date = datetime(2026, 12, 10)
    
    available_dates = get_available_dates()
    if not available_dates:
        print("Nenalezeny žádné dostupné dny z API.")
        return found_events

    for date_str in available_dates:
        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        if event_date >= limit_date:
            url = f"{API_BASE_URL}/film-events/in-cinema/{CINEMA_ID}/at-date/{date_str}?attr=&lang=cs_CZ"
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if "body" in data and "films" in data["body"] and "events" in data["body"]:
                    film_map = {}
                    for film in data["body"]["films"]:
                        name = film["name"]
                        if "dune" in name.lower() or "duna" in name.lower():
                            film_map[film["id"]] = name
                    
                    if film_map:
                        for event in data["body"]["events"]:
                            film_id = event.get("filmId")
                            if film_id in film_map:
                                attrs = event.get("attributeIds", [])
                                if not attrs:
                                    attrs = event.get("screeningAttributes", [])
                                
                                if "70-mm" in attrs:
                                    film_name = film_map[film_id]
                                    event_time = event["eventDateTime"]
                                    found_events.add(f"{film_name}###{event_time}")
                                    
            except Exception:
                pass
            
    return found_events

def main():
    print("Stahuji data z API...")
    current_events = get_current_events()
    
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            previous_events = set(json.load(f))
    else:
        previous_events = set()

    new_events_set = current_events - previous_events

    if new_events_set:
        print(f"Nasel jsem nove casy: {new_events_set}")
        
        structured_new_events = {}
        for item in new_events_set:
            film_name, event_time = item.split("###", 1)
            if film_name not in structured_new_events:
                structured_new_events[film_name] = []
            structured_new_events[film_name].append(event_time)
            
        send_email(structured_new_events)
        
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(current_events), f, ensure_ascii=False)
        print("Novy stav byl ulozen.")
    else:
        print("Zadne nove casy v 70mm formatu. Koncim.")

if __name__ == "__main__":
    main()