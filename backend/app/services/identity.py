from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from ..models.ais import AISMessage, VesselIdentity
from ..models.detection import IdentityChangeEvent


class IdentityTracker:
    """Detect changes in vessel identity metadata across AIS reports."""

    def analyse(
        self,
        identity: Optional[VesselIdentity],
        messages: Iterable[AISMessage],
    ) -> List[IdentityChangeEvent]:
        events: List[IdentityChangeEvent] = []
        current_identity = identity

        for message in messages:
            if current_identity is None:
                current_identity = VesselIdentity(mmsi=message.mmsi, imo=message.imo)
                continue

            if message.imo and current_identity.imo and message.imo != current_identity.imo:
                events.append(
                    IdentityChangeEvent(
                        mmsi=message.mmsi,
                        previous_imo=current_identity.imo,
                        new_imo=message.imo,
                        previous_name=current_identity.name,
                        new_name=current_identity.name,
                        timestamp=message.timestamp,
                        change_reason="IMO change detected",
                    )
                )
                current_identity = current_identity.copy(update={"imo": message.imo})
            elif message.imo and not current_identity.imo:
                current_identity = current_identity.copy(update={"imo": message.imo})

            if message.vessel_name and message.vessel_name != current_identity.name:
                events.append(
                    IdentityChangeEvent(
                        mmsi=message.mmsi,
                        previous_imo=current_identity.imo,
                        new_imo=current_identity.imo,
                        previous_name=current_identity.name,
                        new_name=message.vessel_name,
                        timestamp=message.timestamp,
                        change_reason="Vessel name change detected",
                    )
                )
                current_identity = current_identity.copy(update={"name": message.vessel_name})

        return events
