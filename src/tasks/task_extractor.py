# task_extractor.py
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import spacy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TaskComponents:
    """Data class to store extracted task components."""

    action: str = ""
    person: str = ""
    topic: str = ""
    deadline: str = ""
    language: str = "en"
    task_type: str = "general"

    def to_dict(self) -> Dict:
        """Convert task components to dictionary."""
        return {
            "action": self.action,
            "person": self.person,
            "topic": self.topic,
            "deadline": self.deadline,
            "language": self.language,
            "task_type": self.task_type,
        }


class LanguageDetector:
    """Detect language from input text."""

    # German keywords that indicate the text might be in German
    GERMAN_KEYWORDS = {
        # Task verbs
        "anrufen",
        "telefonieren",
        "senden",
        "schicken",
        "erstellen",
        "planen",
        "organisieren",
        "vereinbaren",
        "einrichten",
        "einstellen",
        "erledigen",
        "ruf",
        "rufe",
        "schreibe",
        "erstelle",
        "plane",
        "notiere",
        "dokumentiere",
        # Task nouns
        "termin",
        "besprechung",
        "sitzung",
        "anruf",
        "email",
        "nachricht",
        "aufgabe",
        "treffen",
        "konferenz",
        "meeting",
        "erinnerung",
        "folgetermin",
        # Insurance terms
        "versicherung",
        "angebot",
        "beratung",
        "schaden",
        "kunde",
        "police",
        # Common prepositions and articles
        "über",
        "mit",
        "für",
        "wegen",
        "zum",
        "zur",
        "bis",
        "am",
        "um",
        "der",
        "die",
        "das",
        "dem",
        "den",
        "herr",
        "frau",
    }

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detect language of input text.

        Args:
            text: Input text to analyze

        Returns:
            Language code ('en' or 'de')
        """
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()

        # Split into words and check for German keywords
        words = re.findall(r"\b\w+\b", text_lower)
        german_word_count = sum(1 for word in words if word in cls.GERMAN_KEYWORDS)

        # Check for German-specific patterns
        has_german_patterns = any(
            [
                "herr " in text_lower,
                "frau " in text_lower,
                " bis " in text_lower,
                " bitte " in text_lower,
                " kannst du " in text_lower,
                " möchte " in text_lower,
            ]
        )

        # If more than 1 German keyword or specific patterns, classify as German
        if german_word_count > 1 or has_german_patterns:
            return "de"
        return "en"


class NLPProcessor:
    """Process text using spaCy NLP models."""

    # Dictionary to store loaded spaCy models
    _nlp_models = {}

    # Mapping of language codes to spaCy model names
    _model_names = {"en": "en_core_web_sm", "de": "de_core_news_sm"}

    @classmethod
    def get_nlp_model(cls, language: str):
        """
        Get or load spaCy model for the specified language.

        Args:
            language: Language code ('en' or 'de')

        Returns:
            Loaded spaCy model
        """
        if language not in cls._nlp_models:
            try:
                cls._nlp_models[language] = spacy.load(cls._model_names[language])
                logger.info(f"Loaded spaCy model for {language}")
            except OSError:
                logger.info(f"Downloading spaCy model for {language}")
                import subprocess

                subprocess.run(
                    ["python", "-m", "spacy", "download", cls._model_names[language]],
                    check=True,
                )
                cls._nlp_models[language] = spacy.load(cls._model_names[language])

        return cls._nlp_models[language]

    @classmethod
    def process_text(cls, text: str, language: str):
        """
        Process text with spaCy.

        Args:
            text: Text to process
            language: Language code ('en' or 'de')

        Returns:
            spaCy Doc object
        """
        nlp = cls.get_nlp_model(language)
        return nlp(text)


# We'll continue from where the code in paste-2.txt left off


# Finishing the task_extractor.py file
class TaskExtractor:
    """Extract task components from text."""

    # Phrases to ignore at the beginning of the command (introductory phrases)
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
            "i wish",
            "remind me to",
            "make sure to",
            "don't forget to",
            "please create",
            "please make",
            "create a task",
            "create a reminder",
            "remind me",
        ],
        "de": [
            "ich will",
            "ich möchte",
            "ich wünsche",
            "bitte",
            "könntest du",
            "kannst du",
            "würdest du",
            "ich hätte gerne",
            "erstelle eine aufgabe",
            "erstelle einen termin",
            "erstelle eine erinnerung",
            "erinnere mich",
            "vergiss nicht zu",
            "denk daran",
        ],
    }

    # Insurance-specific action verbs mapped to standardized tasks
    INSURANCE_ACTIONS = {
        "en": {
            "call": ["call", "phone", "dial", "ring", "call back", "callback"],
            "email": [
                "email",
                "mail",
                "message",
                "write",
                "send an email",
                "send a message",
            ],
            "meet": [
                "meet",
                "appointment",
                "schedule",
                "arrange",
                "setup",
                "organize",
                "book",
                "consultation",
            ],
            "create": ["create", "make", "build", "prepare", "draft", "document"],
            "send": ["send", "deliver", "share", "forward", "offer"],
            "remind": [
                "remind",
                "reminder",
                "follow-up",
                "follow up",
                "schedule a reminder",
            ],
            "document": ["document", "note", "record", "write down", "take note"],
            "followup": ["follow up", "check back", "contact again"],
        },
        "de": {
            "anrufen": [
                "anrufen",
                "telefonieren",
                "kontaktieren",
                "rückruf",
                "zurückrufen",
            ],
            "email": ["emailen", "mailen", "schreiben", "nachricht senden", "schicken"],
            "treffen": [
                "treffen",
                "termin",
                "vereinbaren",
                "planen",
                "organisieren",
                "beratung",
            ],
            "erstellen": [
                "erstellen",
                "anlegen",
                "vorbereiten",
                "entwerfen",
                "dokumentieren",
            ],
            "senden": ["senden", "schicken", "teilen", "weiterleiten", "angebot"],
            "erinnern": ["erinnern", "erinnerung", "folgetermin", "nachfassen"],
            "dokumentieren": [
                "dokumentieren",
                "notieren",
                "aufschreiben",
                "festhalten",
            ],
            "nachfassen": ["nachfassen", "nachverfolgen", "wieder kontaktieren"],
        },
    }

    # Task type mapping - maps actions to standardized task types
    TASK_TYPE_MAPPING = {
        "en": {
            "call": "call",
            "email": "email",
            "meet": "meeting",
            "remind": "reminder",
            "document": "document",
            "followup": "followup",
            "send offer": "offer",
            "send": "email",
            "create": "general",
        },
        "de": {
            "anrufen": "call",
            "email": "email",
            "treffen": "meeting",
            "erinnern": "reminder",
            "dokumentieren": "document",
            "nachfassen": "followup",
            "angebot senden": "offer",
            "senden": "email",
            "erstellen": "general",
        },
    }

    # Titles and honorifics for person detection
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
        ],
        "de": ["herr", "frau", "dr", "dr.", "prof", "prof."],
    }

    # Insurance-specific topics
    INSURANCE_TOPICS = {
        "en": [
            "insurance",
            "policy",
            "claim",
            "coverage",
            "premium",
            "renewal",
            "quote",
            "accident",
            "damage",
            "liability",
            "car insurance",
            "home insurance",
            "health insurance",
            "life insurance",
            "disability",
            "occupational disability",
        ],
        "de": [
            "versicherung",
            "police",
            "schaden",
            "deckung",
            "prämie",
            "verlängerung",
            "angebot",
            "unfall",
            "schaden",
            "haftpflicht",
            "autoversicherung",
            "hausratsversicherung",
            "krankenversicherung",
            "lebensversicherung",
            "berufsunfähigkeit",
        ],
    }

    # Words indicating topic follows
    TOPIC_MARKERS = {
        "en": [
            "about",
            "regarding",
            "concerning",
            "on the subject of",
            "on",
            "for",
            "related to",
            "topic",
        ],
        "de": [
            "über",
            "betreffend",
            "bezüglich",
            "zum thema",
            "zu",
            "für",
            "im zusammenhang mit",
            "thema",
        ],
    }

    # Words indicating deadline follows
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
            "diese",
            "morgen",
            "heute",
        ],
    }

    # Time frame indicators
    TIME_FRAMES = {
        "en": {
            "today": "today",
            "tomorrow": "tomorrow",
            "next week": "next week",
            "next month": "next month",
            "in a week": "in a week",
            "in a month": "in a month",
            "in 6 months": "in 6 months",
            "in 3 months": "in 3 months",
        },
        "de": {
            "heute": "today",
            "morgen": "tomorrow",
            "nächste woche": "next week",
            "nächsten monat": "next month",
            "in einer woche": "in a week",
            "in einem monat": "in a month",
            "in 6 monaten": "in 6 months",
            "in 3 monaten": "in 3 months",
        },
    }

    def __init__(self, text: str):
        """
        Initialize task extractor with input text.

        Args:
            text: Input text to extract task from
        """
        self.text = text
        self.language = LanguageDetector.detect_language(text)
        self.cleaned_text = self._clean_text(text)
        self.doc = NLPProcessor.process_text(self.cleaned_text, self.language)

    def _clean_text(self, text: str) -> str:
        """
        Clean text by removing introductory phrases.

        Args:
            text: Original text

        Returns:
            Cleaned text
        """
        text_lower = text.lower()

        # Try to remove introductory phrases
        for phrase in self.INTRODUCTORY_PHRASES[self.language]:
            if text_lower.startswith(phrase):
                return text[len(phrase) :].strip()

        # Check for task creation commands
        task_creation_patterns = {
            "en": [
                r"(?:please\s+)?create\s+(?:a\s+)?(?:task|reminder)\s*:?\s*(.+)",
                r"(?:please\s+)?set\s+(?:up|a)\s+(?:task|reminder)\s*:?\s*(.+)",
            ],
            "de": [
                r"(?:bitte\s+)?erstelle\s+(?:eine\s+)?(?:aufgabe|erinnerung)\s*:?\s*(.+)",
                r"(?:bitte\s+)?richte\s+(?:eine\s+)?(?:aufgabe|erinnerung)\s+ein\s*:?\s*(.+)",
            ],
        }

        for pattern in task_creation_patterns[self.language]:
            match = re.match(pattern, text_lower)
            if match:
                return match.group(1).strip()

        return text

    def extract_task(self) -> TaskComponents:
        """
        Extract all task components from the text.

        Returns:
            TaskComponents object containing extracted data
        """
        task = TaskComponents(language=self.language)
        task.action = self._extract_action()
        task.task_type = self._determine_task_type(task.action)
        task.person = self._extract_person()
        task.topic = self._extract_topic()
        task.deadline = self._extract_deadline()
        task.action = self._standardize_action(task.action, task.task_type)

        return task

    def _extract_action(self) -> str:
        text_lower = self.cleaned_text.lower()

        for action, variants in self.INSURANCE_ACTIONS[self.language].items():
            for variant in variants:
                if variant in text_lower:
                    return action

        action_patterns = {
            "en": [
                r"(?:please\s+)?call(?:\s+back)?\s+",
                r"(?:please\s+)?send\s+",
                r"(?:please\s+)?email\s+",
                r"(?:please\s+)?remind\s+(?:me\s+)?(?:about|to)\s+",
                r"(?:please\s+)?document\s+(?:that)?\s+",
                r"(?:please\s+)?create\s+(?:a\s+)?follow-?up\s+",
                r"(?:please\s+)?schedule\s+(?:a\s+)?",
            ],
            "de": [
                r"(?:bitte\s+)?(?:rufe?|rufen sie)\s+",
                r"(?:bitte\s+)?sende\s+",
                r"(?:bitte\s+)?schicke\s+",
                r"(?:bitte\s+)?erinnere\s+(?:mich\s+)?(?:an|zu)\s+",
                r"(?:bitte\s+)?dokumentiere\s+(?:dass)?\s+",
                r"(?:bitte\s+)?erstelle\s+(?:einen\s+)?folgetermin\s+",
                r"(?:bitte\s+)?plane\s+(?:einen\s+)?",
            ],
        }

        for pattern in action_patterns[self.language]:
            match = re.search(pattern, text_lower)
            if match:
                action_word = re.sub(
                    r"(?:please\s+|\?|\s+)", "", match.group(0)
                ).strip()

                if self.language == "en":
                    if "call" in action_word or "phone" in action_word:
                        return "call"
                    elif "send" in action_word or "email" in action_word:
                        return "send"
                    elif "remind" in action_word:
                        return "remind"
                    elif "document" in action_word:
                        return "document"
                    elif "follow" in action_word:
                        return "followup"
                    elif "schedule" in action_word:
                        return "meet"
                else:
                    if "ruf" in action_word:
                        return "anrufen"
                    elif "send" in action_word or "schick" in action_word:
                        return "senden"
                    elif "erinner" in action_word:
                        return "erinnern"
                    elif "dokumentier" in action_word:
                        return "dokumentieren"
                    elif "folge" in action_word:
                        return "nachfassen"
                    elif "plan" in action_word:
                        return "treffen"

        root_verb = None
        for token in self.doc:
            if token.pos_ == "VERB" and token.dep_ in ["ROOT", "root"]:
                root_verb = token.lemma_.lower()
                break

        if not root_verb:
            for token in self.doc:
                if token.pos_ == "VERB":
                    root_verb = token.lemma_.lower()
                    break

        if not root_verb:
            return "Task" if self.language == "en" else "Aufgabe"

        for action, variants in self.INSURANCE_ACTIONS[self.language].items():
            for variant in variants:
                if variant in root_verb or root_verb in variant:
                    return action

        return root_verb

    def _determine_task_type(self, action: str) -> str:
        task_type_mapping = self.TASK_TYPE_MAPPING[self.language]

        if action in task_type_mapping:
            return task_type_mapping[action]

        for key, task_type in task_type_mapping.items():
            if key in action or action in key:
                return task_type

        return "general"

    def _standardize_action(self, action: str, task_type: str) -> str:
        standard_actions = {
            "en": {
                "call": "Call",
                "email": "Email",
                "meeting": "Schedule meeting with",
                "reminder": "Reminder for",
                "document": "Document",
                "followup": "Follow up with",
                "offer": "Send offer to",
                "general": "Task",
            },
            "de": {
                "call": "Anrufen",
                "email": "E-Mail an",
                "meeting": "Termin mit",
                "reminder": "Erinnerung für",
                "document": "Dokumentieren",
                "followup": "Nachfassen bei",
                "offer": "Angebot senden an",
                "general": "Aufgabe",
            },
        }

        return standard_actions[self.language].get(task_type, action.capitalize())

    def _extract_person(self) -> str:
        text = self.cleaned_text
        text_lower = text.lower()
        titles = self.TITLES[self.language]

        for title in titles:
            title_pattern = (
                r"\b" + re.escape(title) + r"\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
            )
            match = re.search(title_pattern, text)
            if match:
                return f"{title.capitalize()}. {match.group(1)}"

        for ent in self.doc.ents:
            if ent.label_ in ["PERSON", "PER", "ORG"]:

                entity_position = ent.start_char
                if entity_position < 10 and len(self.doc) > ent.end:
                    next_token = self.doc[ent.end]
                    if next_token.pos_ == "VERB":
                        continue
                return ent.text

        team_patterns = {
            "en": r"\b(?:the|with|to|for)\s+(\w+\s*\w*)\b",
            "de": r"\b(?:das|dem|die|der|mit|für|an)\s+(\w+\s*\w*)\b",
        }

        skip_words = {
            "en": {
                "me",
                "you",
                "topic",
                "subject",
                "task",
                "reminder",
                "note",
                "problem",
                "issue",
                "subject",
                "meeting",
            },
            "de": {
                "mich",
                "dir",
                "thema",
                "aufgabe",
                "erinnerung",
                "notiz",
                "problem",
                "betreff",
                "treffen",
            },
        }

        matches = re.finditer(team_patterns[self.language], text_lower)
        for match in matches:
            potential_person = match.group(1).strip()
            if potential_person not in skip_words[self.language]:
                if self.language == "en":
                    return "the " + potential_person
                else:
                    article = text_lower[match.start() : match.start() + 3].strip()
                    if article in ["der", "die", "das", "dem"]:
                        return article + " " + potential_person
                    else:
                        return "der/die " + potential_person

        return ""

    def _extract_topic(self) -> str:
        text = self.cleaned_text
        text_lower = text.lower()

        topic_markers = self.TOPIC_MARKERS[self.language]
        for marker in topic_markers:
            pattern = r"\b" + re.escape(marker) + r"\b\s*([^,.;:!?]*)"
            match = re.search(pattern, text_lower)
            if match:
                topic_text = match.group(1).strip()

                deadline_markers = self.DEADLINE_MARKERS[self.language]
                for d_marker in deadline_markers:
                    d_pattern = r"\b" + re.escape(d_marker) + r"\b.*$"
                    topic_text = re.sub(d_pattern, "", topic_text).strip()

                topic_text = re.sub(
                    r"\b(and|or|but|und|oder|aber|mit|for|für)\s*$", "", topic_text
                ).strip()
                return topic_text

        insurance_topics = self.INSURANCE_TOPICS[self.language]
        for topic in insurance_topics:
            if topic in text_lower:

                topic_idx = text_lower.index(topic)
                start_idx = max(0, topic_idx - 20)
                end_idx = min(len(text_lower), topic_idx + len(topic) + 20)
                context = text_lower[start_idx:end_idx]

                context = re.sub(r"^[^a-z]*", "", context)
                context = re.sub(r"[^a-z]*$", "", context)

                for d_marker in self.DEADLINE_MARKERS[self.language]:
                    d_pattern = r"\b" + re.escape(d_marker) + r"\b.*$"
                    context = re.sub(d_pattern, "", context).strip()

                if context:
                    return context
                return topic

        action = self._extract_action()
        person = self._extract_person()

        action_person_pattern = ""
        if action:
            action_variants = []
            for variants in self.INSURANCE_ACTIONS[self.language].values():
                action_variants.extend(variants)

            for variant in action_variants:
                if variant in text_lower:
                    action_person_pattern += r"\b" + re.escape(variant) + r"\b"
                    break

        if person:
            clean_person = re.escape(person.lower())
            if action_person_pattern:
                action_person_pattern += r".*?" + clean_person
            else:
                action_person_pattern = r"\b" + clean_person

        if action_person_pattern:
            match = re.search(action_person_pattern, text_lower)
            if match:
                remaining_text = text_lower[match.end() :].strip()
                for d_marker in self.DEADLINE_MARKERS[self.language]:
                    d_pattern = r"\b" + re.escape(d_marker) + r"\b.*$"
                    remaining_text = re.sub(d_pattern, "", remaining_text).strip()

                remaining_text = re.sub(
                    r"^(about|regarding|concerning|über|betreffend|bezüglich|zu|zum)\s+",
                    "",
                    remaining_text,
                )

                if len(remaining_text.split()) <= 8 and len(remaining_text.split()) > 0:
                    return remaining_text

        return ""

    def _extract_deadline(self) -> str:
        text = self.cleaned_text
        text_lower = text.lower()

        date_entity = None
        for ent in self.doc.ents:
            if ent.label_ == "DATE" or ent.label_ == "TIME":
                date_entity = ent.text
                break

        if date_entity:
            return date_entity

        time_frames = self.TIME_FRAMES[self.language]
        for time_frame, standardized in time_frames.items():
            if time_frame in text_lower:
                return standardized

        deadline_markers = self.DEADLINE_MARKERS[self.language]

        for marker in deadline_markers:
            pattern = r"\b" + re.escape(marker) + r"\b\s*([^,.;:!?]*)"
            match = re.search(pattern, text_lower)
            if match:
                deadline_text = match.group(1).strip()

                deadline_doc = NLPProcessor.process_text(deadline_text, self.language)
                for ent in deadline_doc.ents:
                    if ent.label_ == "DATE" or ent.label_ == "TIME":
                        return ent.text

                if len(deadline_text.split()) <= 5:
                    return deadline_text

        time_period_patterns = {
            "en": r"\bin\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)\b",
            "de": r"\bin\s+(\d+)\s+(tag|tagen|woche|wochen|monat|monaten|jahr|jahren)\b",
        }

        match = re.search(time_period_patterns[self.language], text_lower)
        if match:
            number = match.group(1)
            unit = match.group(2)
            return f"in {number} {unit}"

        return ""


class InsuranceTaskHandler:

    INSURANCE_TASK_TYPES = {
        "callback": "call",
        "consultation": "meeting",
        "offer": "offer",
        "follow-up": "followup",
        "claim": "document",
    }

    INSURANCE_TERMS = {
        "en": {
            "car insurance": "auto policy",
            "home insurance": "homeowners policy",
            "home contents": "contents insurance",
            "occupational disability": "disability insurance",
            "consultation": "insurance consultation",
            "claim": "insurance claim",
        },
        "de": {
            "autoversicherung": "KFZ Police",
            "hausratsversicherung": "Hausrat Versicherung",
            "berufsunfähigkeit": "BU Versicherung",
            "beratung": "Versicherungsberatung",
            "schaden": "Versicherungsfall",
        },
    }

    @classmethod
    def enhance_task(cls, task: TaskComponents) -> TaskComponents:
        if task.topic:
            terms = cls.INSURANCE_TERMS[task.language]
            for term, standard in terms.items():
                if term.lower() in task.topic.lower():
                    task.topic = standard
                    break

        text_lower = task.topic.lower()
        for key_term, task_type in cls.INSURANCE_TASK_TYPES.items():
            if key_term in text_lower:
                task.task_type = task_type
                break

        if "claim" in text_lower and task.action.lower() in [
            "document",
            "dokumentieren",
        ]:
            task.task_type = "document"
            if task.language == "en":
                task.action = "Create claim file"
            else:
                task.action = "Schadenakte anlegen"

        return task


def extract_task_from_text(text: str) -> Dict:
    try:
        extractor = TaskExtractor(text)
        task_components = extractor.extract_task()

        # Apply insurance-specific enhancements
        enhanced_task = InsuranceTaskHandler.enhance_task(task_components)

        return enhanced_task.to_dict()
    except Exception as e:
        logging.error(f"Error extracting task: {str(e)}")
        return {
            "action": "",
            "person": "",
            "topic": "",
            "deadline": "",
            "language": "en",
            "task_type": "general",
            "error": str(e),
        }


def generate_feedback_message(task: TaskComponents) -> str:
    if task.language == "en":
        message = f"Task created: {task.action}"
        if task.person:
            message += f" with {task.person}"
        if task.topic:
            message += f" about {task.topic}"
        if task.deadline:
            message += f" - Due {task.deadline}"
    else:
        message = f"Aufgabe erstellt: {task.action}"
        if task.person:
            message += f" mit {task.person}"
        if task.topic:
            message += f" über {task.topic}"
        if task.deadline:
            message += f" - Fällig {task.deadline}"

    return message


def format_task_for_database(
    task: TaskComponents, voice_input: str, user: str = "anonymous"
) -> Dict:
    return {
        "user": user,
        "voice_input": voice_input,
        "task_type": task.task_type,
        "action": task.action,
        "person": task.person,
        "topic": task.topic,
        "deadline": task.deadline,
        "language": task.language,
    }
