"""Métricas de recuperación binaria sobre rankings completos."""


def evaluar_ranking(nombres, relevantes, universo):
    nombres = list(nombres)
    relevantes = set(relevantes)
    universo = set(universo)
    if not relevantes or not relevantes <= universo:
        raise ValueError("Se requiere al menos un relevante dentro de la colección.")
    if len(nombres) != len(set(nombres)) or not set(nombres) <= universo:
        raise ValueError("El ranking contiene duplicados o documentos ajenos.")
    aciertos = 0
    suma_precisiones = 0.0
    puntos = []
    for posicion, nombre in enumerate(nombres, 1):
        relevante = nombre in relevantes
        aciertos += int(relevante)
        precision = aciertos / posicion
        exhaustividad = aciertos / len(relevantes)
        if relevante:
            suma_precisiones += precision
        puntos.append({
            "posicion": posicion, "nombre": nombre, "relevante": relevante,
            "precision": precision, "recall": exhaustividad,
        })
    tp = aciertos
    fp = len(nombres) - tp
    fn = len(relevantes) - tp
    tn = len(universo) - tp - fp - fn
    interpolada = [
        max((p["precision"] for p in puntos if p["recall"] >= nivel / 10), default=0.0)
        for nivel in range(11)
    ]
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": tp / len(nombres) if nombres else 0.0,
        "recall": tp / len(relevantes), "accuracy": (tp + tn) / len(universo),
        "AP": suma_precisiones / len(relevantes), "puntos": puntos,
        "interpolada": interpolada,
        "relevantes_ausentes": sorted(relevantes - set(nombres)),
    }
