# task_extractor.py
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import spacy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TaskComponents:
    action: str = ""
    person: str = ""
    topic: str = ""
    deadline: str = ""
    language: str = "en-US"
    task_type: str = "general"
    original_text: str = ""

    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "person": self.person,
            "topic": self.topic,
            "deadline": self.deadline,
            "language": self.language,
            "task_type": self.task_type,
            "original_text": self.original_text,
        }


class NLPProcessor:
    _nlp_models = {}
    _model_names = {"en": "en_core_web_sm", "de": "de_core_news_sm"}

    @classmethod
    def get_nlp_model(cls, language: str):
        base_lang = language.split("-")[0].lower()

        if base_lang not in cls._nlp_models:
            try:
                model_name = cls._model_names.get(base_lang, "en_core_web_sm")
                cls._nlp_models[base_lang] = spacy.load(model_name)
                logger.info(f"Loaded spaCy model for {base_lang}")
            except OSError:
                logger.info(f"Downloading spaCy model for {base_lang}")
                import subprocess

                subprocess.run(
                    ["python", "-m", "spacy", "download", model_name], check=True
                )
                cls._nlp_models[base_lang] = spacy.load(model_name)
        return cls._nlp_models[base_lang]

    @classmethod
    def process_text(cls, text: str, language: str):
        nlp = cls.get_nlp_model(language)
        return nlp(text)


class TaskExtractor:
    INTRODUCTORY_PHRASES = {
        "en": [
            "i want",
            "i need",
            "please",
            "can you",
            "could you",
            "would you",
            "i would like",
            "i'd like",
            "remind me to",
            "create a task",
            "remind me",
            "add a task",
            "set a reminder",
            "schedule a",
            "make a",
            "set up a",
        ],
        "de": [
            "ich will",
            "ich möchte",
            "bitte",
            "könntest du",
            "kannst du",
            "erstelle eine aufgabe",
            "erinnere mich",
            "vergiss nicht zu",
            "füge eine aufgabe hinzu",
            "setze eine erinnerung",
            "plane einen",
            "mache einen",
            "richte ein",
            "hallo",
        ],
    }

    ACTION_PATTERNS = {
        "en": {
            "call": [
                "call",
                "phone",
                "dial",
                "ring",
                "contact",
                "reach out",
                "get in touch",
            ],
            "email": [
                "email",
                "mail",
                "message",
                "write to",
                "send message",
                "compose",
                "write",
            ],
            "meeting": [
                "meet",
                "meeting",
                "appointment",
                "schedule",
                "arrange",
                "book",
                "organize",
                "plan meeting",
            ],
            "reminder": [
                "remind",
                "reminder",
                "follow up",
                "follow-up",
                "check back",
                "touch base",
            ],
            "create": [
                "create",
                "make",
                "build",
                "prepare",
                "draft",
                "develop",
                "generate",
            ],
            "review": ["review", "check", "examine", "analyze", "look at"],
            "update": ["update", "modify", "change", "adjust", "revise"],
        },
        "de": {
            "anrufen": [
                "anrufen",
                "rufen",
                "telefonieren",
                "kontaktieren",
                "erreichen",
                "anrufe",
            ],
            "email": [
                "schreiben",
                "mailen",
                "nachricht",
                "verfassen",
                "e-mail",
                "email",
            ],
            "termin": [
                "termin",
                "meeting",
                "besprechung",
                "vereinbaren",
                "planen",
                "buchen",
                "organisieren",
            ],
            "erinnerung": [
                "erinnern",
                "erinnerung",
                "nachfassen",
                "nachverfolgen",
                "folgeup",
            ],
            "erstellen": [
                "erstellen",
                "vorbereiten",
                "entwickeln",
                "bereiten",
                "erstelle",
                "bereite",
                "entwickle",
                "machen",
                "mache",
            ],
            "prüfen": [
                "prüfen",
                "überprüfen",
                "kontrollieren",
                "analysieren",
                "checken",
                "schauen",
            ],
            "aktualisieren": [
                "aktualisieren",
                "ändern",
                "anpassen",
                "modifizieren",
                "updaten",
                "update",
            ],
        },
    }

    TASK_TYPE_MAPPING = {
        "en": {
            "call": "call",
            "email": "email",
            "meeting": "meeting",
            "reminder": "reminder",
            "create": "general",
            "review": "review",
            "update": "update",
        },
        "de": {
            "anrufen": "call",
            "email": "email",
            "termin": "meeting",
            "erinnerung": "reminder",
            "erstellen": "general",
            "prüfen": "review",
            "aktualisieren": "update",
        },
    }

    STANDARD_ACTIONS = {
        "en": {
            "call": "Call",
            "email": "Email",
            "meeting": "Schedule meeting with",
            "reminder": "Follow up with",
            "general": "Task",
            "review": "Review",
            "update": "Update",
        },
        "de": {
            "call": "Anruf mit",
            "email": "E-Mail an",
            "meeting": "Termin mit",
            "reminder": "Nachfassen bei",
            "general": "Aufgabe für",
            "review": "Prüfen",
            "update": "Aktualisieren",
        },
    }

    TITLES = {
        "en": [
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "ms",
            "ms.",
            "dr",
            "dr.",
            "miss",
            "prof",
            "prof.",
            "sir",
            "madam",
        ],
        "de": ["herr", "frau", "dr", "dr.", "prof", "prof.", "fräulein"],
    }

    TEAM_INDICATORS = {
        "en": [
            "team",
            "group",
            "department",
            "staff",
            "crew",
            "committee",
            "board",
            "panel",
        ],
        "de": [
            "team",
            "gruppe",
            "abteilung",
            "personal",
            "mannschaft",
            "ausschuss",
            "gremium",
        ],
    }

    GENERIC_PERSON_INDICATORS = {
        "en": [
            "client",
            "customer",
            "colleague",
            "manager",
            "supervisor",
            "assistant",
            "partner",
            "vendor",
            "supplier",
            "contractor",
            "representative",
            "agent",
            "contact",
            "lead",
            "prospect",
            "stakeholder",
        ],
        "de": [
            "kunde",
            "kunden",
            "kundin",
            "kollege",
            "kollegin",
            "manager",
            "managerin",
            "vorgesetzter",
            "vorgesetzte",
            "assistent",
            "assistentin",
            "partner",
            "partnerin",
            "lieferant",
            "auftragnehmer",
            "vertreter",
            "vertreterin",
            "agent",
            "agentin",
            "kontakt",
            "ansprechpartner",
            "ansprechpartnerin",
            "interessent",
            "interessentin",
        ],
    }

    GERMAN_PATTERNS = {
        "call_wegen": r"rufen\s+sie\s+(?:bitte\s+)?(?:(herr|frau|dr\.?)\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\s+wegen\s+([^,.;!?\n]+?)\s+an",
        "email_bezueglich": r"schreiben\s+sie\s+(?:bitte\s+)?(?:an\s+)?(?:(herr|frau|dr\.?)\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\s+(?:bezüglich|betreffend|über)\s+([^,.;!?\n]+)",
        "meeting_mit": r"termin\s+mit\s+(?:(herr|frau|dr\.?)\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\s+(?:für|bezüglich)\s+([^,.;!?\n]+)",
        "action_person": r"(anrufen|schreiben|kontaktieren|erreichen)\s+(?:sie\s+)?(?:bitte\s+)?(?:(herr|frau|dr\.?)\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
        "action_generic": r"(anrufen|schreiben|kontaktieren|erreichen)\s+(?:sie\s+)?(?:bitte\s+)?(?:den|die|das)?\s*(kunde|kunden|kundin|team|gruppe|kollege|kollegin)",
    }

    DEADLINE_MARKERS = {
        "en": [
            "by",
            "until",
            "before",
            "on",
            "at",
            "due",
            "in",
            "next",
            "this",
            "tomorrow",
            "today",
        ],
        "de": [
            "bis",
            "bis zum",
            "vor",
            "am",
            "um",
            "fällig",
            "in",
            "nächste",
            "nächsten",
            "morgen",
            "heute",
        ],
    }

    TIME_PATTERNS = {
        "en": [
            (
                r"\b(?:at\s+)?(\d{1,2}):(\d{2})\s*(?:am|pm)?\b",
                lambda m: f"{m.group(1)}:{m.group(2)}",
            ),
            (
                r"\b(?:at\s+)?(\d{1,2})\s*(am|pm)\b",
                lambda m: f"{m.group(1)} {m.group(2)}",
            ),
            (r"\btoday\b", "today"),
            (r"\btomorrow\b", "tomorrow"),
            (r"\bnext\s+week\b", "next week"),
            (r"\bthis\s+(morning|afternoon|evening)\b", lambda m: f"this {m.group(1)}"),
        ],
        "de": [
            (
                r"\bum\s+(\d{1,2}):(\d{2})\s*uhr\b",
                lambda m: f"{m.group(1)}:{m.group(2)}",
            ),
            (r"\bum\s+(\d{1,2})\s*uhr\b", lambda m: f"{m.group(1)}:00"),
            (r"\bheute\b", "heute"),
            (r"\bmorgen\b", "morgen"),
            (r"\bnächste\s+woche\b", "nächste Woche"),
            (
                r"\bnächsten\s+(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b",
                lambda m: f"nächsten {m.group(1)}",
            ),
            (r"\bbis\s+nächste\s+woche\b", "nächste Woche"),
        ],
    }

    def __init__(self, text: str, language: str = "en-US"):
        if not language or language not in ["en-US", "de-DE"]:
            language = "en-US"

        self.original_text = text
        self.language = language
        self.base_lang = language.split("-")[0].lower()
        self.cleaned_text = self._clean_text(text)
        self.doc = NLPProcessor.process_text(self.cleaned_text, self.language)

    def _clean_text(self, text: str) -> str:
        text_lower = text.lower().strip()

        if self.base_lang == "de":
            greetings = ["hallo", "guten tag", "guten morgen", "guten abend"]
            for greeting in greetings:
                if text_lower.startswith(greeting):
                    text = text[len(greeting) :].strip()
                    text_lower = text.lower()
                    break

        intro_phrases = self.INTRODUCTORY_PHRASES.get(
            self.base_lang, self.INTRODUCTORY_PHRASES["en"]
        )
        for phrase in sorted(intro_phrases, key=len, reverse=True):
            if text_lower.startswith(phrase):
                text = text[len(phrase) :].strip()
                text_lower = text.lower()
                break

        polite_endings = {
            "en": ["please", "thank you", "thanks", "appreciate it"],
            "de": ["bitte", "danke", "vielen dank", "danke schön"],
        }.get(self.base_lang, ["please", "thank you"])

        for ending in polite_endings:
            if text_lower.endswith(ending):
                text = text[: -len(ending)].strip()
                text_lower = text.lower()
                break

        return text

    def extract_task(self) -> TaskComponents:
        task = TaskComponents(language=self.language, original_text=self.original_text)

        if self.base_lang == "de":
            extracted = self._extract_using_german_patterns()
            if extracted:
                task.task_type = extracted.get("task_type", "general")
                task.person = extracted.get("person", "")
                task.topic = extracted.get("topic", "")
            else:
                task.task_type, main_verb = self._determine_task_type_and_verb()
                task.person = self._extract_person()
                task.topic = self._extract_topic(main_verb, task.person)
        else:
            task.task_type, main_verb = self._determine_task_type_and_verb()
            task.person = self._extract_person()
            task.topic = self._extract_topic(main_verb, task.person)

        task.action = self._standardize_action(task.task_type)
        task.deadline = self._extract_deadline()
        self._post_process_task(task)
        return task

    def _extract_using_german_patterns(self) -> Optional[Dict]:
        text = self.cleaned_text.lower()

        for pattern_name, pattern in self.GERMAN_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if (
                    pattern_name.startswith("call_")
                    or pattern_name.startswith("email_")
                    or pattern_name.startswith("meeting_")
                ):
                    title = match.group(1) if match.group(1) else ""
                    person_name = match.group(2)
                    topic = match.group(3).strip() if len(match.groups()) > 2 else ""

                    person = self._format_german_person(title, person_name)
                    topic = self._clean_german_topic(topic)

                    task_type = pattern_name.split("_")[0]
                    if task_type == "call":
                        task_type = "call"
                    elif task_type == "email":
                        task_type = "email"
                    elif task_type == "meeting":
                        task_type = "meeting"

                    return {"task_type": task_type, "person": person, "topic": topic}

                elif pattern_name == "action_person":
                    action_verb = match.group(1)
                    title = match.group(2) if match.group(2) else ""
                    person_name = match.group(3)

                    person = self._format_german_person(title, person_name)
                    task_type = self._get_task_type_from_german_verb(action_verb)
                    topic = self._extract_topic_after_person(text, person_name)

                    return {"task_type": task_type, "person": person, "topic": topic}

                elif pattern_name == "action_generic":
                    action_verb = match.group(1)
                    entity_type = match.group(2)

                    person = self._standardize_german_entity(entity_type)
                    task_type = self._get_task_type_from_german_verb(action_verb)
                    topic = self._extract_topic_after_entity(text, entity_type)

                    return {"task_type": task_type, "person": person, "topic": topic}

        return None

    def _standardize_german_entity(self, entity_type: str) -> str:
        entity_map = {
            "kunde": "Kunde",
            "kunden": "Kunden",
            "kundin": "Kundin",
            "team": "Team",
            "gruppe": "Gruppe",
            "kollege": "Kollege",
            "kollegin": "Kollegin",
        }
        return entity_map.get(entity_type.lower(), entity_type.capitalize())

    def _get_task_type_from_german_verb(self, verb: str) -> str:
        verb_mapping = {
            "anrufen": "call",
            "rufen": "call",
            "schreiben": "email",
            "kontaktieren": "general",
            "erreichen": "general",
        }
        return verb_mapping.get(verb.lower(), "general")

    def _format_german_person(self, title: str, name: str) -> str:
        if title:
            title = title.capitalize()
            if title in ["Frau", "Herr"]:
                return f"{title} {name}"
            elif title.startswith("Dr"):
                return f"Dr. {name}"
        return name

    def _clean_german_topic(self, topic: str) -> str:
        if not topic:
            return ""

        temporal_patterns = [
            r"\bbis\s+nächste\s+woche.*",
            r"\bnächste\s+woche.*",
            r"\bmorgen.*",
            r"\bheute.*",
            r"\bam\s+\w+.*",
            r"\bum\s+\d+.*",
        ]

        for pattern in temporal_patterns:
            topic = re.sub(pattern, "", topic, flags=re.IGNORECASE).strip()

        topic = re.sub(
            r"\s+(an|von|mit|zu|für|der|die|das|bis)$", "", topic, flags=re.IGNORECASE
        )
        topic = re.sub(r"\b(ihres?|seiner?|ihrer?)\s+", "", topic, flags=re.IGNORECASE)

        return topic.strip(" ,.;:")

    def _extract_topic_after_person(self, text: str, person_name: str) -> str:
        person_pos = text.lower().find(person_name.lower())
        if person_pos == -1:
            return ""

        remaining_text = text[person_pos + len(person_name) :].strip()
        topic_indicators = ["wegen", "bezüglich", "betreffend", "über", "für"]

        for indicator in topic_indicators:
            indicator_pos = remaining_text.lower().find(indicator)
            if indicator_pos != -1:
                topic_text = remaining_text[indicator_pos + len(indicator) :].strip()
                return self._clean_german_topic(topic_text)

        return ""

    def _extract_topic_after_entity(self, text: str, entity_type: str) -> str:
        entity_pos = text.lower().find(entity_type.lower())
        if entity_pos == -1:
            return ""

        remaining_text = text[entity_pos + len(entity_type) :].strip()
        topic_indicators = ["wegen", "bezüglich", "betreffend", "über", "für"]

        for indicator in topic_indicators:
            indicator_pos = remaining_text.lower().find(indicator)
            if indicator_pos != -1:
                topic_text = remaining_text[indicator_pos + len(indicator) :].strip()
                return self._clean_german_topic(topic_text)

        return ""

    def _extract_person(self) -> str:
        text = self.cleaned_text
        text_lower = text.lower()

        generic_indicators = self.GENERIC_PERSON_INDICATORS.get(self.base_lang, [])
        team_indicators = self.TEAM_INDICATORS.get(self.base_lang, [])
        all_indicators = generic_indicators + team_indicators

        for indicator in all_indicators:
            pattern = rf"\b(?:der|die|das|den|dem|the|a|an)?\s*{re.escape(indicator)}\b"
            match = re.search(pattern, text_lower)
            if match:
                return indicator.capitalize()

        titles = self.TITLES.get(self.base_lang, self.TITLES["en"])
        title_pattern = (
            r"\b("
            + "|".join(re.escape(title) + r"\.?" for title in titles)
            + r")\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)"
        )
        match = re.search(title_pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).capitalize()
            if not title.endswith(".") and title.lower() in ["dr", "prof"]:
                title += "."
            return f"{title} {match.group(2)}"

        for ent in self.doc.ents:
            if ent.label_ in ["PERSON", "PER"] and len(ent.text.split()) <= 2:
                ent_end = ent.end_char
                remaining_text = text[ent_end : ent_end + 50].lower().strip()
                if not re.match(
                    r"^\s*(tomorrow|today|at|on|by|am|pm|morgen|heute|\d)",
                    remaining_text,
                ):
                    return ent.text

        return ""

    def _determine_task_type_and_verb(self) -> Tuple[str, Optional[str]]:
        text_lower = self.cleaned_text.lower()
        patterns = self.ACTION_PATTERNS.get(self.base_lang, self.ACTION_PATTERNS["en"])
        mapping = self.TASK_TYPE_MAPPING.get(
            self.base_lang, self.TASK_TYPE_MAPPING["en"]
        )

        main_verb = None

        for action_type, keywords in patterns.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                    main_verb = keyword
                    return mapping.get(action_type, "general"), main_verb

        for token in self.doc:
            if token.pos_ == "VERB" and not token.is_stop:
                lemma = token.lemma_.lower()
                for action_type, keywords in patterns.items():
                    if lemma in keywords or token.text.lower() in keywords:
                        main_verb = token.text
                        return mapping.get(action_type, "general"), main_verb

        return "general", main_verb

    def _standardize_action(self, task_type: str) -> str:
        actions = self.STANDARD_ACTIONS.get(self.base_lang, self.STANDARD_ACTIONS["en"])
        return actions.get(task_type, "Task" if self.base_lang == "en" else "Aufgabe")

    def _extract_topic(self, main_verb: Optional[str], person: str) -> str:
        text = self.cleaned_text.lower()

        topic_indicators = {
            "en": ["about", "regarding", "concerning", "for", "on", "re:"],
            "de": ["wegen", "bezüglich", "betreffend", "über", "für", "zu"],
        }.get(self.base_lang, ["about", "regarding"])

        for indicator in topic_indicators:
            pattern = rf"\b{re.escape(indicator)}\s+([^,.;!?\n]+)"
            match = re.search(pattern, text)
            if match:
                topic = match.group(1).strip()
                temporal_words = [
                    "today",
                    "tomorrow",
                    "next week",
                    "this week",
                    "heute",
                    "morgen",
                    "nächste woche",
                ]
                for word in temporal_words:
                    topic = re.sub(rf"\b{word}.*", "", topic, flags=re.IGNORECASE)
                topic = topic.strip(" ,.;:")
                if topic:
                    return topic

        return ""

    def _extract_deadline(self) -> str:
        text = self.cleaned_text

        for ent in self.doc.ents:
            if ent.label_ in ["DATE", "TIME"]:
                return ent.text

        time_patterns = self.TIME_PATTERNS.get(self.base_lang, self.TIME_PATTERNS["en"])
        for pattern, handler in time_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return handler if isinstance(handler, str) else handler(match)

        deadline_markers = self.DEADLINE_MARKERS.get(
            self.base_lang, self.DEADLINE_MARKERS["en"]
        )
        for marker in deadline_markers:
            pattern = rf"\b{re.escape(marker)}\s+([^,.;!?\n]+)"
            match = re.search(pattern, text.lower())
            if match:
                deadline = match.group(1).strip()
                deadline = re.sub(
                    r"\b(please|bitte|an).*", "", deadline, flags=re.IGNORECASE
                )
                return deadline.strip()

        return ""

    def _post_process_task(self, task: TaskComponents):
        task.person = task.person.strip(" ,.;:") if task.person else ""
        task.topic = task.topic.strip(" ,.;:") if task.topic else ""
        task.deadline = task.deadline.strip(" ,.;:") if task.deadline else ""

        if task.person and task.topic:
            person_name = task.person.split()[-1]
            if person_name.lower() in task.topic.lower():
                task.topic = re.sub(
                    re.escape(person_name), "", task.topic, flags=re.IGNORECASE
                ).strip(" ,.;:")

        if task.task_type == "general" and task.topic:
            topic_lower = task.topic.lower()
            type_keywords = {
                "meeting": ["meeting", "termin", "besprechung"],
                "call": ["call", "anruf", "phone"],
                "email": ["email", "mail", "message", "nachricht"],
            }

            for new_type, keywords in type_keywords.items():
                if any(word in topic_lower for word in keywords):
                    task.task_type = new_type
                    task.action = self._standardize_action(new_type)
                    break


class InsuranceTaskHandler:
    INSURANCE_TERMS = {
        "en": {
            "car insurance": "auto policy",
            "home insurance": "homeowners policy",
            "consultation": "insurance consultation",
            "claim": "insurance claim",
            "policy": "insurance policy",
            "renewal": "policy renewal",
            "quote": "insurance quote",
            "application": "insurance application",
        },
        "de": {
            "autoversicherung": "KFZ-Versicherung",
            "hausratversicherung": "Hausratversicherung",
            "beratung": "Versicherungsberatung",
            "schaden": "Versicherungsfall",
            "police": "Versicherungspolice",
            "policenverlängerung": "Policeverlängerung",
            "verlängerung": "Policeverlängerung",
            "angebot": "Versicherungsangebot",
            "antrag": "Versicherungsantrag",
            "versicherungsanalyse": "Versicherungsanalyse",
            "bericht": "Bericht",
            "analyse": "Analyse",
            "update": "Update",
        },
    }

    @classmethod
    def enhance_task(cls, task: TaskComponents) -> TaskComponents:
        if not task.topic:
            return task

        base_lang = task.language.split("-")[0].lower()
        terms = cls.INSURANCE_TERMS.get(base_lang, cls.INSURANCE_TERMS["en"])

        topic_lower = task.topic.lower()
        for term, standard in terms.items():
            if term in topic_lower:
                task.topic = standard
                break

        return task


def extract_task_from_text(text: str, language: str = "en-US") -> Dict:
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string")

        extractor = TaskExtractor(text, language)
        task = extractor.extract_task()
        enhanced_task = InsuranceTaskHandler.enhance_task(task)

        return {
            "task_type": enhanced_task.task_type,
            "action": enhanced_task.action,
            "person": enhanced_task.person,
            "topic": enhanced_task.topic,
            "deadline": enhanced_task.deadline,
            "language": enhanced_task.language,
            "original_text": enhanced_task.original_text,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Error extracting task from text: {str(e)}", exc_info=True)
        return {"error": str(e), "status": "error", "original_text": text}


def generate_feedback_message(task: TaskComponents) -> str:
    base_lang = task.language.split("-")[0].lower()

    if base_lang == "en":
        parts = [f"Task created: {task.action}"]

        if task.person:
            parts.append(
                f"with {task.person}"
                if task.action.lower().startswith(("call", "email", "meet", "schedule"))
                else f"for {task.person}"
            )

        if task.topic:
            parts.append(f"regarding {task.topic}")

        if task.deadline:
            parts.append(f"(Due: {task.deadline})")

        return " ".join(parts)
    else:
        parts = [f"Aufgabe erstellt: {task.action}"]

        if task.person:
            parts.append(f"{task.person}")

        if task.topic:
            parts.append(f"betreffend {task.topic}")

        if task.deadline:
            parts.append(f"(Fällig: {task.deadline})")

        return " ".join(parts)


def format_task_for_database(
    task: TaskComponents, input_method: str = "text", user: str = "anonymous"
) -> Dict:
    created_at = datetime.now().isoformat()

    return {
        "user": user,
        "input_method": input_method,
        "original_text": task.original_text,
        "task_type": task.task_type,
        "action": task.action,
        "person": task.person,
        "topic": task.topic,
        "deadline": task.deadline,
        "language": task.language,
        "created_at": created_at,
        "status": "pending",
        "workflow_id": f"task_{int(datetime.now().timestamp())}_{task.task_type}",
    }
