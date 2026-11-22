-- BRONZE: historico de operaciones con nombres y textos estandarizados.
select
    nullif(trim(numero_operacion), '')          as numero_operacion,
    upper(nullif(trim(estado_actual), ''))      as estado_actual
from {{ source('raw', 'operaciones') }}