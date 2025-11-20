import gi
gi.require_version('Secret', '1')
from gi.repository import Secret, GLib, Gio
import logging

from .constants import APP_ID

# Схема для хранения паролей в системной связке ключей.
# Атрибуты помогают однозначно идентифицировать запись.
SCHEMA = Secret.Schema.new("com.example.thongssh.password",
                           Secret.SchemaFlags.NONE,
                           {
                               "app_id": Secret.SchemaAttributeType.STRING,
                               "host_name": Secret.SchemaAttributeType.STRING,
                           })

class KeyringManager:
    """
    A manager class to handle storing, retrieving, and deleting passwords
    from the system's keyring using libsecret.
    """

    def save_password(self, host_name, password):
        """
        Saves or updates a password in the keyring for a given host name.
        """
        if not host_name or not password:
            logging.warning("Keyring: Attempted to save password with empty host_name or password.")
            return

        attributes = {
            "app_id": APP_ID,
            "host_name": host_name,
        }
        label = f"Password for {host_name} in ThongSSH"

        Secret.password_store_sync(SCHEMA, attributes, Secret.COLLECTION_DEFAULT, label, password, None)
        logging.info(f"Keyring: Password for '{host_name}' saved successfully.")

    def load_password(self, host_name):
        """
        Loads a password from the keyring for a given host name.
        Returns the password string or None if not found.
        """
        if not host_name:
            return None

        attributes = {
            "app_id": APP_ID,
            "host_name": host_name,
        }
        item = Secret.password_lookup_sync(SCHEMA, attributes, None)
        return item # This function directly returns the password string or None

    def clear_password(self, host_name):
        """
        Deletes a password from the keyring for a given host name.
        """
        if not host_name:
            return

        attributes = {"app_id": APP_ID, "host_name": host_name}
        Secret.password_clear_sync(SCHEMA, attributes, None)
        logging.info(f"Keyring: Password for '{host_name}' cleared.")
