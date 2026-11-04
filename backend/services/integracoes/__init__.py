"""Integrações externas encapsuladas (cada uma em seu Service).

    cliente_http ............ ClienteHttp (User-Agent, timeout, cache e intervalo mínimo por host)
    geocodificacao_service .. GeocodificacaoService (Nominatim / OpenStreetMap)
    pontos_interesse_service  PontosInteresseService (Overpass API / OpenStreetMap)
    clima_service ........... ClimaService (Open-Meteo)
    fotos_wikimedia_service . FotosWikimediaService (Wikipédia + Wikimedia Commons)
    fotos_pexels_service .... FotosPexelsService (requer PEXELS_API_KEY)
    fotos_unsplash_service .. FotosUnsplashService (requer UNSPLASH_ACCESS_KEY)
"""
