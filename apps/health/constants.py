TREATMENT_PLAN_DATE_OVERLAP_MESSAGE = (
    "Las fechas se solapan con otro plan de tratamiento vigente del mismo registro de salud."
)

# Tipo de evaluación de peces creada desde un POST combinado de HealthStat.
FISH_EVALUATED_TYPE_HEALTH_STAT = "health_stat"

# Campos write-only del POST combinado (formulario plano → FishEvaluated).
FISH_EVALUATION_CREATE_FIELDS = (
    "sampled_quantity",
    "mortality_quantity",
    "observations",
    "batch_id",
)
