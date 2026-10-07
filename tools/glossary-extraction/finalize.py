#!/usr/bin/env python3
"""Apply the hand corrections to the raw glossary extractions and write the final glossary TSVs.

The O-Week book glossaries reach the site as sources/glossaries/<year>.tsv, one row per term. The raw
extractions that run_all.py writes into out/ come from PDF text layers, and they contain words split at
line ends, terms run into their definitions, entries broken by a column change, and whole pages the
extractor could not read. Every correction below was checked by hand against the page text printed from
the corpus, and the comments say which page. Keeping them here means the TSVs can be re-derived, or a
newly found book added, without redoing that work.

It reads these files:

    out/<year>.tsv    the raw extraction of each book, in the folder of this script; written by run_all.py
    riceinfo.rice.edu-wiess/text/college__gloss.html__20001207053100.md, in the corpus folder
                      the riceinfo transcription of the 1994 Freshman Handbook glossary

and writes one TSV per glossary, with the columns term, definition, source_key and locator, creating the
folder first if it is missing:

    sources/glossaries/<year>.tsv, in this repository

The glossaries are written in this order: 2003, 2006, 2007, 2008, 2010, 2011, 2014, 2015, 2016, 2017,
2016-owlmanac, 1994. tools/paths.py finds the corpus folder
(see README.md); the output folder is always this repository's.

Run it after run_all.py, from anywhere:

    python3 tools/glossary-extraction/finalize.py

It prints "<year>: <count> rows -> <file>" for each file it writes. A line on standard error such as

    WARNING oweek-2003: set_def terms not found: ['Corner']

is not an error. It means a corrected definition matched no extracted term, so the extracted definition
was kept; the term was probably extracted under a different spelling. ("set_def" is the old name of
new_definitions in GlossaryCorrections.)

If it stops with a Python traceback, the glossaries before the one it was working on are written, the rest
are not, and that one's file may be partly written. Fix the cause and run it again.

    PermissionError or OSError at the start     GLOSSARIES_ROOT cannot be created; nothing written.
    FileNotFoundError: .../out/<year>.tsv       run run_all.py first.
    KeyError: 'term', 'definition', ...         that raw TSV lacks the column.
    TypeError or AttributeError                 a raw TSV row has fewer columns than its header.
    FileNotFoundError: ...college__gloss...     HANDBOOK_1994_FILE is missing; every glossary but 1994 is written.
"""

import csv
import os
import re
import sys
from typing import NamedTuple

# This repository's tools/ folder, for paths.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import REPOSITORY_ROOT, corpus_folder  # noqa: E402  (needs the sys.path line above)

# Where the TSVs go, and the 1994 handbook glossary in the corpus; see the module docstring.
GLOSSARIES_ROOT = f"{REPOSITORY_ROOT}/sources/glossaries"
HANDBOOK_1994_FILE = f"{corpus_folder()}/riceinfo.rice.edu-wiess/text/college__gloss.html__20001207053100.md"

# Books whose spaced em dashes (" — ") are written closed up ("—") in the TSVs, as they were edited by hand.
CLOSED_UP_DASH_GLOSSARIES = {"2003", "2006", "2007", "2008", "2010", "2011"}

# run_all.py writes the raw extraction of each book here, as <year>.tsv.
RAW_EXTRACTIONS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# (pattern, replacement) fixes for the definitions of every book, applied in this order. The specific words
# come before the general line-end rule, which would otherwise turn "girl- ask-guy" into "girlask-guy".
DEFINITION_FIXES_FOR_EVERY_BOOK = [
    (r"[⟨⟩]", ""),  # decode2014.py marks the runs it deciphered with these brackets
    ("­", ""),  # soft hyphen
    (r"girl- ask-guy", "girl-ask-guy"),
    (r"\bO- Week\b", "O-Week"),
    (r"live-inhousemate", "live-in housemate"),
    (r"wonder ful", "wonderful"),
    (r"Dar ned", "Darned"),
    (r"allnighter", "all-nighter"),
    (r"StudentCenter", "Student Center"),
    # line-end hyphenation left over after column joins: "resi- dent" becomes "resident"
    (r"(?P<before>[a-z])- (?P<after>[a-z])", r"\g<before>\g<after>"),
    (r"back-?to-?back", "back-to-back"),
    (r"\s+", " "),
]

# The 2015-2017 books run each term into its definition, so the raw extraction takes the first word as the
# term. These are the terms longer than one word, tried longest first, so that where one term starts with
# another the longer one wins.
MULTI_WORD_TERMS_LONGEST_FIRST = sorted(
    [
    "Wiess Master House (Wilson House)", "Wilson House (Wiess Master House)", "Wilson House (Wiess Magister’s House)",
    "Freshman Service Points", "Freshman One-Acts", "R2 (The Rice Review)", "Associates Night", "College Night",
    "Head Fellows", "OC Lounge", "Pumpkin Caroling", "Room Draw", "Wiess Day", "Team Wiess", "Upper Commons", "War Pig",
    "45, 90, 180", "Academic Quad", "Archi (AR-kee)", "Baker 13", "Baker Institute", "Beer Bike", "Beyond the hedges",
    "Big Three", "ChBE (“Chubby”)", "Cohen House", "D1, D2, D3", "Frog Wall", "The Hoot", "Inner Loop", "Jones School",
    "KTRU (KAY-true)", "Media Center", "Mudd Lab", "Musi (Myoo-zee)", "Outer Loop", "Private Party", "Public Party",
    "Pumpkin Grades", "The Rec", "Recharge U", "Sammy the Owl", "Tetra Points", "Willy Week", "Willy’s Statue",
    ],
    key=len,
    reverse=True,
)

# The 2015-2017 glossaries include a table, "What to call people from...", which extracts as one short row
# per college. These are the first words of those rows; the table becomes this one summary row instead.
NICKNAME_TABLE_FIRST_WORDS = {
    "WHAT", "Baker", "Will", "Hanszen", "Jones", "Brown", "Lovett", "Sid", "Martel", "McMurtry", "Duncan",
}
NICKNAME_TABLE_DEFINITION = (
    "(table) Baker—Bakerite; Will Rice—Will Ricer; Hanszen—Hanszenite; Jones—Jonesian; Brown—Brownie; "
    "Lovett—Lovetteer; Sid Richardson—Sidizen; Martel—Martelian; McMurtry—Murt; Duncan—Duncaroo."
)

# The page in a locator such as "p.104": its first run of digits.
PAGE_NUMBER_PATTERN = re.compile(r"(?P<page_number>\d+)")

# A Markdown link, "[text](address)": the text is kept and the address dropped.
MARKDOWN_LINK_PATTERN = re.compile(r"\[(?P<link_text>[^\]]+)\]\([^)]+\)")


class GlossaryCorrections(NamedTuple):
    """The hand corrections for one book's glossary, each checked against the page text.

    Terms are matched as they appear in out/<year>.tsv, with surrounding spaces removed but before any other
    cleaning, so a term with a trailing full stop must be written with it ("campus.").
    """

    source_key: str  # the book's bibliography key, e.g. "oweek-2003"; also the source_key of added entries
    new_definitions: dict[str, str] = {}  # extracted term -> the definition that replaces the extracted one
    dropped_terms: list[str] = []  # extracted terms to remove, mostly scraps of a definition taken for a term
    renamed_terms: dict[str, str] = {}  # extracted term -> the term to write instead
    dropped_locators: list[str] = []  # every row on these pages is removed, for pages transcribed by hand
    added_entries: list[tuple[str, str, str]] = []  # (term, definition, locator) for entries the extraction missed


# 2003: the conclusions PDF, pp.3-7.
CORRECTIONS_2003 = GlossaryCorrections(
    source_key="oweek-2003",
    new_definitions={
        "Battlesows": "1. Affectionate name for the back-to-back defending champion Wiess powderpuff football team.",
        "Christie": (
            "1. Wiess RA and wife of Doward. Class of 2001 from South Dakota. A chemical engineer with crazy work "
            "hours and the ability to organize anything."
        ),
        "Coffeehouse Night": "1. An evening of entertainment featuring performing Wiessmen and free caffeine.",
        "College night": (
            "1. A day filled with college bonding, hanging out, a nice dinner and an evening of entertainment. Always "
            "held the last day of classes."
        ),
        "Corner": (
            "1. To pull up an extra chair at the corner of a table. Frequently occurs during meals, but never at "
            "formal occasions."
        ),
        "Doward": (
            "1. Wiess RA and husband of Christie. Class of 2001. Most likely to find him fixing computers on campus or "
            "vegging in the Acabowl."
        ),
        "Family Style": (
            "1. The faster, funner, better way that Wiessmen choose to eat. Once a week, we all sit and eat as a "
            "family instead of plodding through the kitchen line like the drones at other college. The night features "
            "entertainment, freshmen waiters, bonding and, if you’re lucky, a ubangee."
        ),
        "Filmest": (
            "1. A 24-hour film marathon held during Dead Week. 2. The best way to waste time when you should be "
            "studying."
        ),
        "Five-man": "1. Popular suite at Wiess, which typically ends up being a hangout location for thirsty Wiessmen.",
        "Freshmen One-Acts": (
            "1. First Tabletop production of the year, which includes, you guessed it, one-acts featuring freshfers."
        ),
        "Jamfest": (
            "1. One of the coolest parties at Rice. Held during Owl Weekend, Wiess books live bands and people hang "
            "out in the Acabowl all day."
        ),
        "Katharine": (
            "1. Master of Wiess. Sociology professor by day, Latin dancer by night. An all-around cool person."
        ),
        "Moment of Silence": (
            "1. Honor given to a deserving individual at family style to break the ear-shattering noise of plate "
            "banging. “Hi, my name is [insert name here]. May I please have a moment of silence?”"
        ),
        "Night of Decadence (NOD)": (
            "1. The best party at Rice. Held at Wiess on the last Friday of October, it features a live band, "
            "interesting decorations and creative costumes."
        ),
        "PDR": (
            "1. Private dining room. A smaller room attached to the Commons. Used for studying and as a dressing room "
            "during Tabletop productions."
        ),
        "Pumpkin caroling": (
            "1. The spreading of Halloween cheer, led by the College Idiot. Features Halloween songs, candles and a "
            "visit to the Gillis home."
        ),
        "Summit": "1. Weekend retreat to discuss Wiess issues and bond far away from campus.",
        "TV room": (
            "1. An awesome room on the fourth floor, featuring a big-screen TV and surround sound. Site of film fest "
            "and open for use at any time."
        ),
        "Beer-Bike": (
            "1. A competitive inter-college race held in the spring in which ten bikers and ten chuggres from each "
            "collge compete in a strugle for personal and college pride. 2. A day full of events, including the race, "
            "a parade and a water balloon fight."
        ),
        "CCA": (
            "1. College Computing Associates 2. Friendly people in your college who will help you when your computer "
            "acts up"
        ),
        "Cloisters": "1. Collection of offices adjactent to the Student Center",
        "Early ’80s": "1. Party that brings back both memories and clothing.",
        "Hanszen": (
            "1. A lesser college distinguished by its lack of anything cool. 2. A lesser college undistinguishable "
            "from a pile of bricks."
        ),
        "Jones": (
            "1. A lesser college distinguished by the brightly colored Jones House 2. A lesser college "
            "indistinguishable from Brown."
        ),
        "Outer Loop": "1. The path that encircles campus 2. A 3-mile long path that greats for a jog.",
        "Sammy the Owl": "1. The Rice mascot",
    },
    dropped_terms=["campus.", "on campus.", "jog."],
    added_entries=[
        (
            "Dr. Bill",
            "1. Wiess RA. Electrical Engineering Professor Dr. William Wilson. A great friend and mentor to all "
            "Wiessmen. Catch him setting up Tabletop sets, recording things on campus and taking pictures wherever he "
            "goes.",
            "p.3",
        ),
        ("Tabletop", "1. Wiess theatre. 2. The best theatre production group on campus.", "p.4"),
        (
            "Team Wiess",
            "1. The most powerful cheer on campus. 2. The embodiment of everything that makes Wiess College cool.",
            "p.4",
        ),
        (
            "Club 13",
            "1. An organization whose sole function is to undress, smear shaving cream on their bodies and run around "
            "campus leaving a slimy trail of body prints. 2. A favorite target of Wiessmen with buckets of water.",
            "p.5",
        ),
        ("Esperanza", "1. Fall formal. Traditionally a girl-ask-guy affair.", "p.5"),
        (
            "Hedges",
            "1. Extensive botanical growth that surrounds campus and is in the quad. 2. “Beyond the hedges” refers to "
            "the world beyond Rice. 3. Fun things to jump over.",
            "p.5",
        ),
        ("P/F", "1. Pass-fail. A fun way to take a class.", "p.6"),
        ("S/E", "A student majoring in science or engineering", "p.7"),
    ],
)

# 2008: Part 7, pp.3-7.
CORRECTIONS_2008 = GlossaryCorrections(
    source_key="oweek-2008",
    new_definitions={
        "Quad": "1. The central academic quadrangle around Willy’s Statue.",
        "SCC": (
            "1. College Computing Associates. 2. Friendly people in your college who will help you when your computer "
            "acts up."
        ),
        "Sid Rich": (
            "1. A lesser college distinguished by its height. 2. A lesser college indistinguishable from the Medical "
            "Center."
        ),
        "Trasher": "1. The April’s Fool newspaper.",
    },
    added_entries=[
        (
            "SMR",
            "1. Student Maintenance Representative. 2. The person to find if you lose your key or something breaks.",
            "part 7 p.7",
        ),
        (
            "U. Blue",
            "1. Undergraduate literary magazine. 2. Also, there is R2, Rice's newest literary publication.",
            "part 7 p.7",
        ),
    ],
)

# 2011: pp.92-96, glyph cipher decoded.
CORRECTIONS_2011 = GlossaryCorrections(
    source_key="oweek-2011",
    new_definitions={
        "Freshmen Service Points": (
            "1. It’s called “giving back to the wonderful place that is Wiess.” 2. Four hours of required service for "
            "freshmen."
        ),
        "Archi (AR-kee)": "A student majoring in architecture.",
        "Baker": (
            "1. A lesser college distinguished by its old Commons. 2. A lesser college indistinguishable from "
            "neighboring Will Rice."
        ),
        "Inner Loop": "One-way loop that runs around the center of campus.",
        "Sallyport": "1. The big archway in Lovett Hall. 2. DO NOT walk out of it until you graduate!",
        "RMC": (
            "1. Rice Memorial Center. 2. The Student Center. 3. Where you can find the bookstore, the convienence "
            "store, and Smoothie King (yummy!)."
        ),
        "SMR": "1. Student Maintenance Representative. 2. The person to find if you lose your key or something breaks.",
        "Will Rice": (
            "1. A lesser college distinguished by its obsession with Beer-Bike. 2. A lesser college indistinguishable "
            "from Baker."
        ),
    },
    dropped_terms=[".", "able"],
    added_entries=[
        ("Ironman/Ironwoman", "Someone who bikes and chugs at Beer Bike.", "p.95"),
        ("Squirrels", "Creatures seen throughout campus. Known to be very crazy.", "p.96"),
    ],
)

# 2014: pp.102-106; Rice Speak pp.104 and 106 hand-transcribed.
CORRECTIONS_2014 = GlossaryCorrections(
    source_key="oweek-2014",
    new_definitions={
        "Basement": (
            "The area under the Commons used for storage and shirt screen making. Can be accessed using your room key."
        ),
        "Benjamin and Jenna": (
            "Wiess Aca-children, son and daughter of the Byrds, who love jumping on the trampoline and reading."
        ),
        "College Night": (
            "A day filled with college bonding, hanging out, a nice dinner, and an evening of entertainment. Wiess' is "
            "always held the last day of classes each semester. Each college has their own college night, which are "
            "not always on the last day of classes."
        ),
        "Freshmen Service Points": (
            "Four hours of required service to Wiess. Necessary to enter the housing jack at the end of your first "
            "year. There are plenty of opportunities to get them!"
        ),
        "Pumpkin caroling": (
            "The spreading of Halloween cheer, led by the College Idiots. Features Halloween songs, candles, and a "
            "visit to the other colleges."
        ),
        "Team Wiess": (
            "The most powerful cheer on campus, and the embodiment of everything that makes Wiess College cool."
        ),
        "Wiessmen": "The inclusive, gender neutral term for the women and men of Wiess College. This includes you.",
        "H&D": (
            "Housing and Dining. Administrative office in charge of all food service and residential buildings on "
            "campus."
        ),
        "Jack": "A prank pulled on another college.",
        "Leebron (and Ping)": (
            "David Leebron - President of the University. Married to Ping.. Also sends fascinating holiday e-card "
            "every year."
        ),
        "Matriculation": "Ceremony held during O-Week to officially welcome you to Rice.",
        "Mudd Lab": (
            "The university computer/IT center. If you have problems with your computer, the people here are glad to "
            "help out. Also a great place to print large posters"
        ),
        "Meet Sheet": "Officially called First Look, a book with a catalogue of pictures of all incoming students.",
        "MOB": (
            "The Marching Owl Band. That doesn’t march. They always put on an entertaining show during halftime, "
            "filled with amusing skits, jibes at opposing teams, and zany antics."
        ),
    },
    dropped_terms=["Affectionate name for the Wiess powder-"],
    dropped_locators=["p.104", "p.106"],
    added_entries=[
        ("Battlesows", "Affectionate name for the Wiess powderpuff football team.", "p.102"),
        ("Big Bang", "Event held for the new students after they ace their first round of exams.", "p.102"),
        (
            "Goldenrod",
            "The official Wiess color. It will soon dominate your wardrobe. Remember it's not yellow!",
            "p.103",
        ),
        (
            "Renata",
            "Third floor RA and Bioengineering lecturer. Loves to talk and make delicious Mexican food. Married to "
            "Lenin, proud mama of Gavin. Also a shirt-screening expert!",
            "p.103",
        ),
        ("Jonesian", "A member of Jones college.", "p.105"),
        ("Lovetteer", "A resident of Lovett College", "p.105"),
        # p.104—Rice Speak, first page
        ("45, 90, 180", "Three big slabs of rock in the Engineering Quad.", "p.104"),
        ("’80s Party", "Party held at Sid Rich college that brings back both awesome music and clothing.", "p.104"),
        ("Academ", "A person majoring in humanities or social sciences.", "p.104"),
        ("Academic Quad", "The central academic quadrangle around Willy’s Statue.", "p.104"),
        ("Archi (AR-kee)", "A student majoring in architecture.", "p.104"),
        ("ASB", "Alternative Spring Break; service project over spring break, often in another state.", "p.104"),
        (
            "Associate",
            "Faculty, staff, or community members associated with a college. Darned good people to know.",
            "p.104",
        ),
        ("Autry", "Gym in Tudor Fieldhouse where the Rice basketball team plays.", "p.104"),
        ("Backpage", "The humorous last page of the Thresher.", "p.104"),
        ("Bakerite", "A resident of Baker College.", "p.104"),
        (
            "Baker 13",
            "An organization whose sole function is to undress, smear shaving cream on their bodies, and run around "
            "campus leaving a slimy trail of body prints. A favorite target of Wiessmen with buckets of water.",
            "p.104",
        ),
        (
            "Beer Bike",
            "A competitive intercollege race held in the spring in which ten bikers and ten chuggers from each "
            "college compete in a struggle for personal and college pride. Also includes a water balloon fight and "
            "much rejoicing.",
            "p.104",
        ),
        ("Beyond the hedges", "A term to describe the “real word” outside of Rice.", "p.104"),
        (
            "Big Three",
            "Classes frequently taken by freshmen science and engineering majors: Physics, Chemistry, and Calculus.",
            "p.104",
        ),
        (
            "Brochstein",
            "A modernistic glass building located behind Fondren. Home to Salento (a non-student operated coffeeshop) "
            "and is a great place to relax and sit outside.",
            "p.104",
        ),
        ("Brownie", "A resident of Brown College.", "p.104"),
        (
            "Campanile",
            "1. The bell tower in the Engineering quad. 2. Rice’s yearbook 3. An undergraduate orchestras.",
            "p.104",
        ),
        ("Cloisters", "Collection of offices adjacent to the Student Center.", "p.104"),
        (
            "Coffeehouse",
            "Student-run shop in the Student Center that provides caffeine to needy students. Also a great place to "
            "study and/or pretend to be a hipster.",
            "p.104",
        ),
        ("Cohen House", "The faculty dining club near Sewall Hall. Eat here if you get a chance.", "p.104"),
        (
            "D1, D2, D3",
            "Refers to distribution credits, Rice's way of making sure you get a balanced education. 12 credit hours "
            "of each category are required to graduate. D1 = humanities, D2 = social sciences, D3 = science and "
            "engineering.",
            "p.104",
        ),
        ("DMC", "The Digital Media Center. Lots of computers to use and cool equipment to check out.", "p.104"),
        ("Duncaroo", "A resident of Duncan College.", "p.104"),
        ("Esperanza", "Fall formal. A major part of homecoming weekend and lots of fun!", "p.104"),
        # p.106—Rice Speak, last page
        ("Pumpkin Grades", "Mid-semester grades given to new students in the fall.", "p.106"),
        ("R2 (The Rice Review)", "An independent literary magazine published entirely by students", "p.106"),
        ("Recharge U", "Campus convenience store in the RMC.", "p.106"),
        ("REMS", "Rice students that are trained as EMTs. Respond to emergencies on campus.", "p.106"),
        ("Rice Players", "Only campus theater group not associated with a college.", "p.106"),
        (
            "RMC",
            "Rice Memorial Center, also referred to as the Student Center. This is where you can find the bookstore, "
            "the convenience store, Coffeehouse, Pub, and important offices like Academic Advising.",
            "p.106",
        ),
        (
            "RPC",
            "Rice Program Council. The organization in charge of all university-wide events, like Beer Bike, Screw "
            "Yer Roommate, Ezperanza, and study breaks during finals.",
            "p.106",
        ),
        (
            "SA",
            "Student Association. The campus-wide body representing students. Deals with campus-wide issues and "
            "administrative business.",
            "p.106",
        ),
        (
            "Sallyport",
            "The big archway in Lovett Hall. Tradition holds that if you walk through it between matriculation and "
            "graduation, you won't graduate.",
            "p.106",
        ),
        ("Sammy the Owl", "The Rice mascot.", "p.106"),
        ("S/E", "A student majoring in science or engineering.", "p.106"),
        ("Sidizen", "A resident of Sid Richardson College.", "p.106"),
        (
            "SMR",
            "Student Maintenance Representative. The liaison between H&D and the students. They can help you change "
            "the height of your bed or change your light bulbs.",
            "p.106",
        ),
        (
            "SpoCo",
            "Spontaneous Combustion, the improv skit group on campus. Check out one of their shows, they’re very "
            "funny!",
            "p.106",
        ),
        (
            "Squirrels",
            "Creatures seen throughout campus. Known to be very crazy and totally unafraid of humans.",
            "p.106",
        ),
        ("TC", "Taco Cabana. A twenty-four hour food-serving institution and an all-nighter’s best friend.", "p.106"),
        ("Tetra Points", "Credit on your meal plan used to buy food at the RMC or the Hoot.", "p.106"),
        (
            "Thresher",
            "Rice’s student-operated newspaper. Check out the Backpage for some ol’ time ribbing, hehehe.",
            "p.106",
        ),
        ("Ultimate", "The frisbee-lacrosse-soccer amalgam frequently played on campus.", "p.106"),
        (
            "Valhalla",
            "The other on-campus pub, often populated by grad students, but a great place for cheap beer.",
            "p.106",
        ),
        (
            "Village",
            "The shopping center west of campus. Has lots of great restaurants and shops, all within walking distance!",
            "p.106",
        ),
        (
            "Whataburger",
            "A 24-hour restaurant to get a burger or legendary Honey Butter Chicken Biscuit. Ask for Texas Toast—it’s "
            "the only way to truly eat a Whataburger.",
            "p.106",
        ),
        ("Wiess", "Your home and family.", "p.106"),
        ("Will Ricer", "A resident of Will Rice College", "p.106"),
        ("Willy Week", "The week preceding Beer Bike, filled with college activities, alumni, and jacks.", "p.106"),
        (
            "Willy’s Statue",
            "A two-ton brass likeness of the founder of the university located in the center of the Academic Quad.",
            "p.106",
        ),
        (
            "Y’all",
            "Southern slang short for \"you all.\" Something you have to get used to. Y'all will be saying this if "
            "you want to or not.",
            "p.106",
        ),
    ],
)

# 2016 and 2017: inline "Term Definition" style, so split_inline_terms() runs first.
CORRECTIONS_2016 = GlossaryCorrections(
    source_key="oweek-2016",
    new_definitions={
        "Head Fellows": (
            "The ones who have been planning O-Week since January. AKA Meagan, Olivia and Yash, Moliviyash, MOY, Yash, "
            "Liv and Meg, R+S— call them what you want, they just want to be your friends."
        ),
        "Summit": "Weekend retreat during the fall semester to discuss Wiess issues and bond with other Wiessmen.",
    },
    dropped_terms=["O-Week", "Wiessmen."],
)

CORRECTIONS_2017 = GlossaryCorrections(
    source_key="oweek-2017",
    new_definitions={
        "Summit": "Weekend retreat during the fall semester to discuss Wiess issues and bond with other Wiessmen.",
    },
    dropped_terms=["Wiessmen."],
)


def main() -> None:
    """Correct and write each glossary in turn, printing one line per file written.

    Each book is read, corrected and written before the next is read, so a run that stops leaves the
    earlier books written; the module docstring lists the failures.
    """
    os.makedirs(GLOSSARIES_ROOT, exist_ok=True)
    write_glossary("2003", apply_corrections(read_raw_extraction("2003"), CORRECTIONS_2003))
    # 2006 and 2007 are clean apart from DEFINITION_FIXES_FOR_EVERY_BOOK.
    write_glossary("2006", read_raw_extraction("2006"))
    write_glossary("2007", read_raw_extraction("2007"))
    write_glossary("2008", apply_corrections(read_raw_extraction("2008"), CORRECTIONS_2008))
    write_glossary("2010", read_raw_extraction("2010"))  # clean
    write_glossary("2011", apply_corrections(read_raw_extraction("2011"), CORRECTIONS_2011))
    write_glossary("2014", sort_by_page(apply_corrections(read_raw_extraction("2014"), CORRECTIONS_2014)))
    write_glossary("2015", split_inline_terms(read_raw_extraction("2015"), "oweek-2015"))
    write_glossary(
        "2016",
        apply_corrections(split_inline_terms(read_raw_extraction("2016"), "oweek-2016"), CORRECTIONS_2016),
    )
    write_glossary(
        "2017",
        apply_corrections(split_inline_terms(read_raw_extraction("2017"), "oweek-2017"), CORRECTIONS_2017),
    )
    write_glossary("2016-owlmanac", read_raw_extraction("2016-owlmanac"))  # clean
    write_glossary("1994", read_handbook_1994_glossary())


def read_raw_extraction(glossary_name: str) -> list[dict[str, str]]:
    """Return the rows of out/<glossary_name>.tsv as dictionaries keyed by its header.

    The file is read with the csv module's default quoting, although run_all.py writes it without quoting.
    A field that begins with a straight double quote is therefore read as a quoted field: the quotes are
    dropped, and any tabs and line breaks up to the next double quote become part of that one field.
    """
    with open(f"{RAW_EXTRACTIONS_ROOT}/{glossary_name}.tsv", encoding="utf-8", newline="") as raw_extraction:
        return [dict(row) for row in csv.DictReader(raw_extraction, delimiter="\t")]


def apply_corrections(rows: list[dict[str, str]], corrections: GlossaryCorrections) -> list[dict[str, str]]:
    """Return the rows with one book's corrections applied, warning about new definitions that matched nothing.

    Every correction matches the term as extracted, so a renamed term is redefined under its old spelling.
    Added entries go at the end; a book whose page order matters is sorted afterwards (see sort_by_page).
    The rows passed in are changed in place.
    """
    dropped_terms = set(corrections.dropped_terms)
    corrected_rows = []
    redefined_terms = set()
    for row in rows:
        extracted_term = row["term"].strip()
        # The locator is read only when there are pages to drop, so a file without a locator column still
        # gets this far.
        if extracted_term in dropped_terms or (
            corrections.dropped_locators and row["locator"] in corrections.dropped_locators
        ):
            continue
        if extracted_term in corrections.new_definitions:
            row["definition"] = corrections.new_definitions[extracted_term]
            redefined_terms.add(extracted_term)
        if extracted_term in corrections.renamed_terms:
            row["term"] = corrections.renamed_terms[extracted_term]
        corrected_rows.append(row)

    terms_not_found = set(corrections.new_definitions) - redefined_terms
    if terms_not_found:
        print(
            f"  WARNING {corrections.source_key}: set_def terms not found: {sorted(terms_not_found)}",
            file=sys.stderr,
        )
    for term, definition, locator in corrections.added_entries:
        corrected_rows.append(
            {"term": term, "definition": definition, "source_key": corrections.source_key, "locator": locator}
        )
    return corrected_rows


def sort_by_page(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Sort the rows in place by the page in their locator, keeping their order within a page; return them.

    The 2014 corrections add whole hand-transcribed pages at the end; this puts them back in page order.
    A locator without a number stops the run with a traceback.
    """
    rows.sort(key=lambda row: int(PAGE_NUMBER_PATTERN.search(row["locator"])["page_number"]))
    return rows


def split_inline_terms(rows: list[dict[str, str]], source_key: str) -> list[dict[str, str]]:
    """Return the rows with multi-word terms split from their definitions and the nickname table summarised.

    In the 2015-2017 books each term runs straight into its definition ("Wiess Day The day..."), and the
    raw extraction takes the first word as the term. This rejoins the two and splits them after the
    longest matching term in MULTI_WORD_TERMS_LONGEST_FIRST instead; a row that matches none is kept as it
    is. The nickname table's heading row is dropped, and so is every later row of at most four words whose
    term is in NICKNAME_TABLE_FIRST_WORDS; one summary row, at the heading's locator, is added at the end.
    The rows passed in are changed in place.
    """
    split_rows = []
    table_locator = None
    for row in rows:
        whole_entry = (row["term"].strip() + " " + row["definition"].strip()).strip()
        if row["term"].strip() == "WHAT" and whole_entry.startswith("WHAT TO CALL PEOPLE FROM"):
            table_locator = row["locator"]
            continue
        if table_locator and row["term"].strip() in NICKNAME_TABLE_FIRST_WORDS and len(whole_entry.split()) <= 4:
            continue  # a row of the nickname table
        for multi_word_term in MULTI_WORD_TERMS_LONGEST_FIRST:
            if whole_entry.startswith(multi_word_term + " ") or whole_entry == multi_word_term:
                row["term"], row["definition"] = multi_word_term, whole_entry[len(multi_word_term):].strip()
                break
        split_rows.append(row)
    if table_locator:
        split_rows.append(
            {
                "term": "What to call people from…",
                "definition": NICKNAME_TABLE_DEFINITION,
                "source_key": source_key,
                "locator": table_locator,
            }
        )
    return split_rows


def read_handbook_1994_glossary() -> list[dict[str, str]]:
    """Return the 1994 Freshman Handbook glossary, read from its riceinfo transcription.

    In the Markdown each entry starts with a heading line beginning "****" (the term in bold, sometimes
    as a link), and its definition is every line up to the next heading. The glossary ends at the
    "Last Updated" line. The rows have no locator, since the transcription has no page numbers.
    """
    with open(HANDBOOK_1994_FILE, encoding="utf-8") as handbook:
        lines = handbook.read().splitlines()

    entries: list[tuple[str, list[str]]] = []  # (term, the definition's lines) in order
    for line in lines:
        if line.startswith("Last Updated"):
            break
        if line.startswith("****"):
            entries.append((read_handbook_term(line), []))
        elif entries:
            _, definition_lines = entries[-1]
            definition_lines.append(line)

    return [
        {
            "term": term,
            "definition": read_handbook_definition(definition_lines),
            "source_key": "handbook-1994",
            "locator": "",
        }
        for term, definition_lines in entries
    ]


def read_handbook_term(heading_line: str) -> str:
    """Return the term in a handbook heading line, without its bold markers or link."""
    term = heading_line.strip("*").strip()
    term = MARKDOWN_LINK_PATTERN.sub(r"\g<link_text>", term).strip("* ").strip()
    # The TEAM WIESS heading is split over two lines in the Markdown ("****[TEAM WIESS](...)" / "**").
    if term.upper().startswith("TEAM WIESS"):
        term = "TEAM WIESS"
    if term == "Pumpkin Caroling!":
        term = "Pumpkin Caroling"
    return term


def read_handbook_definition(definition_lines: list[str]) -> str:
    """Return a handbook definition as one line of plain text, without Markdown links, bold or its opening dash."""
    definition = " ".join(line.strip() for line in definition_lines if line.strip())
    definition = MARKDOWN_LINK_PATTERN.sub(r"\g<link_text>", definition)
    # An em dash that opens the definition, with any asterisks before it (none are left by now).
    definition = re.sub(r"^\**\s*—\s*", "", definition.replace("*", ""))
    return re.sub(r"\s+", " ", definition).strip()


def write_glossary(glossary_name: str, rows: list[dict[str, str]]) -> None:
    """Write sources/glossaries/<glossary_name>.tsv from the rows, cleaning each term and definition.

    The Rice-speak section repeats "College night" with a different sense: keep both rows, marking the
    second so the series tool (tools/build_glossary_series.py) does not collapse them. Fields are written
    without quoting; cleaning turns any tab in a term or definition into a space.
    """
    cleaned_terms_seen = set()
    for row in rows:
        cleaned_term = clean_term(row["term"]).lower()
        if cleaned_term in cleaned_terms_seen and cleaned_term == "college night":
            row["term"] = clean_term(row["term"]) + " [Rice speak]"
        cleaned_terms_seen.add(cleaned_term)

    if glossary_name in CLOSED_UP_DASH_GLOSSARIES:
        for row in rows:
            row["definition"] = row["definition"].replace(" — ", "—")

    glossary_file = f"{GLOSSARIES_ROOT}/{glossary_name}.tsv"
    with open(glossary_file, "w", encoding="utf-8") as glossary:
        glossary.write("term\tdefinition\tsource_key\tlocator\n")
        for row in rows:
            glossary.write(
                f"{clean_term(row['term'])}\t{clean_definition(row['definition'])}\t"
                f"{row['source_key']}\t{row['locator']}\n"
            )
    print(f"{glossary_name}: {len(rows)} rows -> {glossary_file}")


def clean_term(term: str) -> str:
    """Return the term without decoding brackets, extra spaces or a final full stop (kept after an initial: "U.")."""
    term = re.sub(r"[⟨⟩]", "", term).strip()
    term = re.sub(r"\s+", " ", term)
    if term.endswith(".") and not re.search(r"\b[A-Z]\.$", term):
        term = term[:-1]
    return term


def clean_definition(definition: str) -> str:
    """Return the definition with DEFINITION_FIXES_FOR_EVERY_BOOK applied."""
    for pattern, replacement in DEFINITION_FIXES_FOR_EVERY_BOOK:
        definition = re.sub(pattern, replacement, definition)
    return definition.strip()


if __name__ == "__main__":
    main()
