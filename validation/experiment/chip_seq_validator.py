from typing import Type, Dict, List
import requests
import json
from pydantic import BaseModel
from validation.experiment.base_experiment_validator import BaseExperimentValidator
from validation.generic_validator_classes import OntologyValidator
from rulesets_pydantics.experiment.experiment_chip_seq_ruleset import (
    ChIPSeqDNABindingProteinsExperiment,
    ChIPSeqInputDNAExperiment
)


class ChIPSeqDNABindingProteinsValidator(BaseExperimentValidator):

    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return ChIPSeqDNABindingProteinsExperiment
    
    def get_experiment_type_name(self) -> str:
        return "chip-seq dna-binding proteins"
    
    def _get_relationship_errors(self, all_experiments: Dict[str, List[Dict]]) -> Dict[str, List[str]]:
        relationship_errors = {}
        
        # Get ChIP-seq DNA-binding proteins experiments
        dna_binding_experiments = all_experiments.get('chip-seq dna-binding proteins', [])
        input_dna_experiments = all_experiments.get('chip-seq input dna', [])
        
        # Build a set of Input DNA experiment aliases from current submission
        input_dna_aliases = set()
        for exp in input_dna_experiments:
            # Check both potential identifier fields
            alias = exp.get('Experiment Alias', '')
            if alias:
                input_dna_aliases.add(alias)
        
        # Validate each DNA-binding experiment
        for exp in dna_binding_experiments:
            identifier = exp.get('Sample Descriptor', 
                               exp.get('Experiment Alias', 'unknown'))
            control_exp = exp.get('Control Experiment')
            
            # Skip if no control experiment specified or if it's a special value
            if not control_exp or control_exp in [
                "not applicable", 
                "not collected", 
                "not provided", 
                "restricted access"
            ]:
                continue
            
            # Check if control experiment exists in current submission
            if control_exp in input_dna_aliases:
                continue
            
            # Check if control experiment exists in ENA
            if self._check_control_in_ena(control_exp):
                continue
            
            # Control experiment not found anywhere
            if identifier not in relationship_errors:
                relationship_errors[identifier] = []
            relationship_errors[identifier].append(
                f"Control experiment '{control_exp}' not found in this submission or in ENA"
            )
        
        return relationship_errors
    
    def _check_control_in_ena(self, experiment_alias: str) -> bool:
        try:
            url = f'https://www.ebi.ac.uk/ena/browser/api/summary/{experiment_alias}'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = json.loads(response.content)
                total = result.get('total', 0)
                if isinstance(total, (int, str)):
                    return int(total) > 0
        except requests.exceptions.Timeout:
            print(f"Timeout checking ENA for experiment: {experiment_alias}")
        except requests.exceptions.RequestException as e:
            print(f"Error checking ENA for experiment {experiment_alias}: {e}")
        except Exception as e:
            print(f"Unexpected error checking ENA for experiment {experiment_alias}: {e}")
        
        return False


class ChIPSeqInputDNAValidator(BaseExperimentValidator):

    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return ChIPSeqInputDNAExperiment
    
    def get_experiment_type_name(self) -> str:
        return "chip-seq input dna"
