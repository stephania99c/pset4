-- Regla de alcance: en Gold no debe haber operaciones con sufijo (solo creditos de auto).
select numero_operacion
from {{ ref('dim_operacion') }}
where substr(numero_operacion, 10) <> ''