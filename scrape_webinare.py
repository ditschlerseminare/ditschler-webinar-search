import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.ditschler-seminare.de/seminare-webinare/seminarprogramm/"

def scrape():
    html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}).text
    soup = BeautifulSoup(html, "html.parser")

    webinars = []

    # Alle Textblöcke durchgehen
    text_blocks = soup.get_text("\n").split("\n")

    current_title = None

    for line in text_blocks:
        line = line.strip()

        if not line:
            continue

        # Titel erkennen (groß + keine Standardtexte)
        if len(line) > 20 and "Webinar" not in line and "Mehr Informationen" not in line:
            current_title = line

        # Webinar Nummer erkennen
        if "Webinar-Nr." in line and current_title:
            number = line.split("Webinar-Nr.")[-1].strip()

            webinars.append({
                "id": f"webinar-{number}",
                "type": "Webinar",
                "title": current_title,
                "number": number,
                "topic": "",
                "description": "",
                "price": "",
                "dateText": "",
                "tags": [],
                "url": URL,
                "searchText": current_title.lower()
            })

    return webinars


def main():
    data = scrape()
    print(f"Gefunden: {len(data)} Webinare")

    with open("webinare.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
