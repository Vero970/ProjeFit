import logging
import azure.functions as func
import requests
import json
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime

USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

def get_usda_calories(api_key, query):
    params = {"api_key": api_key, "query": query, "pageSize": 1}
    resp = requests.get(USDA_API_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    foods = data.get("foods", [])
    if not foods:
        return None, None
    f = foods[0]
    kcal = None
    for n in f.get("foodNutrients", []):
        name = n.get("nutrientName", "").lower()
        if "energy" in name or "calories" in name:
            kcal = n.get("value")
            break
    desc = f.get("description") or f.get("lowercaseDescription") or query
    return kcal, desc

def save_blob(conn_str, container, prefix, data):
    cli = BlobServiceClient.from_connection_string(conn_str)
    cont = cli.get_container_client(container)
    try:
        cont.create_container()
    except:
        pass
    blob_name = f"{prefix}_{int(datetime.utcnow().timestamp())}.json"
    cont.upload_blob(blob_name, json.dumps(data), overwrite=True)
    return blob_name

def calc_harris_benedict(sexo, peso, altura, idade, atividade):
    sexo = sexo.lower()
    if sexo == "f" or sexo == "feminino":
        tmb = 447.6 + (9.2 * peso) + (3.1 * altura) - (4.3 * idade)
    else:
        tmb = 88.36 + (13.4 * peso) + (4.8 * altura) - (5.7 * idade)
    fatores = {
        "sedentario": 1.2,
        "leve": 1.375,
        "moderado": 1.55,
        "intenso": 1.725,
        "muito_intenso": 1.9
    }
    fator = fatores.get(atividade, 1.2)
    get = tmb * fator
    return tmb, get

def list_blobs(conn_str, container, max_items=50):
    cli = BlobServiceClient.from_connection_string(conn_str)
    cont = cli.get_container_client(container)
    names = []
    try:
        for b in cont.list_blobs():
            names.append(b.name)
            if len(names) >= max_items:
                break
    except:
        pass
    return sorted(names, reverse=True)

def read_blob(conn_str, container, blob_name):
    cli = BlobServiceClient.from_connection_string(conn_str)
    cont = cli.get_container_client(container)
    try:
        blob = cont.download_blob(blob_name)
        return json.loads(blob.readall())
    except:
        return None

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        action = req.params.get("action", "calc")
        conn = os.getenv("STORAGE_CONNECTION_STRING")
        container = os.getenv("BLOB_CONTAINER", "ingestao")
        api_key = os.getenv("USDA_API_KEY")
        if action == "calc":
            body = req.get_json(silent=True) or {}
            alimento = req.params.get("alimento") or body.get("alimento")
            quantidade = req.params.get("quantidade") or body.get("quantidade")
            if not alimento or not quantidade:
                return func.HttpResponse("Faltando alimento/quantidade", status_code=400)
            quantidade = float(quantidade)
            kcal100, desc = get_usda_calories(api_key, alimento)
            if kcal100 is None:
                return func.HttpResponse("Alimento não encontrado.", status_code=404)
            total = kcal100 * (quantidade / 100)
            result = {
                "tipo": "ingestao",
                "alimento": desc,
                "query": alimento,
                "quantidade_g": quantidade,
                "calorias_por_100g": kcal100,
                "calorias_totais": total,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            if conn:
                name = save_blob(conn, container, "ingestao", result)
                result["saved_as"] = name
            return func.HttpResponse(json.dumps(result), mimetype="application/json")
        if action == "tmb":
            b = req.get_json(silent=True) or {}
            sexo = b.get("sexo"); peso = float(b.get("peso")); altura = float(b.get("altura")); idade = int(b.get("idade")); atividade = b.get("atividade")
            if not sexo or not peso or not altura or not idade:
                return func.HttpResponse("Campos insuficientes", status_code=400)
            tmb, get = calc_harris_benedict(sexo, peso, altura, idade, atividade)
            result = {"tipo":"tmb","sexo":sexo,"peso":peso,"altura":altura,"idade":idade,"atividade":atividade,"tmb":tmb,"get":get,"timestamp":datetime.utcnow().isoformat() + "Z"}
            if conn:
                name = save_blob(conn, container, "tmb", result)
                result["saved_as"] = name
            return func.HttpResponse(json.dumps(result), mimetype="application/json")
        if action == "relatorio":
            blobs = list_blobs(conn, container, max_items=200)
            ingestao = []; tmb_info = None
            for bname in blobs:
                data = read_blob(conn, container, bname)
                if not data:
                    continue
                if data.get("tipo") == "ingestao":
                    ingestao.append(data)
                if data.get("tipo") == "tmb":
                    tmb_info = data
            total_consumido = sum(i["calorias_totais"] for i in ingestao) if ingestao else 0
            balanco = (total_consumido - tmb_info["get"]) if tmb_info else None
            report = {"calorias_consumidas": total_consumido, "dados_ingestao": ingestao, "tmb_info": tmb_info, "balanco_calorico": balanco}
            return func.HttpResponse(json.dumps(report), mimetype="application/json")
        return func.HttpResponse("Ação inválida", status_code=400)
    except Exception as e:
        logging.exception(e)
        return func.HttpResponse(str(e), status_code=500)
