import json
import re
from dataclasses import dataclass, asdict
from typing import List
import requests
from bs4 import BeautifulSoup

URL = "https://www.ditschler-seminare.de/seminare-webinare/seminarprogramm/"
OUT = "webinare.json"

@dataclass
class Webinar:
    id: str
    type: str
    title: str
    number: str
    topic: str
    description: str
    price: str
    dateText: str
    tags: List[str]
    url: str
    searchText: str

TOPIC_RULES = [
    ("Excel / Office", ["excel"]),
    ("WfbM / Werkstatt", ["wfbm", "werkstatt"]),
    ("BTHG / Eingliederungshilfe", ["eingliederungshilfe", "bthg"]),
    ("Betreuungsrecht", ["betreu"]),
    ("Pflege / SGB XI", ["pflege"]),
    ("TVöD / TV-L", ["tvöd", "tv-l"]),
    ("Arbeitsrecht", ["arbeitsrecht"]),
    ("Sozialrecht", ["sozialrecht"]),
]

def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip()

def infer_topic(text):
    t = text.lower()
    for topic, keys in TOPIC_RULES:
        if any(k in t for k in keys):
            return topic
    return "Sonstiges"

def scrape():
    html = requests.get(URL).text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    pattern = re.compile(
        r"(?P<title>[^\n]+)\nMehr Informationen.*?Termine zur Auswahl:\n"
        r"(?P<dates>.*?)\nBeschreibung:\n"
        r"(?P<desc>.*?)(?:\nDozent:|\nDurchführung mit ZOOM\.|\nDie Seminargebühr beträgt)",
        re.S,
    )

    webinars = []
    for m in pattern.finditer(text):
        title = normalize(m.group("title"))
        desc = normalize(m.group("desc"))
        dates = normalize(m.group("dates"))

        numbers = re.findall(r"Webinar-Nr\.\s*([0-9/ ]+)", dates)
        if not numbers:
            continue

        number = numbers[0].strip()

        webinars.append({
            "id": f"webinar-{number}",
            "type": "Webinar",
            "title": title,
            "number": number,
            "topic": infer_topic(title + " " + desc),
            "description": desc,
            "price": "",
            "dateText": dates,
            "tags": [],
            "url": URL,
            "searchText": (title + " " + desc).lower()
        })

    return webinars

def main():
    data = scrape()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
