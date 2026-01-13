from typing import Type
from pydantic import BaseModel
from validation.experiment.base_experiment_validator import BaseExperimentValidator
from validation.generic_validator_classes import OntologyValidator
from rulesets_pydantics.experiment.bs_seq_ruleset import FAANGBSSeqExperiment
from rulesets_pydantics.experiment.cage_seq_ruleset import FAANGCAGESeqExperiment
from rulesets_pydantics.experiment.dnase_seq_ruleset import FAANGDNaseSeqExperiment
from rulesets_pydantics.experiment.em_seq_ruleset import FAANGEMSeqExperiment
from rulesets_pydantics.experiment.hi_c_ruleset import FAANGHiCExperiment
from rulesets_pydantics.experiment.rna_seq_ruleset import FAANGRNASeqExperiment
from rulesets_pydantics.experiment.scrna_seq_ruleset import FAANGscRNASeqExperiment
from rulesets_pydantics.experiment.scatac_seq_ruleset import FAANGscATACSeqExperiment
from rulesets_pydantics.experiment.wgs_ruleset import FAANGWGSExperiment


class BSSeqValidator(BaseExperimentValidator):

    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGBSSeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "bs-seq"


class CAGESeqValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGCAGESeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "cage-seq"


class DNaseSeqValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGDNaseSeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "dnase-seq"


class EMSeqValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGEMSeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "em-seq"


class HiCValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGHiCExperiment
    
    def get_experiment_type_name(self) -> str:
        return "hi-c"


class RNASeqValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGRNASeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "rna-seq"


class scRNASeqValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGscRNASeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "scrna-seq"


class scATACSeqValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGscATACSeqExperiment
    
    def get_experiment_type_name(self) -> str:
        return "snatac-seq"


class WGSValidator(BaseExperimentValidator):
    
    def _initialize_validators(self):
        if self.ontology_validator is None:
            self.ontology_validator = OntologyValidator(cache_enabled=True)
    
    def get_model_class(self) -> Type[BaseModel]:
        return FAANGWGSExperiment
    
    def get_experiment_type_name(self) -> str:
        return "wgs"
