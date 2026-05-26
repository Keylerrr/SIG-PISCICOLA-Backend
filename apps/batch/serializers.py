from datetime import date

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from .models import Batch, BatchSource, BatchTransfer, PondBatch
from .services.stock import transfer_pond_batch_quantity


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = [
            "id",
            "specie",
            "farm",
            "origin_type",
            "origin_id",
            "code",
            "biological_state",
            "status",
            "comments",
            "initial_quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["code", "created_at", "updated_at"]

    def validate(self, data):
        min_weight = data.get("min_weight_g")
        avg_weight = data.get("avg_weight_g")
        max_weight = data.get("max_weight_g")

        if min_weight and avg_weight and max_weight:
            if not (min_weight <= avg_weight <= max_weight):
                raise serializers.ValidationError(
                    {
                        "weights": "min_weight_g <= avg_weight_g <= max_weight_g debe cumplirse."
                    }
                )

        origin_type = data.get("origin_type")
        origin_id = data.get("origin_id")

        if origin_type in [
            Batch.OriginType.PURCHASE_DETAIL,
            Batch.OriginType.HARVEST_CLASSIFICATION,
        ]:
            if not origin_id:
                raise serializers.ValidationError(
                    {"origin_id": f"origin_id es obligatorio para {origin_type}."}
                )

        return data

    def create(self, validated_data):
        farm = validated_data["farm"]
        timestamp = int(timezone.now().timestamp())
        code = f"BATCH-{farm.id}-{timestamp}"

        while Batch.objects.filter(code=code, farm=farm).exists():
            timestamp += 1
            code = f"BATCH-{farm.id}-{timestamp}"

        validated_data["code"] = code
        return super().create(validated_data)


class BatchSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchSource
        fields = ["id", "parent_batch", "child_batch", "quantity"]

    def validate(self, data):
        if data["parent_batch"] == data["child_batch"]:
            raise serializers.ValidationError(
                "Un lote no puede ser su propio padre o hijo."
            )
        if data["quantity"] <= 0:
            raise serializers.ValidationError(
                {"quantity": "La cantidad debe ser mayor a 0."}
            )
        return data


class PondBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PondBatch
        fields = [
            "id",
            "pond",
            "batch",
            "initial_quantity",
            "current_quantity",
            "start_date",
            "end_date",
        ]
        read_only_fields = ["current_quantity"]

    def validate(self, data):
        pond = data.get("pond")
        batch = data.get("batch")
        cantidad_nueva = data.get("initial_quantity", 0)
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if pond and pond.deleted_at is not None:
            raise serializers.ValidationError(
                {"pond": "El estanque ha sido eliminado y no está disponible."}
            )

        # Validar que el estanque esté en estado ACTIVE o IN_USE
        if pond and pond.status not in [pond.Status.ACTIVE, pond.Status.IN_USE]:
            raise serializers.ValidationError(
                {
                    "pond": f"Solo se pueden agregar lotes a estanques en estado ACTIVO o EN USO. "
                    f"Estado actual: '{pond.get_status_display()}'."
                }
            )

        if batch and batch.status != Batch.Status.ACTIVE:
            raise serializers.ValidationError(
                {
                    "batch": f"El lote no está activo. Estado actual: '{batch.get_status_display()}'."
                }
            )

        ya_asignado = PondBatch.objects.filter(
            batch=batch, end_date__isnull=True
        ).exists()
        if ya_asignado:
            raise serializers.ValidationError(
                {"batch": "El lote ya está asignado a un estanque activo."}
            )

        if pond and batch and pond.farm_id != batch.farm_id:
            raise serializers.ValidationError(
                {"pond": "El estanque debe pertenecer a la misma granja del lote."}
            )

        # Validar que no haya lotes de otras especies en el estanque
        if pond and batch:
            other_species = (
                PondBatch.objects.filter(pond=pond, end_date__isnull=True)
                .exclude(batch__specie=batch.specie)
                .exists()
            )

            if other_species:
                raise serializers.ValidationError({
                    "batch": "No se puede combinar lotes de especies distintas en un mismo estanque. "
                             "Ya hay lotes de otra especie en estado activo."
                })
        
        # ✓ NUEVA VALIDACIÓN: Verificar que la etapa biológica coincida
        if pond and batch:
            existing_batches = PondBatch.objects.filter(
                pond=pond,
                end_date__isnull=True
            ).select_related("batch")
            
            for existing_pond_batch in existing_batches:
                if existing_pond_batch.batch.biological_state != batch.biological_state:
                    raise serializers.ValidationError({
                        "batch": f"La etapa biológica del lote '{batch.get_biological_state_display()}' "
                                f"no coincide con la de los lotes existentes en el estanque "
                                f"'{existing_pond_batch.batch.get_biological_state_display()}'. "
                                f"Los lotes deben estar en la MISMA etapa biológica para convivir "
                                f"en el mismo estanque."
                    })

        if start_date and start_date > date.today():
            raise serializers.ValidationError(
                {"start_date": "La fecha de inicio no puede ser futura."}
            )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {
                    "end_date": "La fecha de fin debe ser mayor o igual a la fecha de inicio."
                }
            )

        cantidad_actual = (
            PondBatch.objects.filter(pond=pond, end_date__isnull=True).aggregate(
                total=Sum("current_quantity")
            )["total"]
            or 0
        )

        if cantidad_actual + cantidad_nueva > pond.capacity:
            raise serializers.ValidationError(
                {
                    "initial_quantity": f"El estanque '{pond.name}' supera su capacidad de "
                    f"{pond.capacity} peces. Disponible: {pond.capacity - cantidad_actual}."
                }
            )

        return data

    def create(self, validated_data):
        validated_data["current_quantity"] = validated_data["initial_quantity"]
        pond_batch = super().create(validated_data)

        # Cambiar el estado del estanque a IN_USE
        pond = pond_batch.pond
        if pond.status == pond.Status.ACTIVE:
            pond.status = pond.Status.IN_USE
            pond.save(update_fields=["status"])

        return pond_batch


class BatchTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchTransfer
        fields = [
            "id",
            "source_pond_batch",
            "to_pond_batch",
            "farm",
            "quantity",
            "date",
            "reason",
        ]

    def validate(self, data):
        from apps.cycle.models import Cycle, CyclePondBatch

        source = data["source_pond_batch"]
        destination = data["to_pond_batch"]
        quantity = data["quantity"]
        transfer_date = data.get("date")

        if quantity <= 0:
            raise serializers.ValidationError(
                {"quantity": "La cantidad debe ser mayor a 0."}
            )

        if transfer_date and transfer_date > date.today():
            raise serializers.ValidationError(
                {"date": "La fecha de transferencia no puede ser futura."}
            )

        if source.pond == destination.pond:
            raise serializers.ValidationError(
                {
                    "to_pond_batch": "El estanque origen y destino no pueden ser el mismo."
                }
            )

        # Validar que AMBOS estanques están INACTIVOS (sin ciclos activos)
        source_has_active_cycle = CyclePondBatch.objects.filter(
            pond_batch=source, cycle__state=Cycle.State.IN_PROGRESS
        ).exists()

        if source_has_active_cycle:
            raise serializers.ValidationError(
                {
                    "source_pond_batch": "El estanque origen tiene un ciclo activo. "
                    "BatchTransfer solo se permite entre estanques INACTIVOS. "
                    "Use GradingEvent para trasladar dentro de un ciclo activo."
                }
            )

        dest_has_active_cycle = CyclePondBatch.objects.filter(
            pond_batch=destination, cycle__state=Cycle.State.IN_PROGRESS
        ).exists()

        if dest_has_active_cycle:
            raise serializers.ValidationError(
                {
                    "to_pond_batch": "El estanque destino tiene un ciclo activo. "
                    "BatchTransfer solo se permite entre estanques INACTIVOS. "
                    "Use GradingEvent para trasladar dentro de un ciclo activo."
                }
            )

        if source.batch.status != Batch.Status.ACTIVE:
            raise serializers.ValidationError(
                {
                    "source_pond_batch": f"El lote no está activo. Estado actual: '{source.batch.get_status_display()}'."
                }
            )

        if source.batch.specie != destination.batch.specie:
            raise serializers.ValidationError(
                {
                    "to_pond_batch": "Los lotes deben ser de la misma especie para transferir."
                }
            )

        if source.batch.biological_state != destination.batch.biological_state:
            raise serializers.ValidationError(
                {
                    "to_pond_batch": "Los lotes deben tener el mismo estado biológico para transferir."
                }
            )

        if source.current_quantity < quantity:
            raise serializers.ValidationError(
                {
                    "quantity": f"Cantidad insuficiente. Disponible: {source.current_quantity}."
                }
            )

        if destination.batch.status != Batch.Status.ACTIVE:
            raise serializers.ValidationError(
                {
                    "to_pond_batch": f"El lote destino no está activo. Estado: '{destination.batch.get_status_display()}'."
                }
            )

        cantidad_actual_destino = (
            PondBatch.objects.filter(
                pond=destination.pond, end_date__isnull=True
            ).aggregate(total=Sum("current_quantity"))["total"]
            or 0
        )

        if cantidad_actual_destino + quantity > destination.pond.capacity:
            raise serializers.ValidationError(
                {
                    "to_pond_batch": f"El estanque destino '{destination.pond.name}' supera su capacidad de "
                    f"{destination.pond.capacity} peces. "
                    f"Disponible: {destination.pond.capacity - cantidad_actual_destino}."
                }
            )

        return data

    def create(self, validated_data):
        source = validated_data["source_pond_batch"]
        destination = validated_data["to_pond_batch"]
        quantity = validated_data["quantity"]

        try:
            transfer_pond_batch_quantity(source, destination, quantity)
        except ValueError as e:
            raise serializers.ValidationError({"quantity": str(e)})

        return super().create(validated_data)

