import azure.functions as func
import json
import logging
import requests
from azure.storage.blob import BlobServiceClient
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("HTTP trigger function processed a request.")

    action = req.params.get('action')
    if not action:
        return func.HttpResponse(
            json.dumps({"erro": "Forneça o parâmetro ?action=calc|tmb|relatorio"}),
            status_code=400
        )

    USDA_API_KEY = req.headers.get("X-USDA-KEY") or req.params.get("usda_key")
    if not USDA_API_KEY:
        USDA_API_KEY = "apikey"  # ou deixe vazio para ambiente local

    STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true"
    BLOB_CONTAINER = "ingestao"

    blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    container = blob_service.get_container_client(BLOB_CONTAINER)

    if action == "calc":
        alimento = req.params.get("alimento")
        quantidade = req.params.get("quantidade")

        if not alimento or not quantidade:
            return func.HttpResponse(
                json.dumps({"erro": "Parametros alimento e quantidade obrigatórios"}),
                status_code=400
            )

        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={alimento}&api_key={USDA_API_KEY}"
        usda_response = requests.get(url)
        dados = usda_response.json()

        try:
            alimento_data = dados["foods"][0]
            calorias_100g = next(
                n for n in alimento_data["foodNutrients"] if n["nutrientName"] == "Energy"
            )["value"]
        except:
            return func.HttpResponse(json.dumps({"erro": "Alimento não encontrado"}))

        calorias_totais = calorias_100g * (float(quantidade) / 100)

        registro = {
            "alimento": alimento,
            "quantidade": quantidade,
            "calorias_totais": calorias_totais,
            "timestamp": str(datetime.utcnow())
        }

        nome_blob = f"ingestao_{datetime.utcnow().timestamp()}.json"
        container.upload_blob(nome_blob, json.dumps(registro))

        return func.HttpResponse(json.dumps(registro))

    if action == "tmb":
        body = req.get_json()
        sexo = body["sexo"]
        peso = body["peso"]
        altura = body["altura"]
        idade = body["idade"]
        atividade = body["atividade"]

        if sexo.lower().startswith("m"):
            tmb = 88.36 + (13.4 * peso) + (4.8 * altura) - (5.7 * idade)
        else:
            tmb = 447.6 + (9.2 * peso) + (3.1 * altura) - (4.3 * idade)

        fatores = {
            "sedentario": 1.2,
            "leve": 1.375,
            "moderado": 1.55,
            "intenso": 1.725,
            "muito_intenso": 1.9
        }
        get = tmb * fatores[atividade]

        registro = {
            "tmb": tmb,
            "get": get,
            "timestamp": str(datetime.utcnow())
        }

        nome_blob = f"tmb_{datetime.utcnow().timestamp()}.json"
        container.upload_blob(nome_blob, json.dumps(registro))

        return func.HttpResponse(json.dumps(registro))

    if action == "relatorio":
        blobs = container.list_blobs()

        total_calorias = 0
        tmb_info = None

        for blob in blobs:
            data = json.loads(container.download_blob(blob).readall())

            if "calorias_totais" in data:
                total_calorias += data["calorias_totais"]

            if "get" in data:
                tmb_info = data

        if not tmb_info:
            return func.HttpResponse(json.dumps({"erro": "Nenhum TMB calculado"}))

        balanco = total_calorias - tmb_info["get"]

        return func.HttpResponse(json.dumps({
            "calorias_consumidas": total_calorias,
            "tmb_info": tmb_info,
            "balanco_calorico": balanco
        }))

    return func.HttpResponse(json.dumps({"erro": "Ação inválida"}))
