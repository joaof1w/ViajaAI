"""Services: um por caso de uso.

Cada caso de uso tem seu próprio módulo/classe — importe diretamente o que precisar,
por exemplo:

    from backend.services.cadastrar_usuario_service import CadastrarUsuarioService

Casos de uso disponíveis:
    cadastrar_usuario_service ....... CadastrarUsuarioService
    verificar_codigo_service ........ VerificarCodigoService
    reenviar_codigo_service ......... ReenviarCodigoService
    autenticar_usuario_service ...... AutenticarUsuarioService
    encerrar_sessao_service ......... EncerrarSessaoService
    obter_perfil_service ............ ObterPerfilService
    listar_interesses_service ....... ListarInteressesService
    salvar_preferencias_service ..... SalvarPreferenciasService
    listar_lugares_service .......... ListarLugaresService
    buscar_lugares_service .......... BuscarLugaresService
    recomendar_lugares_service ...... RecomendarLugaresService
    obter_lugar_service ............. ObterLugarService
    calcular_match_service .......... CalcularMatchService
    salvar_favorito_service ......... SalvarFavoritoService
    listar_favoritos_service ........ ListarFavoritosService
    remover_favorito_service ........ RemoverFavoritoService
    enviar_mensagem_chat_service .... EnviarMensagemChatService
    listar_historico_chat_service ... ListarHistoricoChatService
    gerar_relatorio_service ......... GerarRelatorioService

Integrações externas encapsuladas:
    gemini_service .................. GeminiService (LLM)
    assistente_local_service ........ AssistenteLocalService (fallback do chat)
    envio_email_service ............. EnvioEmailService (SMTP)
"""
