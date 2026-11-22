-- GOLD: dimension de gestores de call center. Una fila por gestor.
select
    cobrador_id,
    count(*)                as total_gestiones_mes,
    min(fecha_gestion)      as primera_gestion,
    max(fecha_gestion)      as ultima_gestion
from {{ ref('slv_gestiones') }}
where es_auto and es_call_center and not es_posible_duplicado
  and cobrador_id is not null
group by cobrador_id