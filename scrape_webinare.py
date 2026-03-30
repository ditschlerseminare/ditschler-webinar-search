import json
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.ditschler-seminare.de/seminare-webinare/seminarprogramm/"

def scrape():
    html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}).text
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text("\n", strip=True)
    lines = text.split("\n")

    webinars = []

    for i, line in enumerate(lines):
        if "Webinar-Nr." in line:
            number = line.split("Webinar-Nr.")[-1].strip()

            # Titel ist meist einige Zeilen darüber
            title = ""
            for j in range(i-1, max(i-10, 0), -1):
                if len(lines[j]) > 20:
                    title = lines[j]
                    break

            webinars.append({
                "id": f"webinar-{number}",
                "type": "Webinar",
                "title": title,
                "number": number,
                "topic": "",
                "description": "",
                "price": "",
                "dateText": "",
                "tags": [],
                "url": URL,
                "searchText": title.lower()
            })

    return webinars


def main():
    data = scrape()
    print(f"Gefunden: {len(data)} Webinare")

    with open("webinare.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
