"""Curated day-specific county schedule context used by the dashboard.

This is intentionally hand-structured rather than dynamically parsed from the
PDFs at runtime. That keeps the dashboard simple and fast, while making the
source-of-truth easy to audit when Arlington updates a court schedule.
"""

SCHEDULE_CONTEXT = {
    "Fort Scott Park": {
        "pdf_url": "https://www.arlingtonva.us/files/sharedassets/public/v/1/parks-recreation/documents/courts/fort-scott-dual-court-use.pdf",
        "summary": "Courts 1-2 alternate between drop-in pickleball, reservation blocks, and some drop-in tennis. Court 3 is generally tennis-only.",
        "days": {
            "Sunday": ["Courts 1-2: drop-in pickleball 7am-12pm", "Courts 1-2: reservations 12pm-5pm", "Courts 1-2: drop-in tennis 5pm-10pm"],
            "Monday": ["Courts 1-2: drop-in pickleball 7am-12pm", "Courts 1-2: reservations 12pm-5pm", "Courts 1-2: drop-in pickleball 5pm-10pm"],
            "Tuesday": ["Courts 1-2: no pickleball block shown", "Courts 1-2: reservations / tennis split per county PDF"],
            "Wednesday": ["Courts 1-2: reservations 12pm-5pm", "Courts 1-2: drop-in pickleball 5pm-10pm"],
            "Thursday": ["Courts 1-2: reservation-only all day in county PDF"],
            "Friday": ["Courts 1-2: drop-in pickleball 7am-12pm", "Courts 1-2: reservations 12pm-5pm", "Courts 1-2: drop-in tennis 5pm-10pm"],
            "Saturday": ["Courts 1-2: drop-in pickleball 7am-12pm", "Courts 1-2: reservations 12pm-5pm", "Courts 1-2: drop-in pickleball 5pm-10pm"],
        },
    },
    "Hayes Park": {
        "pdf_url": "https://www.arlingtonva.us/files/sharedassets/public/v/1/parks-recreation/documents/courts/hayes-park-dual-court-use.pdf",
        "summary": "The two courts are split between reservation blocks, drop-in pickleball, and some drop-in tennis depending on the day.",
        "days": {
            "Sunday": ["Both courts: reservations 7am-5pm", "Both courts: drop-in pickleball 5pm-10pm"],
            "Monday": ["Both courts: drop-in pickleball 7am-12pm", "Both courts: reservations 12pm-10pm"],
            "Tuesday": ["Both courts: drop-in tennis 7am-12pm", "Both courts: reservations 12pm-5pm", "Both courts: drop-in pickleball 5pm-10pm"],
            "Wednesday": ["Both courts: reservations all day"],
            "Thursday": ["Both courts: drop-in tennis 7am-12pm", "Both courts: reservations 12pm-10pm"],
            "Friday": ["Both courts: drop-in pickleball 7am-12pm", "Both courts: reservations 12pm-5pm", "Both courts: drop-in pickleball 5pm-10pm"],
            "Saturday": ["Both courts: reservations all day"],
        },
    },
    "Marcey Road Park": {
        "pdf_url": "https://www.arlingtonva.us/files/sharedassets/public/v/1/parks-recreation/documents/courts/marcey-road-dual-court-use-1.pdf",
        "summary": "County schedule context mainly affects Courts 2-3. They switch between drop-in pickleball, reservations, and some drop-in tennis.",
        "days": {
            "Sunday": ["See county PDF for full split; this park uses mixed pickleball / reservation scheduling"],
            "Monday": ["See county PDF for full split; this park uses mixed pickleball / reservation scheduling"],
            "Tuesday": ["See county PDF for full split; this park uses mixed pickleball / reservation scheduling"],
            "Wednesday": ["Courts 2-3: drop-in pickleball 7am-12pm", "Courts 2-3: reservations 12pm-10pm"],
            "Thursday": ["See county PDF for full split; this park uses mixed pickleball / reservation scheduling"],
            "Friday": ["Court 2: drop-in pickleball 7am-12pm, then reservations 12pm-10pm", "Court 3: drop-in pickleball 7am-12pm, reservations 12pm-5pm, then drop-in tennis 5pm-10pm"],
            "Saturday": ["Courts 2-3: drop-in tennis 7am-12pm", "Courts 2-3: reservations 12pm-5pm", "Courts 2-3: drop-in pickleball 5pm-10pm"],
        },
    },
    "Old Glebe Road Courts": {
        "pdf_url": "https://www.arlingtonva.us/files/sharedassets/public/v/1/parks-recreation/documents/courts/old-glebe-road-park-dual-court-use.pdf",
        "summary": "Courts 1-2 share time between pickleball drop-in windows and reservation blocks. Court 3 is mostly tennis.",
        "days": {
            "Sunday": ["Courts 1-2: reservations 7am-5pm", "Courts 1-2: drop-in pickleball 5pm-10pm"],
            "Monday": ["Court 1: drop-in pickleball 7am-12pm and 5pm-10pm", "Court 2: mostly reserved", "Court 3: drop-in tennis all day"],
            "Tuesday": ["Courts 1-2: drop-in pickleball 7am-12pm", "Courts 1-2: reservations 12pm-10pm"],
            "Wednesday": ["Courts 1-2: reservations all day", "Court 3: drop-in tennis all day"],
            "Thursday": ["Court 1: drop-in pickleball 7am-12pm and 5pm-10pm", "Court 2: drop-in pickleball 7am-12pm then reservations 12pm-10pm"],
            "Friday": ["Court 1: drop-in pickleball 7am-12pm and 5pm-10pm", "Court 2: drop-in pickleball 7am-12pm then reservations 12pm-10pm"],
            "Saturday": ["Courts 1-2: drop-in pickleball 7am-12pm", "Courts 1-2: reservations 12pm-10pm"],
        },
    },
    "Lubber Run": {
        "pdf_url": "https://www.arlingtonva.us/files/sharedassets/public/v/3/parks-recreation/documents/temp/sports/pickleball-tennis/lubber-run-court-schedule-infographic_vertical.pdf",
        "summary": "Court 1 is essentially pickleball all day. Court 2 is shared with basketball and needs special handling.",
        "days": {
            "Sunday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-6pm", "Court 2: pick-up basketball 6pm-10pm"],
            "Monday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-3pm", "Court 2: pick-up basketball 3pm-8pm", "Court 2: drop-in pickleball 8pm-10pm"],
            "Tuesday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-3pm", "Court 2: pick-up basketball 3pm-6pm", "Court 2: drop-in pickleball 6pm-10pm"],
            "Wednesday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-3pm", "Court 2: pick-up basketball 3pm-6pm", "Court 2: drop-in pickleball 6pm-10pm"],
            "Thursday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-3pm", "Court 2: pick-up basketball 3pm-6pm", "Court 2: drop-in pickleball 6pm-10pm"],
            "Friday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-3pm", "Court 2: pick-up basketball 3pm-6pm", "Court 2: drop-in pickleball 6pm-10pm"],
            "Saturday": ["Court 1: drop-in pickleball 7am/sunrise-10pm", "Court 2: pickleball or basketball 7am-6pm", "Court 2: pick-up basketball 6pm-10pm"],
        },
    },
}
