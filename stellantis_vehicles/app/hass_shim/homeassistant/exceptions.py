class HomeAssistantError(Exception):
    def __init__(self, *args, translation_domain=None, translation_key=None, translation_placeholders=None):
        super().__init__(*args)
        self.translation_domain = translation_domain
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders


class ConfigEntryAuthFailed(HomeAssistantError):
    pass


class ServiceValidationError(HomeAssistantError):
    """Invalid use of a service/command by the user (HA shows it as a toast;
    the add-on only logs it)."""
