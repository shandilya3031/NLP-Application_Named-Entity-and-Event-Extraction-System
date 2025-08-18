import spacy
import re
from datetime import datetime
from config import NEWS_ENTITY_TYPES, EVENT_PATTERNS
from dateutil import parser as date_parser

class NamedEntityExtractor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model not found. Using basic extraction.")
            self.nlp = None
    
    def extract_entities(self, text, selected_types=None):
        """Extract named entities from text"""
        entities = []
        
        if self.nlp:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                entity_type = self._map_spacy_label(ent.label_)
                
                if selected_types is None or entity_type in selected_types:
                    entities.append({
                        'text': ent.text,
                        'type': entity_type,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'confidence': 0.8,  # Default confidence
                        'context': self._get_context(text, ent.start_char, ent.end_char)
                    })
        
        # Add custom pattern-based extraction
        entities.extend(self._extract_custom_patterns(text, selected_types))
        
        return self._remove_duplicates(entities)
    
    def _map_spacy_label(self, spacy_label):
        """Map spaCy labels to our custom entity types"""
        mapping = {
            'PERSON': 'PERSON',
            'ORG': 'ORGANIZATION',
            'GPE': 'LOCATION',  # Geopolitical entity
            'LOC': 'LOCATION',
            'DATE': 'DATE',
            'TIME': 'DATE',
            'MONEY': 'MONEY',
            'EVENT': 'EVENT'
        }
        return mapping.get(spacy_label, spacy_label)
    
    def _extract_custom_patterns(self, text, selected_types):
        """Extract entities using custom regex patterns"""
        entities = []
        
        # Email patterns
        if selected_types is None or 'CONTACT' in selected_types:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            for match in re.finditer(email_pattern, text):
                entities.append({
                    'text': match.group(),
                    'type': 'CONTACT',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9,
                    'context': self._get_context(text, match.start(), match.end())
                })
        
        # Phone patterns
        if selected_types is None or 'CONTACT' in selected_types:
            phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
            for match in re.finditer(phone_pattern, text):
                entities.append({
                    'text': match.group(),
                    'type': 'CONTACT',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.85,
                    'context': self._get_context(text, match.start(), match.end())
                })
        
        return entities
    
    def _get_context(self, text, start, end, context_length=50):
        """Get surrounding context for an entity"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        return text[context_start:context_end].strip()
    
    def _remove_duplicates(self, entities):
        """Remove duplicate entities based on text and position"""
        unique_entities = []
        seen = set()
        
        for entity in entities:
            key = (entity['text'].lower(), entity['start'], entity['end'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return sorted(unique_entities, key=lambda x: x['start'])

class EventExtractor:
    def __init__(self):
        self.patterns = EVENT_PATTERNS
    
    def extract_events(self, text):
        """Extract events from text using predefined patterns"""
        events = []
        
        for pattern_config in self.patterns:
            pattern = pattern_config['pattern']
            event_type = pattern_config['type']
            
            for match in re.finditer(pattern, text):
                event = {
                    'text': match.group(),
                    'type': event_type,
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.7,
                    'context': self._get_context(text, match.start(), match.end()),
                    'attributes': self._extract_attributes(match, pattern_config)
                }
                events.append(event)
        
        # Extract temporal events
        events.extend(self._extract_temporal_events(text))
        
        return sorted(events, key=lambda x: x['start'])
   
    # In extraction_rules.py
    def _extract_attributes(self, match, pattern_config):
        attributes = {}
        if 'attributes' in pattern_config:
            for attr_name, group_index in pattern_config['attributes'].items():
                if match.lastindex >= group_index:
                    attributes[attr_name] = match.group(group_index)
                else:
                    attributes[attr_name] = None
        return attributes

    def _extract_temporal_events(self, text):
        """Extract events with temporal markers"""
        temporal_events = []
        
        # Look for temporal phrases followed by events
        temporal_pattern = r'(?i)(yesterday|today|tomorrow|last\s+\w+|next\s+\w+|on\s+\w+)\s+([^.]+)'
        
        for match in re.finditer(temporal_pattern, text):
            temporal_events.append({
                'text': match.group(),
                'type': 'TEMPORAL_EVENT',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.6,
                'context': self._get_context(text, match.start(), match.end()),
                'attributes': {
                    'temporal_marker': match.group(1),
                    'event_description': match.group(2)
                }
            })
        
        return temporal_events
    
    def _get_context(self, text, start, end, context_length=50):
        """Get surrounding context for an event"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        return text[context_start:context_end].strip()

class TextProcessor:
    def __init__(self):
        self.entity_extractor = NamedEntityExtractor()
        self.event_extractor = EventExtractor()
    
    def process_text(self, text, selected_entity_types=None, extract_events=True):
        """Process text to extract both entities and events"""
        results = {
            'entities': [],
            'events': [],
            'statistics': {},
            'highlighted_text': text
        }
        
        # Extract entities
        results['entities'] = self.entity_extractor.extract_entities(text, selected_entity_types)
        
        # Extract events if requested
        if extract_events:
            results['events'] = self.event_extractor.extract_events(text)
        
        # Generate statistics
        results['statistics'] = self._generate_statistics(results['entities'], results['events'])
        
        # Generate highlighted text
        results['highlighted_text'] = self._highlight_text(text, results['entities'], results['events'])
        
        return results
    
    def _generate_statistics(self, entities, events):
        """Generate statistics about extracted entities and events"""
        entity_counts = {}
        for entity in entities:
            entity_type = entity['type']
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        event_counts = {}
        for event in events:
            event_type = event['type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            'total_entities': len(entities),
            'total_events': len(events),
            'entity_counts': entity_counts,
            'event_counts': event_counts
        }
    
    def _highlight_text(self, text, entities, events):
        """Create highlighted version of text with entities and events marked"""
        # Combine entities and events for highlighting
        all_items = entities + events
        all_items.sort(key=lambda x: x['start'])
        
        highlighted = ""
        last_end = 0
        
        for item in all_items:
            # Add text before the current item
            highlighted += text[last_end:item['start']]
            
            # Add highlighted item
            color = NEWS_ENTITY_TYPES.get(item['type'], {}).get('color', '#CCCCCC')
            highlighted += f'<span class="highlight" data-type="{item["type"]}" data-confidence="{item.get("confidence", 0)}" style="background-color: {color}; padding: 2px 4px; border-radius: 3px; margin: 1px;" title="{item["type"]} (Confidence: {item.get("confidence", 0):.2f})">{item["text"]}</span>'
            
            last_end = item['end']
        
        # Add remaining text
        highlighted += text[last_end:]
        
        return highlighted