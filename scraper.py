import requests
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- NASTAVENÍ ---
# Základní URL pro Kino Flora (ID 1046) bez data na konci
API_URL = "https://www.cinemacity.cz/cz/data-api-service/v1/quickbook/10101/film-events/in-cinema/1052/at-date/"
STATE_FILE = "previous_times.json"

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

def send_email(new_times):
    msg_body = "Byly nalezeny nove casy promitani pro Dunu v 70mm formatu!\n\n"
    for time in sorted(new_times):
        msg_body += f"- {time}\n"
    msg_body += "\nRychle kupuj listky na Flora IMAX!"
    
    msg = MIMEText(msg_body)
    msg['Subject'] = 'Nove listky na Dunu 70mm!'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

def get_current_times():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    found_times = set()
    
    # Nastavení počátečního data (od 10. prosince 2026)
    start_date = datetime(2026, 12, 10)
    
    # Skript zkontroluje start_date a dalších 60 dní
    for i in range(60):
        check_date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"{API_URL}{check_date}?attr=&lang=cs_CZ"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "body" in data and "films" in data["body"]:
                dune_film_ids = []
                
                # 1. Najdeme ID filmu (stačí jakákoliv verze Duny)
                for film in data["body"]["films"]:
                    name = film["name"].lower()
                    if "dune" in name or "duna" in name:
                        dune_film_ids.append(film["id"])
                
                # 2. Vyfiltrujeme časy promítání podle atributů (chceme 70-mm)
                if dune_film_ids:
                    for event in data["body"]["events"]:
                        if event["filmId"] in dune_film_ids:
                            # Kontrola atributů promítání
                            attrs = event.get("attributeIds", [])
                            if not attrs:
                                attrs = event.get("screeningAttributes", [])
                            
                            if "70-mm" in attrs:
                                found_times.add(event["eventDateTime"])
                            
        except Exception:
            # Pokud nějaký den hodí chybu, jedeme dál
            pass
            
    return found_times

def main():
    print("Stahuji data z API...")
    current_times = get_current_times()
    
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            previous_times = set(json.load(f))
    else:
        previous_times = set()

    new_times = current_times - previous_times

    if new_times:
        print(f"Nasel jsem nove casy: {new_times}")
        send_email(list(new_times))
        
        with open(STATE_FILE, "w") as f:
            json.dump(list(current_times), f)
        print("Novy stav byl ulozen.")
    else:
        print("Zadne nove casy v 70mm formatu. Koncim.")

if __name__ == "__main__":
    main()
