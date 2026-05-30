"""User-profile response shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ('ProfileAddress', 'ProfileCountry', 'ProfileEmails', 'ProfileLanguages', 'ProfileNames',
           'ProfileNamesExtension', 'ProfilePhoneNumbers', 'ProfileResponse',
           'ProfileUnitsOfMeasure', 'SaveProfileFields')


class ProfileAddress(TypedDict, total=False):
    """Postal-address block on a profile response."""

    addressLine1: str | None
    """First address line."""
    addressLine2: str | None
    """Second address line."""
    addressLine3: str | None
    """Third address line."""
    addressLine4: str | None
    """Fourth address line."""
    city: str | None
    """City."""
    district: str | None
    """District / state district."""
    neighbourhood: str | None
    """Neighbourhood."""
    postalCode: str | None
    """Postal / ZIP code."""
    state: str | None
    """State / province / region."""


class ProfileCountry(TypedDict, total=False):
    """Country block on a profile response."""

    countryCode: str
    """ISO-3166 alpha-3 country code (e.g. ``'USA'``)."""


class ProfileEmails(TypedDict, total=False):
    """Email-addresses block on a profile response."""

    email: str | None
    """Primary email address."""


class ProfileLanguages(TypedDict, total=False):
    """Languages block on a profile response."""

    preferredLanguage: str
    """BCP-47 locale tag (e.g. ``'en-US'``)."""


class ProfileNames(TypedDict, total=False):
    """First / middle / last name block on a profile response."""

    firstName: str | None
    """User's first name."""
    lastName: str | None
    """User's last name."""
    middleName: str | None
    """User's middle name."""


class ProfileNamesExtension(TypedDict, total=False):
    """One entry in the ``namesExtensions`` list (title, suffix, secondLastName)."""

    fieldName: str
    """Name of the auxiliary field (``'title'``, ``'suffix'``, …)."""
    value: str | None
    """Value of the field, or ``None`` when unset."""


class ProfilePhoneNumbers(TypedDict, total=False):
    """Phone-numbers block on a profile response."""

    alternatePhoneNumber: str | None
    """Alternate phone number."""
    mobilePhoneNumber: str | None
    """Mobile phone number."""
    phoneNumber: str | None
    """Primary phone number."""


class ProfileResponse(TypedDict, total=False):
    """
    Top-level shape of the user-profile lookup response.

    Field presence follows the ``profileGroups`` query parameter; every section may be absent.
    """

    address: ProfileAddress
    """Postal address."""
    country: ProfileCountry
    """Country code."""
    emails: ProfileEmails
    """Email addresses."""
    languages: ProfileLanguages
    """Preferred language."""
    names: ProfileNames
    """First / middle / last name."""
    namesExtensions: Sequence[ProfileNamesExtension]
    """Auxiliary name fields (title, suffix, …)."""
    phoneNumbers: ProfilePhoneNumbers
    """Phone numbers."""
    unitsOfMeasure: ProfileUnitsOfMeasure
    """User's preferred units (distance, pressure, speed, temperature)."""
    userGuid: str
    """Globally-unique user identifier."""


class ProfileUnitsOfMeasure(TypedDict, total=False):
    """Units-of-measure block on a profile response."""

    distance: str | None
    """Preferred distance unit (``'MI'`` / ``'KM'``)."""
    pressure: str | None
    """Preferred pressure unit (``'PSI'`` / ``'KPA'`` / ``'BAR'``)."""
    speed: str | None
    """Preferred speed unit (``'MPH'`` / ``'KPH'``)."""
    temperature: str | None
    """Preferred temperature unit (``'F'`` / ``'C'``); often ``None``."""


class SaveProfileFields(TypedDict, total=False):
    """Keyword-argument shape accepted by the ``PATCH .../users/me`` profile-update endpoint.

    Designed to be unpacked into ``save_profile(**fields)`` via :py:class:`typing.Unpack`.
    Every field is optional; only the sections the caller passes are updated.
    """

    address: ProfileAddress
    """New postal address."""
    country: ProfileCountry
    """New country code."""
    emails: ProfileEmails
    """New email addresses."""
    languages: ProfileLanguages
    """New preferred language."""
    names: ProfileNames
    """New first / middle / last name."""
    namesExtensions: Sequence[ProfileNamesExtension]
    """New auxiliary name fields (title, suffix, …)."""
    phoneNumbers: ProfilePhoneNumbers
    """New phone numbers."""
    unitsOfMeasure: ProfileUnitsOfMeasure
    """New preferred units (distance, pressure, speed, temperature)."""
