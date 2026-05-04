from rest_framework import serializers

from .models import ProductionPlan, Cycle, CycleBatch


class ProductionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionPlan
        fields = [
            "id",
            "farm",
            "specie",
            "name",
            "type",
            "total_days",
            "expected_mortality_rate",
            "expected_final_weight",
            "expected_reproduction_rate",
            "version",
            "is_current",
            "parent",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["version", "is_current", "parent", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        if not instance.is_current:
            raise serializers.ValidationError(
                "No se puede actualizar un plan que no es la versión actual."
            )

        new_plan = ProductionPlan.objects.create(
            farm=instance.farm,
            specie=instance.specie,
            name=validated_data.get("name", instance.name),
            type=validated_data.get("type", instance.type),
            total_days=validated_data.get("total_days", instance.total_days),
            expected_mortality_rate=validated_data.get(
                "expected_mortality_rate", instance.expected_mortality_rate
            ),
            expected_final_weight=validated_data.get(
                "expected_final_weight", instance.expected_final_weight
            ),
            expected_reproduction_rate=validated_data.get(
                "expected_reproduction_rate", instance.expected_reproduction_rate
            ),
            version=instance.version + 1,
            is_current=True,
            parent=instance,
        )

        instance.is_current = False
        instance.save(update_fields=["is_current"])

        return new_plan


class CycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cycle
        fields = [
            "id",
            "farm",
            "specie",
            "pond",
            "production_plan",
            "name",
            "start_date",
            "estimated_finish_date",
            "finish_date",
            "state",
            "comments",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        pond = data.get("pond") or (self.instance.pond if self.instance else None)
        state = data.get("state") or (self.instance.state if self.instance else None)
        start_date = data.get("start_date") or (self.instance.start_date if self.instance else None)
        estimated_finish_date = data.get("estimated_finish_date") or (self.instance.estimated_finish_date if self.instance else None)
        finish_date = data.get("finish_date")

        BLOCKED_STATUSES = ["inactive", "cleaning"]
        if pond and pond.status in BLOCKED_STATUSES:
            raise serializers.ValidationError(
                f"No se puede crear ni editar un ciclo en un estanque con estado '{pond.get_status_display()}'."
            )


        if state == Cycle.State.IN_PROGRESS:
            ciclo_activo = Cycle.objects.filter(
                pond=pond,
                state=Cycle.State.IN_PROGRESS,
                deleted_at__isnull=True
            ).exclude(pk=self.instance.pk if self.instance else None).exists()

            if ciclo_activo:
                raise serializers.ValidationError(
                    f"El estanque '{pond.name}' ya tiene un ciclo en progreso."
                )

        #
        if start_date and estimated_finish_date:
            if estimated_finish_date <= start_date:
                raise serializers.ValidationError({
                    "estimated_finish_date": "La fecha estimada de fin debe ser mayor a la fecha de inicio."
                })


        if finish_date and state not in [Cycle.State.FINISHED, Cycle.State.CANCELLED]:
            raise serializers.ValidationError({
                "finish_date": "La fecha de fin solo se puede registrar cuando el ciclo está terminado o cancelado."
            })

        return data


class CycleBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleBatch
        fields = [
            "id",
            "cycle",
            "pond_batch",
            "quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
        ]

    def validate(self, data):
        cycle = data.get("cycle")
        pond_batch = data.get("pond_batch")

        
        if cycle and cycle.state != Cycle.State.IN_PROGRESS:
            raise serializers.ValidationError({
                "cycle": "Solo se pueden agregar lotes a ciclos en progreso."
            })

        if cycle and pond_batch:
            if pond_batch.batch.specie != cycle.specie:
                raise serializers.ValidationError({
                    "pond_batch": "La especie del lote no coincide con la especie del ciclo."
                })

        return data