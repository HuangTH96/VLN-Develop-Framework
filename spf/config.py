from abc import ABC, abstractmethod

class Config(ABC):
    def __init__(self, cfg_path: str):
        self.config_path = self._load_config(cfg_path)

    @abstractmethod
    def _load_config(path:str):
        pass

class SPFAirSimConfig(Config):
    def __init__(self):
        super.__init__()

    def _load_config(path):
        return super()._load_config()