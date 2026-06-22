"""Template registry for multi-template management."""

from pathlib import Path

import structlog

from src.config.loader import load_template
from src.config.models import AnalysisTemplate

log = structlog.get_logger()


class TemplateNotFoundError(Exception):
    """Raised when a requested template name is not registered."""


class TemplateRegistry:
    """Manage multiple analysis templates. Supports hot-reload.

    Usage:
        registry = TemplateRegistry("configs/templates")
        template = registry.get("sanzhen-jiuti")
        names = registry.list_all()
        registry.refresh()
    """

    def __init__(self, templates_dir: str = "configs/templates"):
        self.templates_dir = Path(templates_dir)
        self._templates: dict[str, AnalysisTemplate] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Scan the templates directory and load all .yaml files."""
        if not self.templates_dir.exists():
            log.warning("template.dir_not_found", dir=str(self.templates_dir))
            return

        for yaml_file in sorted(self.templates_dir.glob("*.yaml")):
            try:
                template = load_template(str(yaml_file))
                self._templates[template.name] = template
                log.info("template.loaded", name=template.name, file=str(yaml_file))
            except Exception as e:
                log.error("template.load_error", file=str(yaml_file), error=str(e))

    def get(self, name: str) -> AnalysisTemplate:
        """Get a template by its unique name."""
        if name not in self._templates:
            raise TemplateNotFoundError(
                f"模版 '{name}' 未注册。可用模版: {', '.join(self.list_all())}"
            )
        return self._templates[name]

    def list_all(self) -> list[str]:
        """Return all registered template names."""
        return list(self._templates.keys())

    def refresh(self) -> None:
        """Reload all templates from disk (hot-reload)."""
        self._templates.clear()
        self._load_all()
        log.info("template.refreshed", count=len(self._templates))
