from spf.base.base_policy import BasePolicy
from spf.spf_observation import SPFObservation

class SPFPolicy(BasePolicy):
    def __init__(self, instruction: str=''):
        self.instruction = instruction
        
    def get_obs(self) -> SPFObservation:
        self.obs = SPFObservation()

    def get_model(self):
        # self.model 
        raise NotImplementedError
    
    def reason(self):
        response = self.model(self.obs, self.instruction)

        return response

    
        
        