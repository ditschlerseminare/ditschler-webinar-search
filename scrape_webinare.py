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

def get_page_lines():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        page.goto(URL, wait_until="networkidle", timeout=60000)
        text = page.locator("body").inner_text()
        browser.close()

    lines = [normalize(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return lines

def parse_webinars(lines):
    webinars = []
    seen = set()
    i = 0

    while i < len(lines):
        # Einstieg: Titelzeile gefolgt von "Mehr Informationen"
        if i + 1 < len(lines) and lines[i + 1] == "Mehr Informationen":
            first_title = lines[i]

            # Suche den eigentlichen Blockstart
            j = i + 2
            while j < len(lines) and lines[j] != "Webinar":
                j += 1

            if j >= len(lines) - 1:
                i += 1
                continue

            # Direkt nach "Webinar" steht nochmal der Titel
            second_title = lines[j + 1]
            title = second_title or first_title

            # "Termine zur Auswahl:" suchen
            k = j + 2
            while k < len(lines) and lines[k] != "Termine zur Auswahl:":
                k += 1

            if k >= len(lines):
                i += 1
                continue

            # Datums-/Nummern-Zeilen sammeln bis "Beschreibung:"
            date_lines = []
            k += 1
            while k < len(lines) and lines[k] != "Beschreibung:":
                date_lines.append(lines[k])
                k += 1

            if k >= len(lines):
                i += 1
                continue

            # Beschreibung sammeln bis "Dozent:"
            desc_lines = []
            k += 1
            while k < len(lines) and lines[k] != "Dozent:":
                desc_lines.append(lines[k])
                k += 1

            # Preis in den Folgezeilen suchen
            price = ""
            m = k
            while m < min(k + 20, len(lines)):
                price_match = re.search(r"Die Seminargebühr beträgt jeweils\s*([0-9]+,[0-9]{2})\s*€", lines[m])
                if price_match:
                    price = f"{price_match.group(1)} €"
                    break
                m += 1

            # Webinar-Nummern aus den Datumszeilen extrahieren
            numbers = []
            cleaned_dates = []
            for line in date_lines:
                num_match = re.search(r"Webinar-Nr\.\s*([0-9/ ]+)", line)
                if num_match:
                    numbers.append(normalize(num_match.group(1)))
                cleaned = re.sub(r"Webinar-Nr\.\s*[0-9/ ]+", "", line)
                cleaned = re.sub(r"Jetzt anmelden.*$", "", cleaned)
                cleaned = normalize(cleaned)
                if re.search(r"\d{2}\.\d{2}\.\d{4}", cleaned):
                    cleaned_dates.append(cleaned)

            if not numbers:
                i += 1
                continue

            number = " / ".join(numbers)
            if number in seen:
                i += 1
                continue
            seen.add(number)

            description = normalize(" ".join(desc_lines))
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
                "dateText": " | ".join(cleaned_dates),
                "tags": tags,
                "url": URL,
                "searchText": normalize(" ".join([title, topic, description, " ".join(tags), number, " | ".join(cleaned_dates)])).lower(),
            })

            i = k
            continue

        i += 1

    webinars.sort(key=lambda x: (x["topic"], x["title"].lower()))
    return webinars

def main():
    lines = get_page_lines()
    webinars = parse_webinars(lines)
    print(f"Gefunden: {len(webinars)} Webinare")

    with open("webinare.json", "w", encoding="utf-8") as f:
        json.dump(webinars, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
