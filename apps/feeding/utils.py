from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from .constants import FEEDING_WORKDAY_START_HOUR
from .models import FeedingEvent, FeedingPlan, FeedingSchedule


def create_feeding_events_for_plan(plan: FeedingPlan) -> int:
    """
    Genera filas FeedingEvent a partir del FeedingSchedule del plan: qué días hay
    jornada, cuántas raciones y a qué horas (ver reglas en código y negocio).
    """
    schedule = FeedingSchedule.objects.select_related("product").get(
        pk=plan.feeding_schedule_id
    )
    unit_id = schedule.product.unit_id

    day_stride = schedule.gap_between_completed_day + 1
    first_ration_time = time(FEEDING_WORKDAY_START_HOUR, 0)

    events: list[FeedingEvent] = []
    ration_number = 1
    day_index = 0
    current = plan.start_date

    while current <= plan.end_date:
        if day_index % day_stride == 0:
            base = datetime.combine(current, first_ration_time)
            for i in range(schedule.times_per_day):
                st = base + timedelta(minutes=i * schedule.gap_between_times_per_day)
                events.append(
                    FeedingEvent(
                        farm_id=plan.farm_id,
                        cycle_id=plan.cycle_id,
                        feeding_plan=plan,
                        date=st.date(),
                        scheduled_time=st.time(),
                        ration_number=ration_number,
                        planned_quantity=Decimal("0"),
                        planned_unit_id=unit_id,
                        status=FeedingEvent.Status.SCHEDULED,
                    )
                )
                ration_number += 1
        current += timedelta(days=1)
        day_index += 1

    if not events:
        return 0
    FeedingEvent.objects.bulk_create(events)
    return len(events)
