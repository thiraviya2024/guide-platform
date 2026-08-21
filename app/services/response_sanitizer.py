"""Remove model-only reasoning before text reaches a patient or the UI."""

import logging
import re


logger = logging.getLogger(__name__)
SAFE_FALLBACK = (
    "I'm sorry, but I couldn't generate a clear answer from the available "
    "information. Please try asking your question again."
)

_REASONING_BLOCK = re.compile(
    r"<(?:think|thinking|analysis)\b[^>]*>.*?</(?:think|thinking|analysis)\s*>",
    re.IGNORECASE | re.DOTALL,
)
_REASONING_TAG = re.compile(r"</?(?:think|thinking|analysis)\b[^>]*>", re.IGNORECASE)
_INTERNAL_MARKER = re.compile(
    r"(?:here(?:'s| is)\s+(?:my\s+)?thinking\s+process|thinking\s+process|"
    r"let['’]?s\s+think\s+step\s+by\s+step|"
    r"analyze\s+user\s+input|deconstruct\s+(?:lab\s+)?results?|"
    r"extract\s+key\s+information|"
    r"draft\s+response|mental\s+refinement|refinement\s*\(\s*patient[- ]friendly\s*\)|"
    r"internal\s+reasoning|"
    r"final\s+(?:check|polish|output\s+generation)|self[- ]correction|"
    r"verification(?:\s+(?:during\s+thought|of\s+the\s+answer))?|"
    r"proceeds?\s+to\s+(?:generate|output)|output\s+generation|"
    r"(?:all\s+)?constraints\s+met|^\s*i\s+will\b|internal\s+(?:prompt|constraint|rule|check)|"
    r"prompt\s+(?:instructions?|constraints?)|constraint\s+checks?|"
    r"required\s+output\s+structure|mandatory|constraints?|"
    r"rule[_ ]name|no\s+rule\s+found|system\s+instruction|chain[- ]of[- ]thought|"
    r"analysis\s+process|rule[- ]engine|database\s+rule|provider\s+(?:information|details|name)|"
    r"debug(?:\s+information)?|\b(?:groq|gemini)\b|"
    r"only\s+final\s+patient[- ]facing\s+answer|^\s*check\s*$)",
    re.IGNORECASE,
)
_FINAL_SECTION = re.compile(
    r"^\s*(?:\[\s*)?(?:\d+[.)]\s*)?(?:\*{0,2})\s*(?:final\s+(?:answer|response|"
    r"output\s+generation)|"
    r"patient[- ]facing\s+answer|answer\s+to\s+the\s+patient|"
    r"output\s+generation)\b\s*(?:\*{0,2})\s*:?\s*(?:\]\s*)?",
    re.IGNORECASE,
)
_ANSWER_SECTION = re.compile(
    r"^\s*(?:\*{0,2})\s*(?:summary|answer)\b\s*(?:\*{0,2})\s*:?\s*",
    re.IGNORECASE,
)
_DRAFT_SECTION = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\d+[.)]\s*)?(?:\*{0,2})\s*(?:draft(?:\s+(?:the\s+)?response|\s*\d+)|"
    r"formulate\s+the\s+response|revised\s+draft)"
    r"(?:\s*\([^)]*\))?\s*(?:\*{0,2})\s*:?\s*",
    re.IGNORECASE,
)
_CHECK_SECTION = re.compile(
    r"^\s*(?:\d+[.)]\s*)?(?:\*{0,2})\s*(?:final\s+(?:check|polish)|checks?|"
    r"self[- ]correction|(?:final\s+)?output\s+generation)\b",
    re.IGNORECASE,
)
_INTERNAL_LINE = re.compile(
    r"^\s*[-*#\d.) ]*(?:constraints?|required\s+output\s+structure|mandatory|"
    r"verification|internal\s+reasoning|refinement\s*\(\s*patient[- ]friendly\s*\)|"
    r"only\s+final\s+patient[- ]facing\s+answer)\s*:\s*",
    re.IGNORECASE,
)


def _strip_internal_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if not _INTERNAL_LINE.match(line)]


def _draft_answer(lines: list[str]) -> list[str]:
    """Extract the model's draft text when output generation is internal-only."""
    draft_indices = [
        index for index, line in enumerate(lines) if _DRAFT_SECTION.match(line)
    ]
    draft_start = draft_indices[-1] if draft_indices else None
    if draft_start is None:
        return []

    draft_marker = _DRAFT_SECTION.match(lines[draft_start])
    answer_lines = [lines[draft_start][draft_marker.end():], *lines[draft_start + 1:]]
    for index, line in enumerate(answer_lines):
        if _CHECK_SECTION.match(line):
            answer_lines = answer_lines[:index]
            break
    return answer_lines


def _tail_after_last_internal_marker(lines: list[str]) -> list[str]:
    """Recover an unlabelled answer after an internal reasoning preamble."""
    marker_indices = [
        index for index, line in enumerate(lines) if _INTERNAL_MARKER.search(line)
    ]
    if not marker_indices:
        return []

    last_marker = marker_indices[-1]
    marker_text = lines[last_marker]
    marker_match = _INTERNAL_MARKER.search(marker_text)
    whole_line_marker = marker_match and re.match(
        r"^\s*i\s+will\b|^\s*(?:all\s+)?constraints\s+met\b",
        marker_text,
        re.IGNORECASE,
    )
    tail = "" if whole_line_marker else (
        marker_text[marker_match.end():].lstrip(" \t:-*")
        if marker_match else ""
    )
    return [tail, *lines[last_marker + 1:]]


def sanitize_model_output(output: str) -> str:
    """Return only patient-facing text, or a safe fallback if none is identifiable."""
    if not output:
        return SAFE_FALLBACK

    cleaned = _REASONING_TAG.sub("", _REASONING_BLOCK.sub("", str(output))).strip()
    lines = cleaned.splitlines()
    detected = any(_INTERNAL_MARKER.search(line) for line in lines)
    if not detected:
        if lines and _FINAL_SECTION.match(lines[0]):
            lines[0] = lines[0][_FINAL_SECTION.match(lines[0]).end():]
            cleaned = "\n".join(lines).strip()
        return cleaned

    logger.warning("Model reasoning detected; sanitizing provider output")
    answer_start = None
    for index, line in enumerate(lines):
        if _FINAL_SECTION.match(line) or _ANSWER_SECTION.match(line):
            answer_start = index
            break

    if answer_start is None:
        draft_lines = _draft_answer(lines)
        if draft_lines:
            answer_lines = draft_lines
        else:
            answer_lines = _tail_after_last_internal_marker(lines)
            if not answer_lines:
                logger.warning("Reasoning had no identifiable patient-answer boundary")
                return SAFE_FALLBACK
    else:
        answer_lines = lines[answer_start:]

    if answer_start is None and not answer_lines:
        logger.warning("Reasoning had no identifiable patient-answer boundary")
        return SAFE_FALLBACK

    if answer_start is not None:
        first_line = answer_lines[0]
        marker = _FINAL_SECTION.match(first_line) or _ANSWER_SECTION.match(first_line)
        if marker:
            answer_lines[0] = first_line[marker.end():]

    if not "\n".join(answer_lines).strip() or _INTERNAL_MARKER.search("\n".join(answer_lines)):
        draft_lines = _draft_answer(lines)
        if draft_lines:
            answer_lines = draft_lines

    for index, line in enumerate(answer_lines):
        if index and _CHECK_SECTION.match(line):
            answer_lines = answer_lines[:index]
            break

    answer = "\n".join(_strip_internal_lines(answer_lines)).strip()
    if len(re.sub(r"[^A-Za-z0-9]+", "", answer)) < 8 or _INTERNAL_MARKER.search(answer):
        logger.warning("Sanitized output contained no usable patient answer")
        return SAFE_FALLBACK
    return answer