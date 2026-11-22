-- Regla de negocio: la fecha de compromiso de pago no puede ser anterior a la gestion.
select gestion_id
from {{ ref('fct_gestiones') }}
where fecha_compromiso < fecha_gestion