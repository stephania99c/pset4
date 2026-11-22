-- GOLD: dimension de fechas (calendario 2015-2027). Una fila por dia.
with dias as (
    select dateadd(day, row_number() over (order by seq4()) - 1, '2015-01-01'::date) as fecha
    from table(generator(rowcount => 4748))
)

select
    fecha,
    year(fecha)                         as anio,
    month(fecha)                        as mes,
    day(fecha)                          as dia,
    dayofweekiso(fecha)                 as dia_semana,       -- 1 = lunes ... 7 = domingo
    dayofweekiso(fecha) in (6, 7)       as es_fin_de_semana,
    fecha = last_day(fecha)             as es_fin_de_mes
from dias
