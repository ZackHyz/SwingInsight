from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_backend_smoke() -> None:
    from swinginsight.settings import Settings

    settings = Settings.model_validate({})
    assert settings.app_name == "SwingInsight API"
