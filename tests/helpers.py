import os

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVERBEND = os.path.join(ENGINE, "examples", "riverbend")
RIVERBEND_CONFIG = os.path.join(RIVERBEND, "cazmind.json")
