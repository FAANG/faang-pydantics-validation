from typing import List, Dict, Any, Type
from pydantic import ValidationError
from rulesets_pydantics.submission_ruleset import FAANGSubmission
from rulesets_pydantics.person_ruleset import FAANGPerson
from rulesets_pydantics.organization_ruleset import FAANGOrganization


class SubmissionValidator:

    def validate_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records or len(records) == 0:
            return {
                'valid': [],
                'invalid': [],
                'error': "Error: data for 'submission' sheet was not provided"
            }

        results = {
            'valid': [],
            'invalid': [],
            'summary': {
                'total': len(records),
                'valid': 0,
                'invalid': 0
            }
        }

        for i, record in enumerate(records):
            try:
                model = FAANGSubmission(**record)
                results['valid'].append({
                    'index': i,
                    'model': model,
                    'data': record
                })
                results['summary']['valid'] += 1
            except ValidationError as e:
                results['invalid'].append({
                    'index': i,
                    'data': record,
                    'errors': [err['msg'] for err in e.errors()]
                })
                results['summary']['invalid'] += 1

        return results


class PersonValidator:
    def validate_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records or len(records) == 0:
            return {
                'valid': [],
                'invalid': [],
                'error': "Error: data for 'person' sheet was not provided"
            }

        results = {
            'valid': [],
            'invalid': [],
            'summary': {
                'total': len(records),
                'valid': 0,
                'invalid': 0
            }
        }

        for i, record in enumerate(records):
            try:
                model = FAANGPerson(**record)
                results['valid'].append({
                    'index': i,
                    'model': model,
                    'data': record
                })
                results['summary']['valid'] += 1
            except ValidationError as e:
                results['invalid'].append({
                    'index': i,
                    'data': record,
                    'errors': [err['msg'] for err in e.errors()]
                })
                results['summary']['invalid'] += 1

        return results


class OrganizationValidator:
    def validate_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records or len(records) == 0:
            return {
                'valid': [],
                'invalid': [],
                'error': "Error: data for 'organization' sheet was not provided"
            }

        results = {
            'valid': [],
            'invalid': [],
            'summary': {
                'total': len(records),
                'valid': 0,
                'invalid': 0
            }
        }

        for i, record in enumerate(records):
            try:
                model = FAANGOrganization(**record)
                results['valid'].append({
                    'index': i,
                    'model': model,
                    'data': record
                })
                results['summary']['valid'] += 1
            except ValidationError as e:
                results['invalid'].append({
                    'index': i,
                    'data': record,
                    'errors': [err['msg'] for err in e.errors()]
                })
                results['summary']['invalid'] += 1

        return results