from django.contrib import admin

from .models import (
    Batch,
    BatchSource,
    BatchTransfer,
    Cycle,
    CycleBatch,
    GradingEvent,
    PondBatch,
    ProductionPlan,
)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ["code", "farm", "specie", "biological_state", "status", "created_at"]
    list_filter = ["farm", "status", "biological_state", "created_at"]
    search_fields = ["code", "farm__name", "specie__name"]
    readonly_fields = ["code", "created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "code",
                    "farm",
                    "specie",
                    "origin_type",
                    "origin_id",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "biological_state",
                    "status",
                )
            },
        ),
        (
            "Quantity & Weights",
            {
                "fields": (
                    "initial_quantity",
                    "min_weight_g",
                    "avg_weight_g",
                    "max_weight_g",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "comments",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(BatchSource)
class BatchSourceAdmin(admin.ModelAdmin):
    list_display = ["parent_batch", "child_batch", "quantity"]
    list_filter = ["parent_batch__farm"]
    search_fields = ["parent_batch__code", "child_batch__code"]
    fieldsets = (
        (
            "Genealogy",
            {
                "fields": (
                    "parent_batch",
                    "child_batch",
                    "quantity",
                )
            },
        ),
    )


@admin.register(PondBatch)
class PondBatchAdmin(admin.ModelAdmin):
    list_display = ["batch", "pond", "initial_quantity", "current_quantity", "start_date"]
    list_filter = ["pond__farm", "start_date"]
    search_fields = ["batch__code", "pond__name"]
    readonly_fields = ["start_date"]
    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "pond",
                    "batch",
                )
            },
        ),
        (
            "Quantities",
            {
                "fields": (
                    "initial_quantity",
                    "current_quantity",
                )
            },
        ),
        (
            "Timeline",
            {
                "fields": (
                    "start_date",
                    "end_date",
                )
            },
        ),
    )


@admin.register(BatchTransfer)
class BatchTransferAdmin(admin.ModelAdmin):
    list_display = ["date", "source_pond_batch", "to_pond_batch", "quantity", "farm"]
    list_filter = ["farm", "date"]
    search_fields = ["source_pond_batch__batch__code", "to_pond_batch__batch__code", "reason"]
    fieldsets = (
        (
            "Transfer Details",
            {
                "fields": (
                    "farm",
                    "date",
                    "quantity",
                    "reason",
                )
            },
        ),
        (
            "Ponds",
            {
                "fields": (
                    "source_pond_batch",
                    "to_pond_batch",
                )
            },
        ),
    )


@admin.register(ProductionPlan)
class ProductionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "farm", "specie", "type", "version", "is_current", "created_at"]
    list_filter = ["farm", "type", "is_current", "created_at"]
    search_fields = ["name", "farm__name", "specie__name"]
    readonly_fields = ["version", "created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "farm",
                    "specie",
                    "name",
                    "type",
                )
            },
        ),
        (
            "Parameters",
            {
                "fields": (
                    "total_days",
                    "expected_mortality_rate",
                    "expected_final_weight",
                    "expected_reproduction_rate",
                )
            },
        ),
        (
            "Versioning",
            {
                "fields": (
                    "version",
                    "is_current",
                    "parent",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "deleted_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ["name", "farm", "specie", "state", "start_date", "estimated_finish_date"]
    list_filter = ["farm", "state", "start_date"]
    search_fields = ["name", "farm__name", "specie__name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "farm",
                    "specie",
                    "pond",
                    "production_plan",
                    "name",
                )
            },
        ),
        (
            "Status & Dates",
            {
                "fields": (
                    "state",
                    "start_date",
                    "estimated_finish_date",
                    "finish_date",
                )
            },
        ),
        (
            "Weights",
            {
                "fields": (
                    "min_weight_g",
                    "avg_weight_g",
                    "max_weight_g",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "comments",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(CycleBatch)
class CycleBatchAdmin(admin.ModelAdmin):
    list_display = ["cycle", "pond_batch", "quantity"]
    list_filter = ["cycle__farm"]
    search_fields = ["cycle__name", "pond_batch__batch__code"]
    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "cycle",
                    "pond_batch",
                    "quantity",
                )
            },
        ),
        (
            "Weights",
            {
                "fields": (
                    "min_weight_g",
                    "avg_weight_g",
                    "max_weight_g",
                )
            },
        ),
    )


@admin.register(GradingEvent)
class GradingEventAdmin(admin.ModelAdmin):
    list_display = ["date", "cycle", "quantity", "source_pond_batch", "to_pond_batch"]
    list_filter = ["cycle__farm", "date"]
    search_fields = ["cycle__name", "source_pond_batch__batch__code", "to_pond_batch__batch__code"]
    fieldsets = (
        (
            "Event Details",
            {
                "fields": (
                    "cycle",
                    "date",
                    "quantity",
                )
            },
        ),
        (
            "Transfer",
            {
                "fields": (
                    "source_pond_batch",
                    "to_pond_batch",
                )
            },
        ),
        (
            "Weights",
            {
                "fields": (
                    "min_weight_g",
                    "avg_weight_g",
                    "max_weight_g",
                )
            },
        ),
    )
