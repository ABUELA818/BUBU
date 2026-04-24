from data.catalog import catalog

def recommend_products(body_type):

    rules = {
        "triangulo_invertido": {
            "preferred_tags": ["claro", "volumen"],
            "avoid_tags": ["hombreras"]
        },
        "triangulo": {
            "preferred_tags": ["estructurada"],
            "avoid_tags": ["volumen"]
        },
        "rectangular": {
            "preferred_tags": ["ajustado", "cintura"],
            "avoid_tags": []
        }
    }

    rule = rules.get(body_type, {})
    preferred = rule.get("preferred_tags", [])
    avoid = rule.get("avoid_tags", [])

    results = []

    for product in catalog:
        score = 0

        for tag in product["tags"]:
            if tag in preferred:
                score += 2
            if tag in avoid:
                score -= 2

        if score > 0:
            results.append({
                "product": product,
                "score": score
            })

    # ordenar por score
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:3]