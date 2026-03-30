#!/usr/bin/env python3
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Dict
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
    ("Excel / Office", ["excel", "pivot", "makro", "steuerelement"]),
    ("WfbM / Werkstatt", ["wfbm", "werkstatt", "werkstattlohn", "wvo", "arbeitsergebnis", "ev", "bbb"]),
    ("BTHG / Eingliederungshilfe", ["eingliederungshilfe", "bthg", "sgb ix", "gesamtplan", "icf", "teilhabe", "budget für arbeit", "budget für ausbildung"]),
    ("Betreuungsrecht", ["betreuungsrecht", "betreuungsbehörde", "betreu"]),
    ("Pflege / SGB XI", ["pflege", "wbvg", "pfleg"]),
    ("TVöD / TV-L", ["tvöd", "tv-l", "tarif"]),
    ("Arbeitsrecht", ["kündigung", "arbeitsrecht", "arbeitsvertrag"]),
    ("Sozialrecht", ["sozialgesetz", "sozialrecht", "bürgergeld", "grundsicherung", "sgb ii", "sgb xii"]),
]

STOPWORDS = {"und","oder","die","der","das","mit","für","in","zu","des","den","von","dem","als","eine","ein","auf","im"}

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def infer_topic(text: str) -> str:
    t = (text or "").lower()
    for topic, needles in TOPIC_RULES:
        if any(n in t for n in needles):
            return topic
    return "Sonstiges"

def extract_tags(title: str, description: str, topic: str, number: str) -> List[str]:
    text = f"{title} {description} {topic} {number}".lower()
    tags = set()
    for token in re.findall(r"[a-zA-ZäöüÄÖÜß0-9\-]{3,}", text):
        if token not in STOPWORDS:
            tags.add(token)
    # Seed helpful synonyms
    if "wfbm" in text or "werkstatt" in text:
        tags.update(["wfbm", "werkstatt"])
    if "eingliederungshilfe" in text or "bthg" in text:
        tags.update(["eingliederungshilfe", "bthg", "sgb ix"])
    if "tvöd" in text or "tv-l" in text:
        tags.update(["tvöd", "tv-l", "tarifrecht"])
    if "pflege" in text or "wbvg" in text:
        tags.update(["pflege", "sgb xi"])
    return sorted(tags)

def scrape() -> List[Webinar]:
    html = requests.get(URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    # The page repeats the webinar blocks in text order; each full detail block contains:
    # title -> "Termine zur Auswahl:" -> date line(s) -> "Beschreibung:" -> long text -> price -> number.
    text = soup.get_text("\n", strip=True)
    chunks = re.split(r"\n(?=[A-ZÄÖÜ0-9].+\nMehr Informationen)", text)

    webinars: List[Webinar] = []
    seen = set()

    title_re = re.compile(r"^(?P<title>.+?)\nMehr Informationen", re.S)
    number_re = re.compile(r"Webinar-Nr\.\s*([0-9/ ]+)")
    price_re = re.compile(r"([0-9]+,[0-9]{2}\s*€\*?)")
    date_re = re.compile(r"(\d{2}\.\d{2}\.\d{4},?\s*[0-9]{1,2}\s*-\s*[0-9]{1,2}\s*Uhr(?:,\s*Webinar-Nr\..*)?)")
    desc_re = re.compile(r"Beschreibung:\s*(.+?)(?:Dozent:|Durchführung mit ZOOM\.|Die Seminargebühr beträgt)", re.S)

    for chunk in chunks:
        if "Webinar" not in chunk or "Webinar-Nr." not in chunk:
            continue
        tm = title_re.search(chunk)
        nm = number_re.search(chunk)
        if not tm or not nm:
            continue

        title = normalize_spaces(tm.group("title"))
        number = normalize_spaces(nm.group(1)).replace(" ", "")
        if number in seen:
            continue
        seen.add(number)

        dates = [normalize_spaces(d.replace(", Webinar-Nr. " + number, "")) for d in date_re.findall(chunk)]
        price_match = price_re.search(chunk)
        desc_match = desc_re.search(chunk)

        description = normalize_spaces(desc_match.group(1)) if desc_match else ""
        topic = infer_topic(f"{title} {description}")
        price = price_match.group(1).replace("*", "") if price_match else ""
        date_text = " | ".join(dates)
        tags = extract_tags(title, description, topic, number)

        webinar = Webinar(
            id=f"webinar-{number.replace('/', '-').replace(' ', '')}",
            type="Webinar",
            title=title,
            number=number,
            topic=topic,
            description=description,
            price=price,
            dateText=date_text,
            tags=tags,
            url=URL,
            searchText=normalize_spaces(" ".join([title, topic, description, " ".join(tags), number, date_text])).lower(),
        )
        webinars.append(webinar)

    webinars.sort(key=lambda x: (x.topic, x.title.lower()))
    return webinars

def main():
    webinars = [asdict(w) for w in scrape()]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(webinars, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(webinars)} webinars to {OUT}")

if __name__ == "__main__":
    main()
