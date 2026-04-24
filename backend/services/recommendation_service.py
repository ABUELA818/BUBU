def get_recommendations(body_type):
    
    recommendations = {
        "triangulo_invertido": {
            "tops": [
                "playeras sueltas",
                "colores oscuros arriba",
                "cuellos en V"
            ],
            "bottoms": [
                "pantalones claros",
                "jeans rectos o baggy",
                "faldas con volumen"
            ]
        },
        "triangulo": {
            "tops": [
                "blusas estructuradas",
                "hombreras",
                "colores llamativos arriba"
            ],
            "bottoms": [
                "pantalones oscuros",
                "cortes rectos",
                "evitar volumen en cadera"
            ]
        },
        "rectangular": {
            "tops": [
                "ropa ajustada",
                "crop tops",
                "capas para volumen"
            ],
            "bottoms": [
                "pantalones de tiro alto",
                "cinturones",
                "cortes que marquen cintura"
            ]
        }
    }

    return recommendations.get(body_type, {})