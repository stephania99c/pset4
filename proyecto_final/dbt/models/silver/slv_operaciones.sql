-- SILVER: una fila por operacion, marcando si es credito de auto (sin sufijo).
select
    numero_operacion,
    estado_actual,
    substr(numero_operacion, 10) = ''   as es_auto
from {{ ref('stg_operaciones') }}
where numero_operacion is not null
qualify row_number() over (partition by numero_operacion order by estado_actual) = 1