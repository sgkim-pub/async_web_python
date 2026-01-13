import os.path
import json

class AppConfig():
    def __init__(self, configPath):
        configPath = os.path.abspath(configPath)

        with open(configPath) as configFile:
            self.config = json.load(configFile)

        self.DB = self.config.get("DB")
        self.DB_USER = self.config.get("DB_USER")
        self.DB_PASSWORD = self.config.get("DB_PASSWORD")
        self.JWT_SECRET = self.config.get("JWT_SECRET")
        self.JWT_ALGORITHM = self.config.get("JWT_ALGORITHM")
