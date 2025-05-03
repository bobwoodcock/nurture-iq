import re
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class BabyLogEntry:
    ts: datetime
    activity: str
    quantity: Optional[int] = None
    comment: Optional[str] = "KinderCare Email Report"
    duration: Optional[int] = None


def parse_kinder_email_report(email_body: str) -> List[BabyLogEntry]:
    email_body = email_body.replace("=0D", "")
    entries = []

    # Extract report date
    date_match = re.search(r"(\w+), (\w+ \d{1,2}, \d{4})", email_body)
    if not date_match:
        raise ValueError("Could not find report date.")
    report_date = datetime.strptime(date_match.group(2), "%b %d, %Y").date()

    # Helper to parse time strings into datetime
    def parse_time(t: str) -> datetime:
        return datetime.strptime(t.strip(), "%I:%M%p").replace(
            year=report_date.year, month=report_date.month, day=report_date.day
        )

    # Extract sections using start/end markers
    def extract_section(start: str, end: Optional[str] = None) -> str:
        pattern = rf"{re.escape(start)}\n[-]+\n(.*?)(?=\n{re.escape(end)}\n[-]+\n|\Z)" if end else rf"{re.escape(start)}\n[-]+\n(.*)"
        match = re.search(pattern, email_body, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    # ---- Naps ----
    naps_text = extract_section("Naps", "Meals")
    for line in naps_text.splitlines():
        line = line.strip()
        if not line:
            continue
        nap_match = re.match(r"(\d{1,2}:\d{2}[ap]m)\s*-\s*(\d{1,2}:\d{2}[ap]m) \((\dh\d+m)\)", line)
        if nap_match:
            _, end_time, duration = nap_match.groups()
            ts = parse_time(end_time)
            h, m = map(int, re.findall(r"(\d+)h(\d+)m", duration)[0])
            entries.append(BabyLogEntry(ts=ts, activity="Nap", quantity=1, duration=h * 60 + m))

    # ---- Meals ----
    meals_text = extract_section("Meals", "Bathroom")
    for line in meals_text.splitlines():
        line = line.strip()
        if not line or not re.search(r"\d+:\d{2}[ap]m", line):
            continue
        meal_match = re.match(r"(\d{1,2}:\d{2}[ap]m)\s*-\s*([\d.]+) oz - (Breast Milk|Formula)", line)
        if meal_match:
            t, oz, typ = meal_match.groups()
            ts = parse_time(t)
            quantity = int(float(oz) * 30)
            activity = "Pumped" if typ == "Breast Milk" else "Formula"
            entries.append(BabyLogEntry(ts=ts, activity=activity, quantity=quantity))

    # ---- Bathroom ----
    bathroom_text = extract_section("Bathroom")
    for line in bathroom_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"(\d{1,2}:\d{2}[ap]m)\s*-\s*(.*)", line)
        if match:
            t, desc = match.groups()
            ts = parse_time(t)
            desc = desc.lower()
            if "diaper - wet" in desc:
                entries.append(BabyLogEntry(ts=ts, activity="Pee", quantity=1))
            if "bowel movement" in desc:
                entries.append(BabyLogEntry(ts=ts, activity="Poo", quantity=1))

    return entries