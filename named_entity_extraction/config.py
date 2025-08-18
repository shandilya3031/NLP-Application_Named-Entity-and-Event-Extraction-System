# Configuration file for extraction rules and entity types

NEWS_ENTITY_TYPES = {
    'PERSON': {
        'color': '#FF6B6B',
        'description': 'People mentioned in news'
    },
    'ORGANIZATION': {
        'color': '#4ECDC4',
        'description': 'Companies, institutions, government bodies'
    },
    'LOCATION': {
        'color': '#45B7D1',
        'description': 'Countries, cities, specific places'
    },
    'DATE': {
        'color': '#96CEB4',
        'description': 'Dates and time references'
    },
    'MONEY': {
        'color': '#FFEAA7',
        'description': 'Monetary values and currencies'
    },
    'EVENT': {
        'color': '#DDA0DD',
        'description': 'Significant events or incidents'
    }
}

# Event extraction patterns for news domain
EVENT_PATTERNS = [
    # Announcement patterns: Captures who announced what.
    {
        'pattern': r'([A-Z][a-zA-Z\s,]+?)\s+(announced|declared|revealed|unveiled|disclosed)\s+(?:that\s)?(.+?)(?:\.|$)',
        'type': 'ANNOUNCEMENT',
        'attributes': {
            'announcer': 1,
            'action': 2,
            'content': 3
        }
    },
    # Meeting/Conference patterns: Captures the event type and participants.
    {
        'pattern': r'(?i)(a\s+meeting|conference|summit|gathering|assembly)\s+(?:between|among|with)\s+((?:[A-Z][\w\s,]+(?:(?:and|,)\s)?)+)',
        'type': 'MEETING',
        'attributes': {
            'event_type': 1,
            'participants': 2
        }
    },
    # Legal/Court patterns: Captures who took action against whom.
    {
        'pattern': r'([A-Z][\w\s,]+?)\s+(sued|filed\s+a\s+lawsuit\s+against|charged|convicted|sentenced)\s+([A-Z][\w\s,]+)',
        'type': 'LEGAL_ACTION',
        'attributes': {
            'plaintiff_or_authority': 1,
            'action': 2,
            'defendant': 3
        }
    },
    # Economic patterns: Captures the metric, direction, and value of a change.
    {
        'pattern': r'(shares|revenue|profits|sales)\s+(rose|fell|increased|decreased|grew)\s+(?:by\s+)?([\d\.\s%]+)',
        'type': 'ECONOMIC_CHANGE',
        'attributes': {
            'metric': 1,
            'direction': 2,
            'value': 3
        }
    },
    # Accident/Incident patterns: Captures the type of incident and its location.
    {
        'pattern': r'(?i)\b(an?\s+accident|a\s+crash|a\s+collision|an\s+explosion|a\s+fire)\s+(?:at|in|near)\s+((?:the\s+)?[A-Z][\w\s,]+)',
        'type': 'INCIDENT',
        'attributes': {
            'incident_type': 1,
            'location': 2
        }
    }
]

# Upload settings
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

# Cache settings
CACHE_TIMEOUT = 300  # 5 minutes
