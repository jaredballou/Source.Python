# ../plugins/command.py

"""Provides a way to utilize sub-commands for a server command."""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python Imports
#   Collections
from collections import OrderedDict
#   Re
import re
#   TextWrap
from textwrap import TextWrapper

# Source.Python Imports
#   Commands
from commands.typed import TypedServerCommand
#   Core
from core import AutoUnload
#   Messages
from messages import HudDestination
from messages import TextMsg
#   Plugins
from plugins import plugins_logger
from plugins import _plugin_strings
from plugins.errors import PluginInstanceError
from plugins.errors import PluginManagerError
from plugins.instance import LoadedPlugin
from plugins.manager import PluginManager


# =============================================================================
# >> ALL DECLARATION
# =============================================================================
__all__ = ('SubCommandManager',
           )


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
# Get the sp.plugins.command logger
plugins_command_logger = plugins_logger.command


# =============================================================================
# >> CLASSES
# =============================================================================
class SubCommandManager(AutoUnload, OrderedDict):
    """Class used for executing sub-commands for the given console command."""

    # Set the default class values for base attributes
    logger = plugins_command_logger
    translations = _plugin_strings

    def __init__(self, command, description='', prefix=''):
        """Called on instance initialization."""
        # Re-call OrderedDict's __init__ to properly setup the object
        super().__init__()

        # Does the class have a proper manager object assigned?
        if not (hasattr(self, 'manager') and
                isinstance(self.manager, PluginManager)):

            # If not, raise an error
            raise PluginManagerError(PluginManagerError.__doc__)

        # Does the class have a proper instance class assigned?
        if not (hasattr(self, 'instance') and
                issubclass(self.instance, LoadedPlugin)):

            # If not, raise an error
            raise PluginInstanceError(PluginInstanceError.__doc__)

        # Store the command
        self._command = command

        # Store the prefix
        self._prefix = prefix if prefix else '[{0}] '.format(
            self.command.upper())

        # Set the prefix for the manager and instance classes
        self.manager.prefix = self.instance.prefix = self.prefix

        # Set the instance class for the manager class
        self.manager.instance = self.instance

    def sub_command(self, commands):
        """Add a sub-command.

        .. seealso:: :class:`commands.typed.TypedServerCommand`
        """
        if isinstance(commands, str):
            commands = [commands]

        return TypedServerCommand([self._command] + list(commands))

    @property
    def manager(self):
        """Raise an error if the inheriting class does not have their own."""
        raise NotImplementedError('No manager attribute defined for class.')

    @property
    def instance(self):
        """Raise an error if the inheriting class does not have their own."""
        raise NotImplementedError('No instance attribute defined for class.')

    @property
    def command(self):
        """Return the server command registered to the class."""
        return self._command

    @property
    def prefix(self):
        """Return the prefix to use in log messages."""
        return self._prefix

    def load_plugin(self, plugin_name):
        """Load a plugin by name."""
        # Is the given plugin name a proper name?
        if not self._is_valid_plugin_name(plugin_name):

            # Log a message that the given name is invalid
            self._log_message(self.prefix + self.translations[
                'Invalid Name'].get_string(plugin=plugin_name))

            # No need to go further
            return

        # Is the plugin already loaded?
        if plugin_name in self.manager:

            # Log a message that the plugin is already loaded
            self._log_message(self.prefix + self.translations[
                'Already Loaded'].get_string(plugin=plugin_name))

            # No need to go further
            return

        # Load the plugin and get its instance
        plugin = self.manager[plugin_name]

        # Was the plugin unable to be loaded?
        if plugin is None:

            # Log a message that the plugin was not loaded
            self._log_message(self.prefix + self.translations[
                'Unable to Load'].get_string(plugin=plugin_name))

            # No need to go further
            return

        # Log a message that the plugin was loaded
        self._log_message(self.prefix + self.translations[
            'Successful Load'].get_string(plugin=plugin_name))

    def unload_plugin(self, plugin_name):
        """Unload a plugin by name."""
        # Is the given plugin name a proper name?
        if not self._is_valid_plugin_name(plugin_name):

            # Send a message that the given name is invalid
            self._log_message(self.prefix + self.translations[
                'Invalid Name'].get_string(plugin=plugin_name))

            # No need to go further
            return

        # Is the plugin loaded?
        if plugin_name not in self.manager:

            # Send a message that the plugin is not loaded
            self._log_message(self.prefix + self.translations[
                'Not Loaded'].get_string(plugin=plugin_name))

            # No need to go further
            return

        # Unload the plugin
        del self.manager[plugin_name]

        # Send a message that the plugin was unloaded
        self._log_message(self.prefix + self.translations[
            'Successful Unload'].get_string(plugin=plugin_name))

    def reload_plugin(self, plugin_name):
        """Reload a plugin by name."""
        # Is the given plugin name a proper name?
        if not self._is_valid_plugin_name(plugin_name):

            # Send a message that the given name is invalid
            self._log_message(self.prefix + self.translations[
                'Invalid Name'].get_string(plugin=plugin_name))

            # No need to go further
            return

        # Unload the plugin
        self.unload_plugin(plugin_name)

        # Load the plugin
        self.load_plugin(plugin_name)

    def print_plugins(self):
        """Print all currently loaded plugins."""
        # Get the header message
        message = self.prefix + self.translations[
            'Plugins'].get_string() + '\n' + '=' * 61 + '\n\n\t'

        # Add all loaded plugins to the message
        message += '\n\t'.join(self.manager)

        # Add a breaker at the end of the message
        message += '\n\n' + '=' * 61

        # Send the message
        self._log_message(message)

    def _log_message(self, message):
        """Log a message."""
        # Log the message
        self.logger.log_message(message)

    @staticmethod
    def _is_valid_plugin_name(plugin_name):
        """Return whether or not the given plugin name is valid."""
        # Get the regular expression match for the given plugin name
        match = re.match('([A-Za-z][A-Za-z0-9_]*[A-Za-z0-9])$', plugin_name)

        # Return whether it is valid or not
        return False if match is None else match.group() == plugin_name
