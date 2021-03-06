# ../entities/entity.py

"""Provides a base class to interact with a specific entity."""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python Imports
#   Contextlib
from contextlib import suppress

# Source.Python Imports
#   Core
from core import GAME_NAME
#   Engines
from engines.precache import Model
from engines.trace import engine_trace
from engines.trace import ContentMasks
from engines.trace import GameTrace
from engines.trace import Ray
from engines.trace import TraceFilterSimple
#   Entities
from entities import BaseEntityGenerator
from entities import TakeDamageInfo
from entities.classes import server_classes
from entities.constants import DamageTypes
from entities.constants import RenderMode
from entities.helpers import edict_from_index
from entities.helpers import index_from_inthandle
from entities.helpers import index_from_pointer
#   Filters
from filters.weapons import WeaponClassIter
#   Memory
from memory import get_object_pointer
from memory import make_object
#   Players
from players.constants import HitGroup
#   Studio
from studio.cache import model_cache
from studio.constants import INVALID_ATTACHMENT_INDEX


# =============================================================================
# >> FORWARD IMPORTS
# =============================================================================
# Source.Python Imports
#   Entities
from _entities._entity import BaseEntity


# =============================================================================
# >> ALL DECLARATION
# =============================================================================
# Add all the global variables to __all__
__all__ = ('BaseEntity',
           'Entity',
           )


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
# Get a list of projectiles for the game
_projectile_weapons = [weapon.name for weapon in WeaponClassIter('grenade')]


# =============================================================================
# >> CLASSES
# =============================================================================
class Entity(BaseEntity):
    """Class used to interact directly with entities."""

    def __init__(self, index):
        """Initialize the Entity object."""
        # Initialize the object
        super().__init__(index)

        # Set the entity's base attributes
        object.__setattr__(self, '_index', index)

    def __eq__(self, other):
        """Return True if both entities have the same index."""
        return self.index == other.index

    def __hash__(self):
        """Return a hash value based on the entity index."""
        # Required for sets, because we have implemented __eq__
        return hash(self.index)

    def __getattr__(self, attr):
        """Find if the attribute is valid and returns the appropriate value."""
        # Loop through all of the entity's server classes
        for server_class in self.server_classes:

            # Does the current server class contain the given attribute?
            if hasattr(server_class, attr):

                # Return the attribute's value
                return getattr(make_object(server_class, self.pointer), attr)

        # If the attribute is not found, raise an error
        raise AttributeError('Attribute "{0}" not found'.format(attr))

    def __setattr__(self, attr, value):
        """Find if the attribute is value and sets its value."""
        # Is the given attribute a property?
        if (attr in super().__dir__() and isinstance(
                getattr(self.__class__, attr, None), property)):

            # Set the property's value
            object.__setattr__(self, attr, value)

            # No need to go further
            return

        # Loop through all of the entity's server classes
        for server_class in self.server_classes:

            # Does the current server class contain the given attribute?
            if hasattr(server_class, attr):

                # Set the attribute's value
                setattr(server_class(self.pointer, wrap=True), attr, value)

                # No need to go further
                return

        # If the attribute is not found, just set the attribute
        super().__setattr__(attr, value)

    def __dir__(self):
        """Return an alphabetized list of attributes for the instance."""
        # Get the base attributes
        attributes = set(super().__dir__())

        # Loop through all server classes for the entity
        for server_class in self.server_classes:

            # Loop through all of the server class' attributes
            for attr in dir(server_class):

                # Add the attribute if it is not private
                if not attr.startswith('_'):
                    attributes.add(attr)

        # Return a sorted list of attributes
        return sorted(attributes)

    @classmethod
    def create(cls, classname):
        """Create a new networked entity with the given classname."""
        entity = BaseEntity.create(classname)
        if entity.is_networked():
            return cls(entity.index)

        entity.destroy()
        raise ValueError('"{}" is not a networked entity.'.format(classname))

    @classmethod
    def find(cls, classname):
        """Try to find an entity with the given classname.

        If not entity has been found, None will be returned.

        :param str classname: The classname of the entity.
        :return: Return the found entity.
        :rtype: Entity
        """
        entity = BaseEntity.find(classname)
        if entity is not None and entity.is_networked():
            return cls(entity.index)

        return None

    @classmethod
    def find_or_create(cls, classname):
        """Try to find an entity with the given classname.

        If no entity has been found, it will be created.

        :param str classname: The classname of the entity.
        :return: Return the found or created entity.
        :rtype: Entity
        """
        entity = cls.find(classname)
        if entity is None:
            entity = cls.create(classname)

        return entity

    @classmethod
    def _obj(cls, ptr):
        """Return an entity instance of the given pointer."""
        return cls(index_from_pointer(ptr))

    @property
    def index(self):
        """Return the entity's index."""
        return self._index

    @property
    def server_classes(self):
        """Yield all server classes for the entity."""
        yield from server_classes.get_entity_server_classes(self)

    @property
    def properties(self):
        """Iterate over all descriptors available for the entity."""
        for server_class in self.server_classes:
            yield from server_class.properties

    @property
    def inputs(self):
        """Iterate over all inputs available for the entity."""
        for server_class in self.server_classes:
            yield from server_class.inputs

    @property
    def outputs(self):
        """Iterate over all outputs available for the entity."""
        for server_class in self.server_classes:
            yield from server_class.outputs

    @property
    def keyvalues(self):
        """Iterate over all entity keyvalues available for the entity.

        .. note::

            An entity might also have hardcoded keyvalues that can't be listed
            with this property.
        """
        for server_class in self.server_classes:
            yield from server_class.keyvalues

    def get_color(self):
        """Return the entity's color as a Color instance."""
        return self.render_color

    def set_color(self, color):
        """Set the entity's color."""
        # Set the entity's render mode
        self.render_mode = RenderMode.TRANS_COLOR

        # Set the entity's color
        self.render_color = color

        # Set the entity's alpha
        self.render_amt = color.a

    # Set the "color" property for Entity
    color = property(
        get_color, set_color,
        doc="""Property to get/set the entity's color values.""")

    def get_model(self):
        """Return the entity's model."""
        return Model(self.model_name)

    def set_model(self, model):
        """Set the entity's model to the given model."""
        self.model_index = model.index
        self.set_key_value_string('model', model.path)

    model = property(
        get_model, set_model,
        doc="""Property to get/set the entity's model.""")

    @property
    def model_header(self):
        """Return a ModelHeader instance of the current entity's model."""
        return model_cache.get_model_header(model_cache.find_model(
            self.model.path))

    def get_property_bool(self, name):
        """Return the boolean property."""
        return self._get_property(name, 'bool')

    def get_property_color(self, name):
        """Return the Color property."""
        return self._get_property(name, 'Color')

    def get_property_edict(self, name):
        """Return the Edict property."""
        return self._get_property(name, 'Edict')

    def get_property_float(self, name):
        """Return the float property."""
        return self._get_property(name, 'float')

    def get_property_int(self, name):
        """Return the integer property."""
        return self._get_property(name, 'int')

    def get_property_interval(self, name):
        """Return the Interval property."""
        return self._get_property(name, 'Interval')

    def get_property_pointer(self, name):
        """Return the pointer property."""
        return self._get_property(name, 'pointer')

    def get_property_quaternion(self, name):
        """Return the Quaternion property."""
        return self._get_property(name, 'Quaternion')

    def get_property_short(self, name):
        """Return the short property."""
        return self._get_property(name, 'short')

    def get_property_ushort(self, name):
        """Return the ushort property."""
        return self._get_property(name, 'ushort')

    def get_property_string(self, name):
        """Return the string property."""
        return self._get_property(name, 'string_array')

    def get_property_string_pointer(self, name):
        """Return the string property."""
        return self._get_property(name, 'string_pointer')

    def get_property_uchar(self, name):
        """Return the uchar property."""
        return self._get_property(name, 'uchar')

    def get_property_uint(self, name):
        """Return the uint property."""
        return self._get_property(name, 'uint')

    def get_property_vector(self, name):
        """Return the Vector property."""
        return self._get_property(name, 'Vector')

    def _get_property(self, name, prop_type):
        """Verify the type and return the property."""
        # Loop through all entity server classes
        for server_class in self.server_classes:

            # Is the name a member of the current server class?
            if name not in server_class.properties:
                continue

            # Is the type the correct type?
            if prop_type != server_class.properties[name].prop_type:
                raise TypeError('Property "{0}" is of type {1} not {2}'.format(
                    name, server_class.properties[name].prop_type, prop_type))

            # Return the property for the entity
            return getattr(
                make_object(server_class._properties, self.pointer), name)

        # Raise an error if the property name was not found
        raise ValueError(
            'Property "{0}" not found for entity type "{1}"'.format(
                name, self.classname))

    def set_property_bool(self, name, value):
        """Set the boolean property."""
        self._set_property(name, 'bool', value)

    def set_property_color(self, name, value):
        """Set the Color property."""
        self._set_property(name, 'Color', value)

    def set_property_edict(self, name, value):
        """Set the Edict property."""
        self._set_property(name, 'Edict', value)

    def set_property_float(self, name, value):
        """Set the float property."""
        self._set_property(name, 'float', value)

    def set_property_int(self, name, value):
        """Set the integer property."""
        self._set_property(name, 'int', value)

    def set_property_interval(self, name, value):
        """Set the Interval property."""
        self._set_property(name, 'Interval', value)

    def set_property_pointer(self, name, value):
        """Set the pointer property."""
        self._set_property(name, 'pointer', value)

    def set_property_quaternion(self, name, value):
        """Set the Quaternion property."""
        self._set_property(name, 'Quaternion', value)

    def set_property_short(self, name, value):
        """Set the short property."""
        self._set_property(name, 'short', value)

    def set_property_ushort(self, name, value):
        """Set the ushort property."""
        self._set_property(name, 'ushort', value)

    def set_property_string(self, name, value):
        """Set the string property."""
        self._set_property(name, 'string_array', value)

    def set_property_string_pointer(self, name, value):
        """Set the string property."""
        self._set_property(name, 'string_pointer', value)

    def set_property_uchar(self, name, value):
        """Set the uchar property."""
        self._set_property(name, 'uchar', value)

    def set_property_uint(self, name, value):
        """Set the uint property."""
        self._set_property(name, 'uint', value)

    def set_property_vector(self, name, value):
        """Set the Vector property."""
        self._set_property(name, 'Vector', value)

    def _set_property(self, name, prop_type, value):
        """Verify the type and set the property."""
        # Loop through all entity server classes
        for server_class in self.server_classes:

            # Is the name a member of the current server class?
            if name not in server_class.properties:
                continue

            # Is the type the correct type?
            if prop_type != server_class.properties[name].prop_type:
                raise TypeError('Property "{0}" is of type {1} not {2}'.format(
                    name, server_class.properties[name].prop_type, prop_type))

            # Set the property for the entity
            setattr(make_object(
                server_class._properties, self.pointer), name, value)

            # Is the property networked?
            if server_class.properties[name].networked:

                # Notify the change of state
                self.edict.state_changed()

            # No need to go further
            return

        # Raise an error if the property name was not found
        raise ValueError(
            'Property "{0}" not found for entity type "{1}"'.format(
                name, self.classname))

    def get_input(self, name):
        """Return the InputFunction instance for the given name."""
        # Loop through each server class for the entity
        for server_class in self.server_classes:

            # Does the current server class contain the input?
            if name in server_class.inputs:

                # Return the InputFunction instance for the given input name
                return getattr(
                    make_object(server_class._inputs, self.pointer), name)

        # If no server class contains the input, raise an error
        raise ValueError(
            'Unknown input "{0}" for entity type "{1}".'.format(
                name, self.classname))

    def call_input(self, name, *args, **kwargs):
        """Call the InputFunction instance for the given name."""
        self.get_input(name)(*args, **kwargs)

    def lookup_attachment(self, name):
        """Return the attachment index matching the given name."""
        # Get the ModelHeader instance of the entity
        model_header = self.model_header

        # Loop through all attachments
        for index in range(model_header.attachments_count):

            # Are the names matching?
            if name == model_header.get_attachment(index).name:

                # Return the current index
                return index

        # No attachment found
        return INVALID_ATTACHMENT_INDEX

    def is_in_solid(
            self, mask=ContentMasks.ALL, generator=BaseEntityGenerator):
        """Return whether or not the entity is in solid."""
        # Get a Ray object of the entity physic box
        ray = Ray(self.origin, self.origin, self.mins, self.maxs)

        # Get a new GameTrace instance
        trace = GameTrace()

        # Do the trace
        engine_trace.trace_ray(ray, mask, TraceFilterSimple(
            [entity.index for entity in generator()]), trace)

        # Return whether or not the trace did hit
        return trace.did_hit()

    def take_damage(
            self, damage, damage_type=DamageTypes.GENERIC, attacker_index=None,
            weapon_index=None, hitgroup=HitGroup.GENERIC, skip_hooks=False,
            **kwargs):
        """Method used to hurt the entity with the given arguments."""
        # Import Entity classes
        # Doing this in the global scope causes cross import errors
        from weapons.entity import Weapon

        # Is the game supported?
        if not hasattr(self, 'on_take_damage'):

            # Raise an error if not supported
            raise NotImplementedError(
                '"take_damage" is not implemented for {0}'.format(GAME_NAME))

        # Store values for later use
        attacker = None
        weapon = None

        # Was an attacker given?
        if attacker_index is not None:

            # Try to get the Entity instance of the attacker
            with suppress(ValueError):
                attacker = Entity(attacker_index)

        # Was a weapon given?
        if weapon_index is not None:

            # Try to get the Weapon instance of the weapon
            with suppress(ValueError):
                weapon = Weapon(weapon_index)

        # Is there a weapon but no attacker?
        if attacker is None and weapon is not None:

            # Try to get the attacker based off of the weapon's owner
            with suppress(ValueError, OverflowError):
                attacker_index = index_from_inthandle(weapon.current_owner)
                attacker = Entity(attacker_index)

        # Is there an attacker but no weapon?
        if attacker is not None and weapon is None:

            # Try to use the attacker's active weapon
            with suppress(AttributeError, ValueError, OverflowError):
                weapon = Weapon(index_from_inthandle(attacker.active_weapon))

        # Try to set the hitgroup
        with suppress(AttributeError):
            self.hitgroup = hitgroup

        # Get a TakeDamageInfo instance
        take_damage_info = TakeDamageInfo()

        # Is there a valid weapon?
        if weapon is not None:

            # Is the weapon a projectile?
            if weapon.classname in _projectile_weapons:

                # Set the inflictor to the weapon's index
                take_damage_info.inflictor = weapon.index

            # Is the weapon not a projectile and the attacker is valid?
            elif attacker_index is not None:

                # Set the inflictor to the attacker's index
                take_damage_info.inflictor = attacker_index

            # Set the weapon to the weapon's index
            take_damage_info.weapon = weapon.index

        # Is the attacker valid?
        if attacker_index is not None:

            # Set the attacker to the attacker's index
            take_damage_info.attacker = attacker_index

        # Set the damage amount
        take_damage_info.damage = damage

        # Set the damage type value
        take_damage_info.type = damage_type

        # Loop through the given keywords
        for item in kwargs:

            # Set the offset's value
            setattr(take_damage_info, item, kwargs[item])

        if skip_hooks:
            self.on_take_damage.skip_hooks(take_damage_info)
        else:
            self.on_take_damage(take_damage_info)
