from src.rase_settings import RaseSettings
from src.rase_functions import initializeDatabase
from src.correspondence_table_dialog import set_default_corrtable
import os

def init_rase(provided_datadir=None):
    settings = RaseSettings()
    if provided_datadir:
        settings.setDataDirectory(provided_datadir)
    settings.ensureDataDirectories()
    initializeDatabase(settings.getDatabaseFilepath())
    set_default_corrtable()