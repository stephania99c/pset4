-- El grano de la cartera (operacion + pagare + fecha) no debe repetirse.
-- Un test propio pasa si esta consulta devuelve 0 filas.
select numero_operacion, tipo_pagare, fecha_corte, count(*) as veces
from {{ ref('slv_cartera_diaria') }}
group by 1, 2, 3
having count(*) > 1