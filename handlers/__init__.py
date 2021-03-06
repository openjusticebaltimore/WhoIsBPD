import os
import sys
import copy
import logging
from datetime import datetime
from fuzzywuzzy import process, fuzz
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'BPDWatch'))
from OpenOversight.app.models import Officer

loglevel = os.environ.get('LOGLEVEL', 'INFO').upper()
numeric_level = getattr(logging, loglevel, None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)
logger = logging.getLogger(__file__)
logger.setLevel(numeric_level)

equivalent_suffixes = [
    ('sr'),
    ('jr', '2nd', 'ii'),
    ('3rd', 'iii'),
    ('4th', 'iv')
]


class MatchedOfficer(Exception):
    pass


class OfficerMatcher:
    def __init__(self, update_seconds=3600):
        self.update_seconds = update_seconds
        self.load_officers()

    @classmethod
    def fetch_officers(cls):
        officer_names = []
        for officer in Officer.query.filter_by(department_id=1).all():
            officer_names.append({
                'officer': officer,
                'names': cls.permutate_names(officer)
            })
        return officer_names
    
    @classmethod
    def permutate_names(cls, officer):
        logger.debug(f'Permutating name for {officer.full_name()}')
        names = [f'{officer.first_name} {officer.last_name}']
        if officer.middle_initial:
            if len(officer.middle_initial) > 1:
                names.append(f'{officer.first_name} {officer.middle_initial[0]} {officer.last_name}')
            names.append(f'{officer.first_name} {officer.middle_initial} {officer.last_name}')
        if officer.suffix:
            for suffix_set in equivalent_suffixes:
                if officer.suffix.lower() in suffix_set:
                    names_copy = copy.deepcopy(names)
                    for suffix in suffix_set:
                        for name in names_copy:
                            names.append(f'{name} {suffix}')
        return names

    def load_officers(self):
        logger.info('Loading officers')
        self.officer_names = self.fetch_officers()
        self.last_updated = datetime.now()

    def match_officers(self, texts):
        logger.debug(f'Matching against {", ".join(texts)}')
        if (self.last_updated - datetime.now()).total_seconds() > self.update_seconds:
            self.load_officers()
        matched_officers = set()
        texts = list(map(str.lower, texts))
        for officer_set in self.officer_names:
            try:
                for name in officer_set['names']:
                    for text in texts:
                        if name.lower() in text:
                            logger.info(f"Matched officer {officer_set['officer'].full_name()}")
                            matched_officers.add(officer_set['officer'])
                            raise MatchedOfficer
            except MatchedOfficer:
                pass
        return matched_officers

    def match_officers_fuzzy(self, texts):
        '''Only matches texts against full name of officer, for performance reasons'''

        logger.debug(f'Matching against {", ".join(texts)}')
        if (self.last_updated - datetime.now()).total_seconds() > self.update_seconds:
            self.load_officers()
        matched_officers = set()
        for officer_set in self.officer_names:
            officer_full_name = officer_set['officer'].full_name()
            _, match_score = process.extractOne(
                officer_full_name,
                texts,
                scorer=fuzz.token_set_ratio
            )
            if match_score >= 90:
                logger.info(f"Matched officer {officer_full_name}")
                matched_officers.add(officer_set['officer'])
        return matched_officers