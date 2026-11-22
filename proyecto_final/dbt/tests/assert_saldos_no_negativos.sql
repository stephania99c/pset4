-- Regla de negocio: dias de mora y saldos no pueden ser negativos.
select cartera_diaria_id
from {{ ref('fct_cartera_diaria') }}
where dias_mora < 0 or capital_insoluto < 0 or valor_deuda_exigible < 0 or capital_vencido < 0