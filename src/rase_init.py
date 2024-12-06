from src.rase_settings import RaseSettings
from src.rase_functions import initializeDatabase
import os

def init_rase(provided_datadir=None):
    settings = RaseSettings()
    if provided_datadir:
        os.makedirs(provided_datadir, exist_ok=True)
        settings.setDataDirectory(provided_datadir)
    dataDir = settings.getDataDirectory()
    os.makedirs(dataDir, exist_ok=True)
    initializeDatabase(settings.getDatabaseFilepath())