"""Service-planner upcoming + history detail response shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ('CompletedServiceActionDetail', 'MaintenanceDetails', 'MaintenanceItem', 'RecallItem',
           'ServiceActionDetail', 'ServicePerformed', 'ServicePlannerResponse')


class CompletedServiceActionDetail(TypedDict, total=False):
    """Detail response for one completed service event (``service history-detail``)."""

    dealerName: str
    """Human-readable dealer name."""
    editable: bool
    """Whether the user can amend this entry from the app."""
    id: str
    """Service-event identifier echoed back from the request."""
    odometerReading: float
    """Odometer reading at the time of service."""
    price: Mapping[str, object]
    """Money block - typically ``{amount, currency, total}``."""
    serviceDate: str
    """ISO-8601 date the service was completed."""
    serviceType: str
    """Categorisation of the work (``'Maintenance'``, ``'Repair'``, …)."""
    servicesPerformed: Sequence[ServicePerformed]
    """Itemised list of work performed."""


class MaintenanceDetails(TypedDict, total=False):
    """Inner ``maintenanceDetails`` block of an upcoming-maintenance detail response."""

    maintenanceDate: str
    """ISO-8601 date the maintenance is due."""
    overview: Sequence[str]
    """Free-text bullet list of work items the dealer will perform."""


class MaintenanceItem(TypedDict, total=False):
    """``maintenanceItem`` branch of a ``MAINTENANCE``-type service action detail."""

    maintenanceDetails: MaintenanceDetails
    """Nested per-action specifics."""


class RecallItem(TypedDict, total=False):
    """``recallItem`` branch of a ``RECALL``-type service action detail."""

    campaignNumber: str
    """Manufacturer recall campaign identifier."""
    description: str
    """Plain-text description of the defect."""
    nhtsaNumber: str
    """NHTSA-assigned recall identifier."""
    recallDate: str
    """ISO-8601 date the recall was issued."""
    recallType: str
    """Recall classification (``'Safety'``, ``'Compliance'``, …)."""
    remedy: str
    """Plain-text remedy / dealer-action description."""
    safetyRisk: str
    """Plain-text safety-risk explanation."""


class ServiceActionDetail(TypedDict, total=False):
    """Detail response for a single upcoming service action (maintenance or recall)."""

    id: str
    """Service-action identifier echoed back from the request."""
    maintenanceItem: MaintenanceItem
    """Present when ``serviceType == 'MAINTENANCE'``."""
    odometerReading: float
    """Current odometer reading the request was made with."""
    recallItem: RecallItem
    """Present when ``serviceType == 'RECALL'``."""
    serviceType: Literal['MAINTENANCE', 'RECALL']
    """Discriminator for the polymorphic body."""
    title: str
    """Human-readable summary."""


class ServicePerformed(TypedDict, total=False):
    """One entry from a completed-service-event's ``servicesPerformed`` list."""

    cost: Mapping[str, object]
    """Money block - typically ``{amount, currency, total}``."""
    name: str
    """Plain-text description of the service performed."""


class ServicePlannerResponse(TypedDict, total=False):
    """Top-level shape of the service-planner upcoming / history list response."""

    completedServiceActions: Sequence[CompletedServiceActionDetail]
    """Historical actions to surface in the planner."""
    response: Mapping[str, object]
    """
    Per-service detail block (used by single-item endpoints; the
    ``upcomingServiceActions`` / ``completedServiceActions`` lists are used by the
    planner-summary endpoints).
    """
    upcomingServiceActions: Sequence[ServiceActionDetail]
    """Pending / upcoming actions to surface in the planner."""
