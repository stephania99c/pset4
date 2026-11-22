-- BRONZE: pagos con tipos corregidos.
select
    nullif(trim(id_operacion), '')              as id_operacion,
    nullif(trim(numero_operacion), '')          as numero_operacion,
    nullif(trim(identificacion), '')            as cliente_id,
    try_to_date(fecha_emision)                  as fecha_emision,
    try_to_date(fecha_pago)                     as fecha_pago,
    try_to_decimal(monto, 18, 2)                as monto,
    upper(nullif(trim(tipo_pago), ''))          as tipo_pago,
    upper(nullif(trim(estado), ''))             as estado,
    upper(nullif(trim(forma_pago), ''))         as forma_pago,
    upper(nullif(trim(motivo), ''))             as motivo
from {{ source('raw', 'pagos') }}