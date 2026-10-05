#!/usr/bin/env python3
"""Apply hand-corrections to the raw extractions (out/<year>.tsv) and write the final TSVs to
/home/claude/familykb/sources/glossaries/<year>.tsv.  Every correction below was checked
against the page text printed from the corpus; the comments say which page."""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/claude/familykb/sources/glossaries"
os.makedirs(OUT, exist_ok=True)

GENERIC = [
    (r"[⟨⟩]", ""),
    ("­", ""),                       # soft hyphen
    (r"girl- ask-guy", "girl-ask-guy"),
    (r"\bO- Week\b", "O-Week"),
    (r"live-inhousemate", "live-in housemate"),
    (r"wonder ful", "wonderful"),
    (r"Dar ned", "Darned"),
    (r"allnighter", "all-nighter"),
    (r"StudentCenter", "Student Center"),
    (r"([a-z])- ([a-z])", r"\1\2"),       # line-end hyphenation left over after column joins
    (r"back-?to-?back", "back-to-back"),
    (r"\s+", " "),
]


def fix(d: str) -> str:
    for pat, rep in GENERIC:
        d = re.sub(pat, rep, d)
    return d.strip()


def fix_term(t: str) -> str:
    t = re.sub(r"[⟨⟩]", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    if t.endswith(".") and not re.search(r"\b[A-Z]\.$", t):
        t = t[:-1]
    return t


def load(year):
    with open(f"{HERE}/out/{year}.tsv", encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter="\t")]


def save(year, rows):
    path = f"{OUT}/{year}.tsv"
    # the Rice-speak section repeats "College night" with a different sense: keep both rows,
    # marking the second so the series tool does not collapse them
    seen = set()
    for r in rows:
        k = fix_term(r["term"]).lower()
        if k in seen and k == "college night":
            r["term"] = fix_term(r["term"]) + " [Rice speak]"
        seen.add(k)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("term\tdefinition\tsource_key\tlocator\n")
        for r in rows:
            fh.write(f"{fix_term(r['term'])}\t{fix(r['definition'])}\t{r['source_key']}\t{r['locator']}\n")
    print(f"{year}: {len(rows)} rows -> {path}")


def apply(rows, key, *, set_def=None, add=None, drop=None, rename=None, drop_pages=None):
    """set_def: {term: def}; add: [(term, def, locator)]; drop: [terms]; rename: {old: new};
    drop_pages: [locator] — remove every row with that locator."""
    set_def = set_def or {}
    drop = set(drop or [])
    rename = rename or {}
    out = []
    seen = set()
    for r in rows:
        t = r["term"].strip()
        if t in drop or (drop_pages and r["locator"] in drop_pages):
            continue
        if t in set_def:
            r["definition"] = set_def[t]
            seen.add(t)
        if t in rename:
            r["term"] = rename[t]
        out.append(r)
    missing = set(set_def) - seen
    if missing:
        print(f"  WARNING {key}: set_def terms not found: {sorted(missing)}", file=sys.stderr)
    for term, d, loc in add or []:
        out.append({"term": term, "definition": d, "source_key": key, "locator": loc})
    return out


def insert_after(rows, after_term, new_row):
    for i, r in enumerate(rows):
        if r["term"].strip() == after_term:
            rows.insert(i + 1, new_row)
            return
    rows.append(new_row)


# ---------------------------------------------------------------- 1994 (hand transcribed; see make1994 below)

# ---------------------------------------------------------------- 2003  (conclusions PDF pp.3-7)
r = load("2003")
r = apply(r, "oweek-2003", set_def={
    "Battlesows": "1. Affectionate name for the back-to-back defending champion Wiess powderpuff football team.",
    "Christie": "1. Wiess RA and wife of Doward. Class of 2001 from South Dakota. A chemical engineer with crazy work hours and the ability to organize anything.",
    "Coffeehouse Night": "1. An evening of entertainment featuring performing Wiessmen and free caffeine.",
    "College night": "1. A day filled with college bonding, hanging out, a nice dinner and an evening of entertainment. Always held the last day of classes.",
    "Corner": "1. To pull up an extra chair at the corner of a table. Frequently occurs during meals, but never at formal occasions.",
    "Doward": "1. Wiess RA and husband of Christie. Class of 2001. Most likely to find him fixing computers on campus or vegging in the Acabowl.",
    "Family Style": "1. The faster, funner, better way that Wiessmen choose to eat. Once a week, we all sit and eat as a family instead of plodding through the kitchen line like the drones at other college. The night features entertainment, freshmen waiters, bonding and, if you’re lucky, a ubangee.",
    "Filmest": "1. A 24-hour film marathon held during Dead Week. 2. The best way to waste time when you should be studying.",
    "Five-man": "1. Popular suite at Wiess, which typically ends up being a hangout location for thirsty Wiessmen.",
    "Freshmen One-Acts": "1. First Tabletop production of the year, which includes, you guessed it, one-acts featuring freshfers.",
    "Jamfest": "1. One of the coolest parties at Rice. Held during Owl Weekend, Wiess books live bands and people hang out in the Acabowl all day.",
    "Katharine": "1. Master of Wiess. Sociology professor by day, Latin dancer by night. An all-around cool person.",
    "Moment of Silence": "1. Honor given to a deserving individual at family style to break the ear-shattering noise of plate banging. “Hi, my name is [insert name here]. May I please have a moment of silence?”",
    "Night of Decadence (NOD)": "1. The best party at Rice. Held at Wiess on the last Friday of October, it features a live band, interesting decorations and creative costumes.",
    "PDR": "1. Private dining room. A smaller room attached to the Commons. Used for studying and as a dressing room during Tabletop productions.",
    "Pumpkin caroling": "1. The spreading of Halloween cheer, led by the College Idiot. Features Halloween songs, candles and a visit to the Gillis home.",
    "Summit": "1. Weekend retreat to discuss Wiess issues and bond far away from campus.",
    "TV room": "1. An awesome room on the fourth floor, featuring a big-screen TV and surround sound. Site of film fest and open for use at any time.",
    "Beer-Bike": "1. A competitive inter-college race held in the spring in which ten bikers and ten chuggres from each collge compete in a strugle for personal and college pride. 2. A day full of events, including the race, a parade and a water balloon fight.",
    "CCA": "1. College Computing Associates 2. Friendly people in your college who will help you when your computer acts up",
    "Cloisters": "1. Collection of offices adjactent to the Student Center",
    "Early ’80s": "1. Party that brings back both memories and clothing.",
    "Hanszen": "1. A lesser college distinguished by its lack of anything cool. 2. A lesser college undistinguishable from a pile of bricks.",
    "Jones": "1. A lesser college distinguished by the brightly colored Jones House 2. A lesser college indistinguishable from Brown.",
    "Outer Loop": "1. The path that encircles campus 2. A 3-mile long path that greats for a jog.",
    "Sammy the Owl": "1. The Rice mascot",
}, drop=["campus.", "on campus.", "jog."], add=[
    ("Dr. Bill", "1. Wiess RA. Electrical Engineering Professor Dr. William Wilson. A great friend and mentor to all Wiessmen. Catch him setting up Tabletop sets, recording things on campus and taking pictures wherever he goes.", "p.3"),
    ("Tabletop", "1. Wiess theatre. 2. The best theatre production group on campus.", "p.4"),
    ("Team Wiess", "1. The most powerful cheer on campus. 2. The embodiment of everything that makes Wiess College cool.", "p.4"),
    ("Club 13", "1. An organization whose sole function is to undress, smear shaving cream on their bodies and run around campus leaving a slimy trail of body prints. 2. A favorite target of Wiessmen with buckets of water.", "p.5"),
    ("Esperanza", "1. Fall formal. Traditionally a girl-ask-guy affair.", "p.5"),
    ("Hedges", "1. Extensive botanical growth that surrounds campus and is in the quad. 2. “Beyond the hedges” refers to the world beyond Rice. 3. Fun things to jump over.", "p.5"),
    ("P/F", "1. Pass-fail. A fun way to take a class.", "p.6"),
    ("S/E", "A student majoring in science or engineering", "p.7"),
])
save("2003", r)

# ---------------------------------------------------------------- 2006 / 2007 (clean apart from generic fixes)
save("2006", load("2006"))
save("2007", load("2007"))

# ---------------------------------------------------------------- 2008 (Part 7, pp.3-7)
r = load("2008")
r = apply(r, "oweek-2008", set_def={
    "Quad": "1. The central academic quadrangle around Willy’s Statue.",
    "SCC": "1. College Computing Associates. 2. Friendly people in your college who will help you when your computer acts up.",
    "Sid Rich": "1. A lesser college distinguished by its height. 2. A lesser college indistinguishable from the Medical Center.",
    "Trasher": "1. The April’s Fool newspaper.",
}, add=[
    ("SMR", "1. Student Maintenance Representative. 2. The person to find if you lose your key or something breaks.", "part 7 p.7"),
    ("U. Blue", "1. Undergraduate literary magazine. 2. Also, there is R2, Rice's newest literary publication.", "part 7 p.7"),
])
save("2008", r)

# ---------------------------------------------------------------- 2010 (clean)
save("2010", load("2010"))

# ---------------------------------------------------------------- 2011 (pp.92-96, glyph cipher decoded)
r = load("2011")
r = apply(r, "oweek-2011", set_def={
    "Freshmen Service Points": "1. It’s called “giving back to the wonderful place that is Wiess.” 2. Four hours of required service for freshmen.",
    "Archi (AR-kee)": "A student majoring in architecture.",
    "Baker": "1. A lesser college distinguished by its old Commons. 2. A lesser college indistinguishable from neighboring Will Rice.",
    "Inner Loop": "One-way loop that runs around the center of campus.",
    "Sallyport": "1. The big archway in Lovett Hall. 2. DO NOT walk out of it until you graduate!",
    "RMC": "1. Rice Memorial Center. 2. The Student Center. 3. Where you can find the bookstore, the convienence store, and Smoothie King (yummy!).",
    "SMR": "1. Student Maintenance Representative. 2. The person to find if you lose your key or something breaks.",
    "Will Rice": "1. A lesser college distinguished by its obsession with Beer-Bike. 2. A lesser college indistinguishable from Baker.",
}, drop=[".", "able"], add=[
    ("Ironman/Ironwoman", "Someone who bikes and chugs at Beer Bike.", "p.95"),
    ("Squirrels", "Creatures seen throughout campus. Known to be very crazy.", "p.96"),
])
save("2011", r)

# ---------------------------------------------------------------- 2014 (pp.102-106; Rice Speak pp.104 and 106 hand-transcribed)
r = load("2014")
r = apply(r, "oweek-2014", set_def={
    "Basement": "The area under the Commons used for storage and shirt screen making. Can be accessed using your room key.",
    "Benjamin and Jenna": "Wiess Aca-children, son and daughter of the Byrds, who love jumping on the trampoline and reading.",
    "College Night": "A day filled with college bonding, hanging out, a nice dinner, and an evening of entertainment. Wiess' is always held the last day of classes each semester. Each college has their own college night, which are not always on the last day of classes.",
    "Freshmen Service Points": "Four hours of required service to Wiess. Necessary to enter the housing jack at the end of your first year. There are plenty of opportunities to get them!",
    "Pumpkin caroling": "The spreading of Halloween cheer, led by the College Idiots. Features Halloween songs, candles, and a visit to the other colleges.",
    "Team Wiess": "The most powerful cheer on campus, and the embodiment of everything that makes Wiess College cool.",
    "Wiessmen": "The inclusive, gender neutral term for the women and men of Wiess College. This includes you.",
    "H&D": "Housing and Dining. Administrative office in charge of all food service and residential buildings on campus.",
    "Jack": "A prank pulled on another college.",
    "Leebron (and Ping)": "David Leebron - President of the University. Married to Ping.. Also sends fascinating holiday e-card every year.",
    "Matriculation": "Ceremony held during O-Week to officially welcome you to Rice.",
    "Mudd Lab": "The university computer/IT center. If you have problems with your computer, the people here are glad to help out. Also a great place to print large posters",
    "Meet Sheet": "Officially called First Look, a book with a catalogue of pictures of all incoming students.",
    "MOB": "The Marching Owl Band. That doesn’t march. They always put on an entertaining show during halftime, filled with amusing skits, jibes at opposing teams, and zany antics.",
}, drop=["Affectionate name for the Wiess powder-"], drop_pages=["p.104", "p.106"], add=[
    ("Battlesows", "Affectionate name for the Wiess powderpuff football team.", "p.102"),
    ("Big Bang", "Event held for the new students after they ace their first round of exams.", "p.102"),
    ("Goldenrod", "The official Wiess color. It will soon dominate your wardrobe. Remember it's not yellow!", "p.103"),
    ("Renata", "Third floor RA and Bioengineering lecturer. Loves to talk and make delicious Mexican food. Married to Lenin, proud mama of Gavin. Also a shirt-screening expert!", "p.103"),
    ("Jonesian", "A member of Jones college.", "p.105"),
    ("Lovetteer", "A resident of Lovett College", "p.105"),
    # p.104 — Rice Speak, first page
    ("45, 90, 180", "Three big slabs of rock in the Engineering Quad.", "p.104"),
    ("’80s Party", "Party held at Sid Rich college that brings back both awesome music and clothing.", "p.104"),
    ("Academ", "A person majoring in humanities or social sciences.", "p.104"),
    ("Academic Quad", "The central academic quadrangle around Willy’s Statue.", "p.104"),
    ("Archi (AR-kee)", "A student majoring in architecture.", "p.104"),
    ("ASB", "Alternative Spring Break; service project over spring break, often in another state.", "p.104"),
    ("Associate", "Faculty, staff, or community members associated with a college. Darned good people to know.", "p.104"),
    ("Autry", "Gym in Tudor Fieldhouse where the Rice basketball team plays.", "p.104"),
    ("Backpage", "The humorous last page of the Thresher.", "p.104"),
    ("Bakerite", "A resident of Baker College.", "p.104"),
    ("Baker 13", "An organization whose sole function is to undress, smear shaving cream on their bodies, and run around campus leaving a slimy trail of body prints. A favorite target of Wiessmen with buckets of water.", "p.104"),
    ("Beer Bike", "A competitive intercollege race held in the spring in which ten bikers and ten chuggers from each college compete in a struggle for personal and college pride. Also includes a water balloon fight and much rejoicing.", "p.104"),
    ("Beyond the hedges", "A term to describe the “real word” outside of Rice.", "p.104"),
    ("Big Three", "Classes frequently taken by freshmen science and engineering majors: Physics, Chemistry, and Calculus.", "p.104"),
    ("Brochstein", "A modernistic glass building located behind Fondren. Home to Salento (a non-student operated coffeeshop) and is a great place to relax and sit outside.", "p.104"),
    ("Brownie", "A resident of Brown College.", "p.104"),
    ("Campanile", "1. The bell tower in the Engineering quad. 2. Rice’s yearbook 3. An undergraduate orchestras.", "p.104"),
    ("Cloisters", "Collection of offices adjacent to the Student Center.", "p.104"),
    ("Coffeehouse", "Student-run shop in the Student Center that provides caffeine to needy students. Also a great place to study and/or pretend to be a hipster.", "p.104"),
    ("Cohen House", "The faculty dining club near Sewall Hall. Eat here if you get a chance.", "p.104"),
    ("D1, D2, D3", "Refers to distribution credits, Rice's way of making sure you get a balanced education. 12 credit hours of each category are required to graduate. D1 = humanities, D2 = social sciences, D3 = science and engineering.", "p.104"),
    ("DMC", "The Digital Media Center. Lots of computers to use and cool equipment to check out.", "p.104"),
    ("Duncaroo", "A resident of Duncan College.", "p.104"),
    ("Esperanza", "Fall formal. A major part of homecoming weekend and lots of fun!", "p.104"),
    # p.106 — Rice Speak, last page
    ("Pumpkin Grades", "Mid-semester grades given to new students in the fall.", "p.106"),
    ("R2 (The Rice Review)", "An independent literary magazine published entirely by students", "p.106"),
    ("Recharge U", "Campus convenience store in the RMC.", "p.106"),
    ("REMS", "Rice students that are trained as EMTs. Respond to emergencies on campus.", "p.106"),
    ("Rice Players", "Only campus theater group not associated with a college.", "p.106"),
    ("RMC", "Rice Memorial Center, also referred to as the Student Center. This is where you can find the bookstore, the convenience store, Coffeehouse, Pub, and important offices like Academic Advising.", "p.106"),
    ("RPC", "Rice Program Council. The organization in charge of all university-wide events, like Beer Bike, Screw Yer Roommate, Ezperanza, and study breaks during finals.", "p.106"),
    ("SA", "Student Association. The campus-wide body representing students. Deals with campus-wide issues and administrative business.", "p.106"),
    ("Sallyport", "The big archway in Lovett Hall. Tradition holds that if you walk through it between matriculation and graduation, you won't graduate.", "p.106"),
    ("Sammy the Owl", "The Rice mascot.", "p.106"),
    ("S/E", "A student majoring in science or engineering.", "p.106"),
    ("Sidizen", "A resident of Sid Richardson College.", "p.106"),
    ("SMR", "Student Maintenance Representative. The liaison between H&D and the students. They can help you change the height of your bed or change your light bulbs.", "p.106"),
    ("SpoCo", "Spontaneous Combustion, the improv skit group on campus. Check out one of their shows, they’re very funny!", "p.106"),
    ("Squirrels", "Creatures seen throughout campus. Known to be very crazy and totally unafraid of humans.", "p.106"),
    ("TC", "Taco Cabana. A twenty-four hour food-serving institution and an all-nighter’s best friend.", "p.106"),
    ("Tetra Points", "Credit on your meal plan used to buy food at the RMC or the Hoot.", "p.106"),
    ("Thresher", "Rice’s student-operated newspaper. Check out the Backpage for some ol’ time ribbing, hehehe.", "p.106"),
    ("Ultimate", "The frisbee-lacrosse-soccer amalgam frequently played on campus.", "p.106"),
    ("Valhalla", "The other on-campus pub, often populated by grad students, but a great place for cheap beer.", "p.106"),
    ("Village", "The shopping center west of campus. Has lots of great restaurants and shops, all within walking distance!", "p.106"),
    ("Whataburger", "A 24-hour restaurant to get a burger or legendary Honey Butter Chicken Biscuit. Ask for Texas Toast — it’s the only way to truly eat a Whataburger.", "p.106"),
    ("Wiess", "Your home and family.", "p.106"),
    ("Will Ricer", "A resident of Will Rice College", "p.106"),
    ("Willy Week", "The week preceding Beer Bike, filled with college activities, alumni, and jacks.", "p.106"),
    ("Willy’s Statue", "A two-ton brass likeness of the founder of the university located in the center of the Academic Quad.", "p.106"),
    ("Y’all", "Southern slang short for \"you all.\" Something you have to get used to. Y'all will be saying this if you want to or not.", "p.106"),
])
# keep page order: sort by locator page number, stable
r.sort(key=lambda x: int(re.search(r"\d+", x["locator"]).group(0)))
save("2014", r)

# ---------------------------------------------------------------- 2015 / 2016 / 2017 (inline "Term Definition" style)
MULTI = [
    "Wiess Master House (Wilson House)", "Wilson House (Wiess Master House)", "Wilson House (Wiess Magister’s House)",
    "Freshman Service Points", "Freshman One-Acts", "R2 (The Rice Review)", "Associates Night", "College Night",
    "Head Fellows", "OC Lounge", "Pumpkin Caroling", "Room Draw", "Wiess Day", "Team Wiess", "Upper Commons",
    "War Pig", "45, 90, 180", "Academic Quad", "Archi (AR-kee)", "Baker 13", "Baker Institute", "Beer Bike",
    "Beyond the hedges", "Big Three", "ChBE (“Chubby”)", "Cohen House", "D1, D2, D3", "Frog Wall", "The Hoot",
    "Inner Loop", "Jones School", "KTRU (KAY-true)", "Media Center", "Mudd Lab", "Musi (Myoo-zee)", "Outer Loop",
    "Private Party", "Public Party", "Pumpkin Grades", "The Rec", "Recharge U", "Sammy the Owl", "Tetra Points",
    "Willy Week", "Willy’s Statue",
]
MULTI.sort(key=len, reverse=True)
NICK = "(table) Baker — Bakerite; Will Rice — Will Ricer; Hanszen — Hanszenite; Jones — Jonesian; Brown — Brownie; Lovett — Lovetteer; Sid Richardson — Sidizen; Martel — Martelian; McMurtry — Murt; Duncan — Duncaroo."
TABLE_ROWS = {"WHAT", "Baker", "Will", "Hanszen", "Jones", "Brown", "Lovett", "Sid", "Martel", "McMurtry", "Duncan"}


def inline_fix(rows, key):
    out = []
    table_loc = None
    for r in rows:
        full = (r["term"].strip() + " " + r["definition"].strip()).strip()
        if r["term"].strip() == "WHAT" and full.startswith("WHAT TO CALL PEOPLE FROM"):
            table_loc = r["locator"]
            continue
        if table_loc and r["term"].strip() in TABLE_ROWS and len(full.split()) <= 4:
            continue  # rows of the nickname table
        for m in MULTI:
            if full.startswith(m + " ") or full == m:
                r["term"], r["definition"] = m, full[len(m):].strip()
                break
        out.append(r)
    if table_loc:
        out.append({"term": "What to call people from…", "definition": NICK, "source_key": key, "locator": table_loc})
    return out


r = inline_fix(load("2015"), "oweek-2015")
save("2015", r)

r = inline_fix(load("2016"), "oweek-2016")
r = apply(r, "oweek-2016", set_def={
    "Head Fellows": "The ones who have been planning O-Week since January. AKA Meagan, Olivia and Yash, Moliviyash, MOY, Yash, Liv and Meg, R+S— call them what you want, they just want to be your friends.",
    "Summit": "Weekend retreat during the fall semester to discuss Wiess issues and bond with other Wiessmen.",
}, drop=["O-Week", "Wiessmen."])
save("2016", r)

r = inline_fix(load("2017"), "oweek-2017")
r = apply(r, "oweek-2017", set_def={
    "Summit": "Weekend retreat during the fall semester to discuss Wiess issues and bond with other Wiessmen.",
}, drop=["Wiessmen."])
save("2017", r)

# ---------------------------------------------------------------- Owlmanac 2016 (clean)
save("2016-owlmanac", load("2016-owlmanac"))

# ---------------------------------------------------------------- 1994 (riceinfo transcription of the Freshman Handbook)
def make1994():
    src = "/home/claude/corpus/riceinfo.rice.edu-wiess/text/college__gloss.html__20001207053100.md"
    lines = open(src, encoding="utf-8").read().splitlines()
    rows = []
    term, buf = None, []

    def flush():
        if term is None:
            return
        d = " ".join(x.strip() for x in buf if x.strip())
        d = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", d)      # markdown links -> text
        d = re.sub(r"^\**\s*—\s*", "", d.replace("*", ""))
        d = re.sub(r"\s+", " ", d).strip()
        rows.append({"term": term, "definition": d, "source_key": "handbook-1994", "locator": ""})

    for l in lines:
        if l.startswith("****"):
            flush()
            t = l.strip("*").strip()
            t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t).strip("* ").strip()
            term, buf = t, []
        elif l.startswith("Last Updated"):
            flush()
            term = None
            break
        elif term is not None:
            buf.append(l)
    flush()
    # the TEAM WIESS heading is split over two lines in the markdown ("****[TEAM WIESS](...)" / "**")
    for r in rows:
        if r["term"].upper().startswith("TEAM WIESS"):
            r["term"] = "TEAM WIESS"
        if r["term"] == "Pumpkin Caroling!":
            r["term"] = "Pumpkin Caroling"
    return rows


save("1994", make1994())
