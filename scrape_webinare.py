import json
import re
from playwright.sync_api import sync_playwright

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

def get_page_text() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        page.goto(URL, wait_until="networkidle", timeout=60000)
        text = page.locator("body").inner_text()
        browser.close()
        return text

def scrape():
    text = get_page_text()

    pattern = re.compile(
        r"(?P<title>[^\n]+)\nMehr Informationen.*?"
        r"\nWebinar\n(?P<title2>[^\n]+)\n"
        r"Termine zur Auswahl:\n(?P<dates>.*?)"
        r"\nBeschreibung:\n(?P<desc>.*?)"
        r"(?=\nDozent:)",
        re.S,
    )

    webinars = []
    seen = set()

    for match in pattern.finditer(text):
        title = normalize(match.group("title2") or match.group("title"))
        desc = normalize(match.group("desc"))
        dates_raw = match.group("dates")

        number_matches = re.findall(r"Webinar-Nr\.\s*([0-9/ ]+)", dates_raw)
        if not number_matches:
            continue

        number = " / ".join(normalize(n) for n in number_matches)
        if number in seen:
            continue
        seen.add(number)

        date_lines = []
        for line in dates_raw.splitlines():
            line = normalize(line)
            if not line:
                continue
            line = re.sub(r"\s*Webinar-Nr\.\s*[0-9/ ]+", "", line)
            line = re.sub(r"\s*Jetzt anmelden.*$", "", line)
            line = normalize(line)
            if re.search(r"\d{2}\.\d{2}\.\d{4}", line):
                date_lines.append(line)

        block_text = match.group(0)
        price_match = re.search(r"Die Seminargebühr beträgt jeweils\s*([0-9]+,[0-9]{2})\s*€", block_text)
        price = f"{price_match.group(1)} €" if price_match else ""

        topic = infer_topic(f"{title} {desc}")
        tags = sorted(set(
            re.findall(r"[a-zA-ZäöüÄÖÜß0-9\-]{3,}", f"{title} {desc} {topic}".lower())
        ))

        webinars.append({
            "id": f"webinar-{re.sub(r'[^0-9]+', '-', number).strip('-')}",
            "type": "Webinar",
            "title": title,
            "number": number,
            "topic": topic,
            "description": desc,
            "price": price,
            "dateText": " | ".join(date_lines),
            "tags": tags,
            "url": URL,
            "searchText": normalize(" ".join([title, topic, desc, " ".join(tags), number, " | ".join(date_lines)])).lower(),
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
