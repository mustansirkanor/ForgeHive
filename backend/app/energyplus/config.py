from pathlib import Path

PROJECT_ROOT = Path.home() / "projects" / "ForgeHive"

ENERGYPLUS_DIR = Path(r"C:\EnergyPlusV26-1-0")
ENERGYPLUS_EXE = ENERGYPLUS_DIR / "energyplus.exe"

DEFAULT_MODEL = ENERGYPLUS_DIR / "ExampleFiles" / "5ZoneAirCooled.idf"
DEFAULT_WEATHER = ENERGYPLUS_DIR / "WeatherData" / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"

RUNS_DIR = PROJECT_ROOT / "runs"
