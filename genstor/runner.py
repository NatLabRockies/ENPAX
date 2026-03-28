import yaml
from pathlib import Path
from genstor.registry import REGISTRY
from genstor.outputs import SystemResult


class CentralRunner:
    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def from_yaml(cls, path: str) -> "CentralRunner":
        with open(path) as f:
            return cls(yaml.safe_load(f))

    def run(self) -> SystemResult:
        project_name = self.config.get("project_name", "unnamed_project")
        result = SystemResult(project_name=project_name)

        for tech_block in self.config["technologies"]:
            tech_type = tech_block["type"]
            if tech_type not in REGISTRY:
                raise ValueError(
                    f"Unknown tech type '{tech_type}'. "
                    f"Registered types: {list(REGISTRY.keys())}"
                )
            model = REGISTRY[tech_type](
                name=tech_block.get("name", tech_type),
                tech_type=tech_type,
                params=tech_block.get("params", {}),
            )
            result.tech_results.append(model.run())

        return result