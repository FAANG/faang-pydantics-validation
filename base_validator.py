from typing import List, Dict, Any, Tuple, Optional, Type
from pydantic import ValidationError, BaseModel
from abc import ABC, abstractmethod


class BaseValidator(ABC):
    def __init__(self):
        self.ontology_validator = None
        self.relationship_validator = None
        self._initialize_validators()

    @abstractmethod
    def _initialize_validators(self):
        pass

    @abstractmethod
    def get_model_class(self) -> Type[BaseModel]:
        pass

    @abstractmethod
    def get_sample_type_name(self) -> str:
        pass

    def get_recommended_fields(self, model_class) -> List[str]:
        recommended_fields = []

        for field_name, field_info in model_class.model_fields.items():
            if (field_info.json_schema_extra and
                isinstance(field_info.json_schema_extra, dict) and
                field_info.json_schema_extra.get("recommended", False)):
                recommended_fields.append(field_name)

        return recommended_fields

    def validate_record(
        self,
        data: Dict[str, Any],
    ) -> Tuple[Optional[Any], Dict[str, List[str]]]:
        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        model_class = self.get_model_class()

        # pydantic validation
        try:
            model_instance = model_class(**data)
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                error_msg = error['msg']

                if field_path not in errors_dict['field_errors']:
                    errors_dict['field_errors'][field_path] = []
                errors_dict['field_errors'][field_path].append(error_msg)
                errors_dict['errors'].append(f"{field_path}: {error_msg}")

            return None, errors_dict
        except Exception as e:
            errors_dict['errors'].append(str(e))
            return None, errors_dict

        # recommended fields
        recommended_fields = self.get_recommended_fields(model_class)
        for field in recommended_fields:
            if getattr(model_instance, field, None) is None:
                field_info = model_class.model_fields.get(field)
                field_display_name = field_info.alias if field_info and field_info.alias else field
                errors_dict['warnings'].append(
                    f"Field '{field_display_name}' is recommended but was not provided"
                )

        return model_instance, errors_dict

    def validate_records(
        self,
        samples: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        sample_type = self.get_sample_type_name()

        results = {
            f'valid_{sample_type}s': [],
            f'invalid_{sample_type}s': [],
            'summary': {
                'total': len(samples),
                'valid': 0,
                'invalid': 0,
                'warnings': 0,
                'relationship_errors': 0
            }
        }

        for i, sample_data in enumerate(samples):
            sample_name = sample_data.get('Sample Name', f'{sample_type}_{i}')

            model, errors = self.validate_record(sample_data)

            if model and not errors['errors']:
                results[f'valid_{sample_type}s'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'model': model,
                    'data': sample_data,
                    'warnings': errors['warnings'],
                    'relationship_errors': []
                })
                results['summary']['valid'] += 1
                if errors['warnings']:
                    results['summary']['warnings'] += 1
            else:
                results[f'invalid_{sample_type}s'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'data': sample_data,
                    'errors': errors
                })
                results['summary']['invalid'] += 1

        return results

    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        sample_type = self.get_sample_type_name()
        sample_type_title = sample_type.title()

        report = []
        report.append(f"FAANG {sample_type_title} Validation Report")
        report.append("=" * (25 + len(sample_type_title)))
        report.append(f"\nTotal {sample_type}s processed: {validation_results['summary']['total']}")
        report.append(f"Valid {sample_type}s: {validation_results['summary']['valid']}")
        report.append(f"Invalid {sample_type}s: {validation_results['summary']['invalid']}")
        report.append(f"{sample_type_title}s with warnings: {validation_results['summary']['warnings']}")

        # validation errors
        if validation_results[f'invalid_{sample_type}s']:
            report.append("\n\nValidation Errors:")
            report.append("-" * 20)
            for sample in validation_results[f'invalid_{sample_type}s']:
                report.append(f"\n{sample_type_title}: {sample['sample_name']} (index: {sample['index']})")

                # Field errors from Pydantic validation
                for field, field_errors in sample['errors'].get('field_errors', {}).items():
                    for error in field_errors:
                        report.append(f"  ERROR in {field}: {error}")

                # General errors
                for error in sample['errors'].get('errors', []):
                    if not any(error.startswith(field) for field in sample['errors'].get('field_errors', {})):
                        report.append(f"  ERROR: {error}")

                # FIXED: Show relationship errors for invalid samples
                if sample['errors'].get('relationship_errors'):
                    for error in sample['errors']['relationship_errors']:
                        report.append(f"  RELATIONSHIP ERROR: {error}")

                # FIXED: Show ontology warnings for invalid samples
                if sample['errors'].get('ontology_warnings'):
                    for warning in sample['errors']['ontology_warnings']:
                        report.append(f"  ONTOLOGY WARNING: {warning}")

        # warnings and relationship issues for valid samples
        if validation_results[f'valid_{sample_type}s']:
            warnings_found = False
            for sample in validation_results[f'valid_{sample_type}s']:
                if (sample.get('warnings') or sample.get('relationship_errors') or
                    sample.get('ontology_warnings')):
                    if not warnings_found:
                        report.append("\n\nWarnings and Non-Critical Issues:")
                        report.append("-" * 30)
                        warnings_found = True

                    report.append(f"\n{sample_type_title}: {sample['sample_name']} (index: {sample['index']})")
                    for warning in sample.get('warnings', []):
                        report.append(f"  WARNING: {warning}")
                    for error in sample.get('relationship_errors', []):
                        report.append(f"  RELATIONSHIP: {error}")
                    for warning in sample.get('ontology_warnings', []):
                        report.append(f"  ONTOLOGY: {warning}")

        return "\n".join(report)