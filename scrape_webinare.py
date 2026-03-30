import json
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.ditschler-seminare.de/seminare-webinare/seminarprogramm/"

TOPIC_RULES = [
    ("Excel / Office", ["excel", "pivot", "makro", "steuerelement"]),
    ("WfbM / Werkstatt", ["wfbm", "werkstatt", "werkstattlohn", "wvo", "arbeitsergebnis", "bbb", "ev"]),
    ("BTHG / Eingliederungshilfe", ["eingliederungshilfe", "bthg", "sgb ix", "gesamtplan", "icf", "teilhabe", "budget für arbeit", "budget für ausbildung"]),
    ("Betreuungsrecht", ["betreuungsrecht", "betreuungsbehörde", "betreu"]),
    ("Pflege / SGB XI", ["pflege", "wbvg", "pfleg"]),
    ("TVöD / TV-L", ["tvöd", "tv-l", "tarif"]),
    ("Arbeitsrecht", ["kündigung", "arbeitsrecht", "arbeitsvertrag"]),
    ("Sozialrecht", ["sozialgesetz", "sozialrecht", "bürgergeld", "grundsicherung", "sgb ii", "sgb xii"]),
]

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def infer_topic(text: str) -> str:
    t = text.lower()
    for topic, needles in TOPIC_RULES:
        if any(n in t for n in needles):
            return topic
    return "Sonstiges"

def scrape():
    html = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    ).text

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    # Webinar-Block:
    # TITLE
    # Mehr Informationen
    # ...
    # Webinar
    # TITLE
    # Termine zur Auswahl:
    # 21.04.2026, 9 - 12 Uhr, Webinar-Nr. 506 Jetzt anmelden
    # Beschreibung:
    # ...
    # Dozent:
    pattern = re.compile(
        r"(?P<title>[^\n]+)\nMehr Informationen.*?"
        r"\nWebinar\n.*?"
        r"\nTermine zur Auswahl:\n(?P<dates>.*?)"
        r"\nBeschreibung:\n(?P<desc>.*?)"
        r"(?=\nDozent:)",
        re.S
    )

    webinars = []
    seen = set()

    for match in pattern.finditer(text):
        title = normalize(match.group("title"))
        dates_block = normalize(match.group("dates"))
        description = normalize(match.group("desc"))

        # Alle Webinar-Nummern im Datumsblock einsammeln
        numbers = re.findall(r"Webinar-Nr\.\s*([0-9/ ]+)", dates_block)
        if not numbers:
            continue

        number = " / ".join(normalize(n) for n in numbers)

        if number in seen:
            continue
        seen.add(number)

        # Datumszeilen säubern
        date_lines = []
        for line in match.group("dates").splitlines():
            line = normalize(line)
            if not line:
                continue
            line = re.sub(r"\s*Webinar-Nr\.\s*[0-9/ ]+", "", line)
            line = re.sub(r"\s*Jetzt anmelden.*$", "", line)
            line = normalize(line)
            if re.search(r"\d{2}\.\d{2}\.\d{4}", line):
                date_lines.append(line)

        # Preis im ganzen Block suchen
        block_text = match.group(0)
        price_match = re.search(r"Die Seminargebühr beträgt jeweils\s*([0-9]+,[0-9]{2})\s*€", block_text)
        price = f"{price_match.group(1)} €" if price_match else ""

        topic = infer_topic(f"{title} {description}")

        tags = sorted(set(
            re.findall(r"[a-zA-ZäöüÄÖÜß0-9\-]{3,}", f"{title} {description} {topic}".lower())
        ))

        webinars.append({
            "id": f"webinar-{re.sub(r'[^0-9]+', '-', number).strip('-')}",
            "type": "Webinar",
            "title": title,
            "number": number,
            "topic": topic,
            "description": description,
            "price": price,
            "dateText": " | ".join(date_lines),
            "tags": tags,
            "url": URL,
            "searchText": normalize(" ".join([title, topic, description, " ".join(tags), number, " | ".join(date_lines)])).lower()
        })

    webinars.sort(key=lambda x: (x["topic"], x["title"].lower()))
    return webinars

def main():
    webinars = scrape()
    print(f"Gefunden: {len(webinars)} Webinare")

    with open("webinare.json", "w", encoding="utf-8") as f:
        json.dump(webinars, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
