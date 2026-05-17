from rest_framework import serializers
from datetime import date

from .models import FishEvaluated, DailyStat, ProductUsageLog, ControlStat
from .services import BiomassCalculator, FishEvaluatedCalculator
from apps.batch.models import Batch, PondBatch
from apps.cycle.models import Cycle
from apps.ponds.models import Pond
from apps.products.models import Product
from apps.purchases.utils import create_out_movement
from apps.purchases.models import InventoryMovement


class FishEvaluatedSerializer(serializers.ModelSerializer):
    """
    Serializer para evaluaciones de peces con validaciones completas.
    Los pesos (min, avg, max) se calculan automáticamente desde los lotes activos del estanque.
    """

    class Meta:
        model = FishEvaluated
        fields = [
            "id",
            "cycle",
            "pond",
            "evaluation_date",
            "sampled_quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "mortality_quantity",
            "observations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "min_weight_g", "avg_weight_g", "max_weight_g"]

    def validate(self, data):
        cycle = data.get("cycle") or (self.instance.cycle if self.instance else None)
        pond = data.get("pond") or (self.instance.pond if self.instance else None)
        evaluation_date = data.get("evaluation_date") or (
            self.instance.evaluation_date if self.instance else None
        )
        sampled_quantity = data.get("sampled_quantity") or (
            self.instance.sampled_quantity if self.instance else None
        )
        mortality_quantity = data.get("mortality_quantity") or (
            self.instance.mortality_quantity if self.instance else 0
        )

        # Validar que el ciclo existe y está IN_PROGRESS
        if cycle:
            if cycle.state != Cycle.State.IN_PROGRESS:
                raise serializers.ValidationError({
                    "cycle": "El ciclo debe estar en estado IN_PROGRESS."
                })

        # Validar que el estanque existe y está IN_USE
        if pond:
            if pond.status != Pond.Status.IN_USE:
                raise serializers.ValidationError({
                    "pond": "El estanque debe estar en estado IN_USE."
                })

        # Validar que el estanque está asociado al ciclo
        if cycle and pond:
            cpb_exists = PondBatch.objects.filter(
                pond=pond,
                pond_batch__cycle_pond_batches__cycle=cycle,
            ).exists()
            if not cpb_exists:
                raise serializers.ValidationError({
                    "pond": "El estanque no está asociado a este ciclo."
                })

        # Validar cantidad muestreada > 0
        if sampled_quantity is not None and sampled_quantity <= 0:
            raise serializers.ValidationError({
                "sampled_quantity": "La cantidad de peces evaluados debe ser mayor a 0."
            })

        # Validar mortalidad <= muestra
        if (
            sampled_quantity is not None
            and mortality_quantity is not None
            and mortality_quantity > sampled_quantity
        ):
            raise serializers.ValidationError({
                "mortality_quantity": "La mortalidad no puede ser mayor a la cantidad muestreada."
            })

        # Validar que la fecha de evaluación <= hoy
        if evaluation_date and evaluation_date > date.today():
            raise serializers.ValidationError({
                "evaluation_date": "La fecha de evaluación no puede ser futura."
            })

        return data

    def create(self, validated_data):
        """
        Crea una evaluación de peces calculando automáticamente los pesos
        desde los lotes activos del estanque.
        """
        pond = validated_data.get("pond")
        
        # Calcular pesos desde los lotes activos del estanque
        weights = BiomassCalculator.get_active_pond_weights(pond.id)
        
        validated_data["min_weight_g"] = weights["min_weight_g"]
        validated_data["avg_weight_g"] = weights["avg_weight_g"]
        validated_data["max_weight_g"] = weights["max_weight_g"]
        
        return super().create(validated_data)


class ProductUsageLogSerializer(serializers.ModelSerializer):
    """
    Serializer para registros de uso de productos.
    """

    class Meta:
        model = ProductUsageLog
        fields = [
            "id",
            "daily_stat",
            "product",
            "quantity_used",
            "unit",
            "batch",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        daily_stat = data.get("daily_stat")
        product = data.get("product")
        batch = data.get("batch")
        quantity_used = data.get("quantity_used")

        # Validar cantidad > 0
        if quantity_used is not None and quantity_used <= 0:
            raise serializers.ValidationError({
                "quantity_used": "La cantidad usada debe ser mayor a 0."
            })

        # Validar que el producto pertenece a la misma farm
        if daily_stat and product:
            if product.farm_id != daily_stat.cycle.farm_id:
                raise serializers.ValidationError({
                    "product": "El producto debe pertenecer a la misma granja que el ciclo."
                })

        # Validar que el batch pertenece a la misma farm
        if daily_stat and batch:
            if batch.farm_id != daily_stat.cycle.farm_id:
                raise serializers.ValidationError({
                    "batch": "El lote debe pertenecer a la misma granja que el ciclo."
                })

        # Validar que el batch está ACTIVE
        if batch and batch.status != Batch.Status.ACTIVE:
            raise serializers.ValidationError({
                "batch": "El lote debe estar en estado ACTIVE."
            })

        return data


class DailyStatSerializer(serializers.ModelSerializer):
    """
    Serializer para estadísticas diarias con soporte para crear ProductUsageLog anidados.
    """
    product_usages = ProductUsageLogSerializer(
        many=True, write_only=True, required=False
    )

    class Meta:
        model = DailyStat
        fields = [
            "id",
            "cycle",
            "pond",
            "stat_date",
            "name",
            "description",
            "product_usages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        cycle = data.get("cycle") or (self.instance.cycle if self.instance else None)
        pond = data.get("pond") or (self.instance.pond if self.instance else None)
        stat_date = data.get("stat_date") or (
            self.instance.stat_date if self.instance else None
        )

        # Validar que el ciclo está IN_PROGRESS
        if cycle:
            if cycle.state != Cycle.State.IN_PROGRESS:
                raise serializers.ValidationError({
                    "cycle": "El ciclo debe estar en estado IN_PROGRESS."
                })

        # Validar que el estanque está IN_USE
        if pond:
            if pond.status != Pond.Status.IN_USE:
                raise serializers.ValidationError({
                    "pond": "El estanque debe estar en estado IN_USE."
                })

        # Validar que el estanque está asociado al ciclo
        if cycle and pond:
            cpb_exists = PondBatch.objects.filter(
                pond=pond,
                pond_batch__cycle_pond_batches__cycle=cycle,
            ).exists()
            if not cpb_exists:
                raise serializers.ValidationError({
                    "pond": "El estanque no está asociado a este ciclo."
                })

        # Validar que la fecha <= hoy
        if stat_date and stat_date > date.today():
            raise serializers.ValidationError({
                "stat_date": "La fecha del stat no puede ser futura."
            })

        return data

    def create(self, validated_data):
        product_usages_data = validated_data.pop("product_usages", [])

        # Crear el DailyStat
        daily_stat = DailyStat.objects.create(**validated_data)

        # Crear ProductUsageLogs y sus InventoryMovements
        for usage_data in product_usages_data:
            usage_data["daily_stat"] = daily_stat
            product_usage = ProductUsageLog.objects.create(**usage_data)

            # Crear InventoryMovement
            try:
                create_out_movement(
                    farm=daily_stat.cycle.farm,
                    product=product_usage.product,
                    quantity=product_usage.quantity_used,
                    source_type=InventoryMovement.SourceType.DAILY,
                    source_id=product_usage.id,
                    observations=f"Uso registrado en Daily Stat {daily_stat.id}",
                    pond=daily_stat.pond,
                    cycle=daily_stat.cycle,
                )
            except ValueError as e:
                # Si hay error de stock, eliminar el ProductUsageLog y relanzar
                product_usage.delete()
                raise serializers.ValidationError({
                    "product_usages": str(e)
                })

        return daily_stat


class ControlStatSerializer(serializers.ModelSerializer):
    """
    Serializer para estadísticas de control con cálculo automático de campos derivados.
    """

    class Meta:
        model = ControlStat
        fields = [
            "id",
            "cycle",
            "pond",
            "control_date",
            "sampled_quantity",
            "live_quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "mortality_percentage",
            "biomass_kg",
            "fca",
            "biomass_gain_kg",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "sampled_quantity",
            "live_quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "mortality_percentage",
            "biomass_kg",
            "fca",
            "biomass_gain_kg",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        cycle = data.get("cycle") or (self.instance.cycle if self.instance else None)
        pond = data.get("pond") or (self.instance.pond if self.instance else None)
        control_date = data.get("control_date") or (
            self.instance.control_date if self.instance else None
        )

        # Validar que el ciclo está IN_PROGRESS
        if cycle:
            if cycle.state != Cycle.State.IN_PROGRESS:
                raise serializers.ValidationError({
                    "cycle": "El ciclo debe estar en estado IN_PROGRESS."
                })

        # Validar que el estanque está IN_USE
        if pond:
            if pond.status != Pond.Status.IN_USE:
                raise serializers.ValidationError({
                    "pond": "El estanque debe estar en estado IN_USE."
                })

        # Validar que el estanque está asociado al ciclo
        if cycle and pond:
            cpb_exists = PondBatch.objects.filter(
                pond=pond,
                pond_batch__cycle_pond_batches__cycle=cycle,
            ).exists()
            if not cpb_exists:
                raise serializers.ValidationError({
                    "pond": "El estanque no está asociado a este ciclo."
                })

        # Validar que debe existir al menos 1 FishEvaluated previo
        if cycle and pond and control_date:
            fish_evals = FishEvaluated.objects.filter(
                cycle=cycle,
                pond=pond,
                evaluation_date__lte=control_date,
                deleted_at__isnull=True,
            )
            if not fish_evals.exists():
                raise serializers.ValidationError({
                    "control_date": "Debe existir al menos una evaluación de peces previa a la fecha de control."
                })

        # Validar que control_date <= hoy
        if control_date and control_date > date.today():
            raise serializers.ValidationError({
                "control_date": "La fecha del control no puede ser futura."
            })

        return data

    def create(self, validated_data):
        cycle = validated_data["cycle"]
        pond = validated_data["pond"]
        control_date = validated_data["control_date"]

        # Obtener todas las evaluaciones hasta la fecha de control
        evaluations = FishEvaluated.objects.filter(
            cycle=cycle,
            pond=pond,
            evaluation_date__lte=control_date,
            deleted_at__isnull=True,
        )

        # Calcular estadísticas agregadas
        stats = FishEvaluatedCalculator.aggregate_fish_evaluations(evaluations)

        # Calcular biomasa actual
        current_biomass = BiomassCalculator.calculate_biomass(
            stats["live_quantity"], stats["avg_weight_g"]
        )

        # Calcular ganancia de biomasa y FCA
        biomass_gain = None
        fca = None

        last_control = (
            ControlStat.objects.filter(
                cycle=cycle,
                pond=pond,
                control_date__lt=control_date,
                deleted_at__isnull=True,
            )
            .order_by("-control_date")
            .first()
        )

        if last_control:
            biomass_gain = BiomassCalculator.calculate_biomass_gain(
                current_biomass, last_control.biomass_kg
            )
            feed_consumed = BiomassCalculator.get_feed_consumed_since_last_control(
                cycle.id, pond.id, control_date
            )
            if biomass_gain:
                fca = BiomassCalculator.calculate_fca(feed_consumed, biomass_gain)

        # Crear el ControlStat con los datos calculados
        control_stat = ControlStat.objects.create(
            cycle=cycle,
            pond=pond,
            control_date=control_date,
            sampled_quantity=stats["sampled_quantity"],
            live_quantity=stats["live_quantity"],
            min_weight_g=stats["min_weight_g"],
            avg_weight_g=stats["avg_weight_g"],
            max_weight_g=stats["max_weight_g"],
            mortality_percentage=stats["mortality_percentage"],
            biomass_kg=current_biomass,
            fca=fca,
            biomass_gain_kg=biomass_gain,
        )

        return control_stat


__all__ = [
    "FishEvaluatedSerializer",
    "DailyStatSerializer",
    "ProductUsageLogSerializer",
    "ControlStatSerializer",
]
