"""Offline pattern-based redaction. Reports contain counts, never matched values."""
from collections import Counter
from dataclasses import replace
import re

VERSION = 1


def luhn(value):
    digits = [int(c) for c in value if c.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) < 2:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit = digit * 2
            digit = digit - 9 if digit > 9 else digit
        total += digit
    return total % 10 == 0


class Redactor:
    def __init__(self, literals=()):
        if not isinstance(literals, (list, tuple)) or any(not isinstance(v, str) or len(v) < 3 for v in literals):
            raise ValueError('Custom redactions must be strings of at least 3 characters')
        self.literals = sorted(set(literals), key=len, reverse=True)
        self.counts = Counter()
        self.rules = [
            ('PRIVATE_KEY', re.compile(r'-----BEGIN (?P<kind>(?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY)-----.*?(?:-----END (?P=kind)-----|\Z)', re.S)),
            ('API_KEY', re.compile(r'\b(?:sk-(?:proj-|ant-[A-Za-z0-9]+-)?[A-Za-z0-9_-]{16,}|(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{16,}|xox[baprs]-[A-Za-z0-9-]{12,}|AIza[\w-]{25,}|(?:AKIA|ASIA)[A-Z0-9]{16})\b')),
            ('JWT', re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b')),
            ('AUTHORIZATION', re.compile(r'(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9_+/=.-]{8,}')),
            ('URL_CREDENTIALS', re.compile(r'(?i)\b[a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@')),
            ('SECRET_VALUE', re.compile(r'''(?ix)
                (?P<prefix>["']?\b(?:[a-z0-9]+[_-])*(?:password|passwd|pwd|secret|secret[_-]?key|signing[_-]?key|encryption[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret|authorization|cookie|set-cookie)\b["']?\s*[:=]\s*)
                (?P<value>"[^"\n]+"|'[^'\n]+'|[^\s,;\}\]\n]+)
            ''')),
            ('EMAIL', re.compile(r'(?<![\w.+-])[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b')),
            ('SSN', re.compile(r'(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)')),
            ('PAYMENT_CARD', re.compile(r'(?<![\w])(?:\d[ -]?){12,18}\d(?![\w])')),
            ('PHONE', re.compile(r'(?<![\w])(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?!\d)')),
        ]

    def clean(self, text):
        if not isinstance(text, str):
            return text
        if self.literals:
            pattern = re.compile('|'.join(re.escape(v) for v in self.literals))
            def custom(match):
                self.counts['CUSTOM'] += 1
                return 'REDACTED-CUSTOM'
            text = ''.join(part if re.fullmatch(r'REDACTED-[A-Z_]+', part) else pattern.sub(custom, part)
                           for part in re.split(r'(REDACTED-[A-Z_]+)', text))
        for name, pattern in self.rules:
            def substitute(match):
                if name == 'SECRET_VALUE' and re.fullmatch(r'REDACTED-[A-Z_]+', match['value'].strip("\"'")):
                    return match.group()
                if name == 'PAYMENT_CARD' and not luhn(match.group()):
                    return match.group()
                self.counts[name] += 1
                if name == 'SECRET_VALUE':
                    value = match['value']
                    quote = value[0] if value[0] in ('"', "'") else ''
                    return match['prefix'] + quote + 'REDACTED-SECRET_VALUE' + quote
                if name == 'URL_CREDENTIALS':
                    return match.group().split('://')[0] + '://REDACTED-URL_CREDENTIALS@'
                return 'REDACTED-' + name
            text = pattern.sub(substitute, text)
        return text

    def chat(self, chat):
        fields = {name: self.clean(getattr(chat, name)) for name in ('id', 'title', 'project', 'origin', 'parent', 'workspace', 'project_root')}
        fields['title'] = fields['title'][:100]
        messages = [replace(m, text=self.clean(m.text), branch=self.clean(m.branch), model=self.clean(m.model)) for m in chat.messages]
        return replace(chat, messages=messages, **fields)
