from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import FeedingEvent, FeedingPlan, FeedingSchedule


def create_feeding_events_for_plan(plan: FeedingPlan) -> int:
    schedule = FeedingSchedule.objects.select_related("product").get(
        pk=plan.feeding_schedule_id
    )
    unit_id = schedule.product.unit_id

    day_stride = schedule.gap_between_completed_day + 1
    first_ration_time = time(0, 0)

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


def replace_feeding_plan(
    *,
    farm_id: int,
    old_plan: FeedingPlan,
    cycle,
    feeding_schedule: FeedingSchedule,
    start_date,
    end_date,
) -> FeedingPlan:
    with transaction.atomic():
        locked = FeedingPlan.objects.select_for_update().get(pk=old_plan.pk)
        if locked.deleted_at is not None:
            raise ValueError(
                "El plan ya fue archivado o reemplazado. Consulte el plan vigente del ciclo."
            )
        locked.deleted_at = timezone.now()
        locked.save(update_fields=["deleted_at"])
        FeedingEvent.objects.filter(
            feeding_plan_id=locked.pk,
            status=FeedingEvent.Status.SCHEDULED,
        ).delete()
        new_plan = FeedingPlan.objects.create(
            farm_id=farm_id,
            cycle=cycle,
            feeding_schedule=feeding_schedule,
            start_date=start_date,
            end_date=end_date,
        )
        create_feeding_events_for_plan(new_plan)
    return new_plan
