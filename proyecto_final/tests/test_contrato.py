"""Contrato de la API: que acepta y que rechaza."""


def test_entrada_valida_devuelve_200_con_el_esquema(cliente, credito):
    respuesta = cliente.post("/predecir", json=credito)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id_prediccion", "decision", "probabilidad", "puntaje", "nota_corte",
                           "efecto_incremental", "interpretacion_efecto", "version_modelo",
                           "uso_respaldo"}
    assert cuerpo["decision"] in ("gestionar", "no gestionar")
    assert 0 <= cuerpo["probabilidad"] <= 1


def test_campo_faltante_devuelve_422(cliente, credito):
    del credito["dias_mora"]
    respuesta = cliente.post("/predecir", json=credito)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][-1] == "dias_mora"


def test_tipo_incorrecto_devuelve_422(cliente, credito):
    credito["capital_insoluto"] = "mucho"
    respuesta = cliente.post("/predecir", json=credito)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][-1] == "capital_insoluto"


def test_categoria_desconocida_devuelve_422(cliente, credito):
    credito["estado_operacion"] = "VIGENTE"
    respuesta = cliente.post("/predecir", json=credito)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"][-1] == "estado_operacion"